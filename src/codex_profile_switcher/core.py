from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback.
    fcntl = None


PROFILE_FILES = ("config.toml", "account.config.toml", "api.config.toml", "auth.json")
PROFILE_METADATA_FILE = "profile.json"

# Codex Desktop groups its conversation history by the active model_provider name.
# Keeping that name constant across every switch is what stops chat history from
# "disappearing" when you flip between auth and api-key profiles. The name must
# NOT be a reserved built-in id (Codex rejects `[model_providers.openai]`), so the
# default is the custom gateway provider used for both auth and api routes.
DEFAULT_ACTIVE_PROVIDER = "gateway"
DEFAULT_ENV_KEY = "OPENAI_API_KEY"

# Provider ids that Codex reserves for built-ins and refuses to let configs
# override with a `[model_providers.<id>]` section (matched case-insensitively).
RESERVED_PROVIDER_IDS = {"openai"}


@dataclass(frozen=True)
class ProfileStatus:
    name: str
    path: Path
    exists: bool
    mode: str
    model: str | None
    provider: str | None
    base_url: str | None
    auth_present: bool
    auth_mode: str | None
    config_present: bool
    config_empty: bool
    api_config_present: bool
    profile_kind: str | None

    @property
    def route_uses_auth(self) -> bool:
        return self.mode in {"auth", "hybrid"}

    @property
    def auth_is_ignored(self) -> bool:
        return self.mode == "api" and self.auth_present


@dataclass(frozen=True)
class Diagnostic:
    level: str
    subject: str
    message: str


class ProfileStore:
    def __init__(self, root: Path | None = None, codex_dir: Path | None = None) -> None:
        self.root = root or Path(os.environ.get("CODEX_PROFILE_ROOT", "~/.codex-profiles")).expanduser()
        self.codex_dir = codex_dir or Path(os.environ.get("CODEX_DIR", "~/.codex")).expanduser()
        configured = os.environ.get("CODEX_ACTIVE_PROVIDER", "").strip()
        safe = safe_provider_name(configured) if configured else ""
        if not safe or safe.lower() in RESERVED_PROVIDER_IDS:
            safe = DEFAULT_ACTIVE_PROVIDER
        self.active_provider = safe
        self._lock_depth = 0

    def profile_dir(self, name: str) -> Path:
        return self.root / validate_profile_name(name)

    def lock_path(self) -> Path:
        return self.root / ".cps.lock"

    @contextmanager
    def locked(self):
        if self._lock_depth:
            yield
            return
        self.root.mkdir(parents=True, exist_ok=True)
        lock_path = self.lock_path()
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            self._lock_depth += 1
            try:
                yield
            finally:
                self._lock_depth -= 1
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def last_mix_path(self) -> Path:
        return self.root / "last-mix.json"

    def read_last_mix(self) -> tuple[str | None, str | None]:
        try:
            data = json.loads(self.last_mix_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None, None
        if not isinstance(data, dict):
            return None, None
        auth = data.get("auth")
        route = data.get("route")
        return (
            auth if isinstance(auth, str) and auth else None,
            route if isinstance(route, str) and route else None,
        )

    def write_last_mix(self, auth_name: str, route_name: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        text = json.dumps({"auth": auth_name, "route": route_name}, indent=2, sort_keys=True) + "\n"
        atomic_write(self.last_mix_path(), text)

    def initial_mix_selection(self) -> tuple[str | None, str | None]:
        auth, route = self.read_last_mix()
        if auth or route:
            return auth, route
        return self.infer_active_mix()

    def infer_active_mix(self) -> tuple[str | None, str | None]:
        active_auth = read_text(self.codex_dir / "auth.json")
        active_status = self.active_status()
        auth_name: str | None = None
        route_name: str | None = None

        for name in self.list_profiles():
            profile_path = self.profile_dir(name)
            status = self.profile_status(name)
            if auth_name is None and active_auth and read_text(profile_path / "auth.json") == active_auth and not status.base_url:
                auth_name = name
            if route_name is None and route_matches_active(status, active_status):
                route_name = name
        return auth_name, route_name

    def list_profiles(self) -> list[str]:
        if not self.root.exists():
            return []
        ignored = {"bin", "backups", "deleted"}
        return sorted(p.name for p in self.root.iterdir() if p.is_dir() and p.name not in ignored)

    def list_deleted(self) -> list[str]:
        deleted = self.root / "deleted"
        if not deleted.exists():
            return []
        return sorted(p.name for p in deleted.iterdir() if p.is_dir())

    def init_profile(self, name: str) -> Path:
        with self.locked():
            target = self.profile_dir(name)
            target.mkdir(parents=True, exist_ok=True)
            self._copy_profile_files(self.codex_dir, target)
            self._ensure_file_auth_store(target / "config.toml")
            self._write_profile_metadata(target, "full")
            return target

    def init_auth_profile(self, name: str) -> Path:
        with self.locked():
            target = self.profile_dir(name)
            target.mkdir(parents=True, exist_ok=True)
            self._copy_named_files(self.codex_dir, target, ("account.config.toml", "config.toml"))
            atomic_write(target / "config.toml", rewrite_config_for_auth_profile(read_text(target / "config.toml")))
            self._ensure_file_auth_store(target / "config.toml")
            self._write_profile_metadata(target, "auth", auth_policy="codex_login")
            return target

    def create_auth_profile(self, name: str) -> int:
        self.init_auth_profile(name)
        return self.login_profile(name)

    def init_route_profile(self, name: str) -> Path:
        with self.locked():
            target = self.profile_dir(name)
            target.mkdir(parents=True, exist_ok=True)
            self._copy_named_files(self.codex_dir, target, ("config.toml", "api.config.toml"))
            for auth_file in ("auth.json", "account.config.toml"):
                path = target / auth_file
                if path.exists():
                    path.unlink()
            self._ensure_file_auth_store(target / "config.toml")
            self._write_route_metadata_from_config(target)
            return target

    def create_route_profile(
        self,
        name: str,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        env_key: str | None = DEFAULT_ENV_KEY,
        provider: str = DEFAULT_ACTIVE_PROVIDER,
        wire_api: str = "responses",
    ) -> Path:
        if not name.strip():
            raise ValueError("profile name is required")
        target = self.profile_dir(name.strip())
        if target.exists():
            raise FileExistsError(f"profile already exists: {target}")
        if not base_url.strip():
            raise ValueError("base_url is required")
        if not model.strip():
            raise ValueError("model is required")
        if not (api_key and api_key.strip()) and not (env_key and env_key.strip()):
            raise ValueError("api_key or env_key is required")
        if not provider.strip():
            raise ValueError("provider is required")

        safe_provider = safe_provider_name(provider)
        if not safe_provider:
            raise ValueError("provider is required")

        credential_mode = "bearer_token" if api_key and api_key.strip() else "env_key"
        clean_env_key = env_key.strip() if env_key else None
        clean_wire_api = wire_api.strip() or "responses"
        with self.locked():
            config = rewrite_config_for_custom_route(
                "",
                provider=safe_provider,
                base_url=base_url.strip(),
                model=model.strip(),
                api_key=api_key.strip() if api_key else None,
                env_key=clean_env_key,
                wire_api=clean_wire_api,
            )
            target.mkdir(parents=True, exist_ok=False)
            atomic_write(target / "config.toml", config)
            self._write_profile_metadata(
                target,
                "route",
                provider=safe_provider,
                model=model.strip(),
                base_url=base_url.strip(),
                wire_api=clean_wire_api,
                credential_mode=credential_mode,
                env_key=clean_env_key if credential_mode == "env_key" else None,
                auth_policy="preserve_on_mix",
            )
            return target

    def save_profile(self, name: str) -> Path:
        return self.init_profile(name)

    def use_profile(self, name: str) -> Path:
        with self.locked():
            source = self.profile_dir(name)
            if not source.exists():
                raise FileNotFoundError(f"profile does not exist: {source}")
            backup = self.backup_current()
            self._replace_profile_files(source, self.codex_dir)
            self._normalize_active_home_paths()
            self._stabilize_active_provider()
            return backup

    def mix_profiles(self, auth_name: str, route_name: str) -> Path:
        with self.locked():
            auth_source = self.profile_dir(auth_name)
            route_source = self.profile_dir(route_name)
            if not auth_source.exists():
                raise FileNotFoundError(f"auth profile does not exist: {auth_source}")
            if not route_source.exists():
                raise FileNotFoundError(f"route profile does not exist: {route_source}")
            if not (auth_source / "auth.json").exists():
                raise FileNotFoundError(f"auth profile has no auth.json: {auth_source}")
            if not (route_source / "config.toml").exists() and not (route_source / "api.config.toml").exists():
                raise FileNotFoundError(f"route profile has no config.toml or api.config.toml: {route_source}")

            backup = self.backup_current()
            self.codex_dir.mkdir(parents=True, exist_ok=True)
            self._replace_named_files(auth_source, self.codex_dir, ("auth.json", "account.config.toml"))
            self._replace_named_files(route_source, self.codex_dir, ("config.toml", "api.config.toml"))
            route_status = self.status_for_path(route_name, route_source)
            if route_status.mode == "api":
                self._normalize_active_api_route(route_name)
            self._normalize_active_home_paths()
            self._stabilize_active_provider()
            self._ensure_file_auth_store(self.codex_dir / "config.toml")
            self.write_last_mix(auth_name, route_name)
            return backup

    def delete_profile(self, name: str) -> Path:
        with self.locked():
            source = self.profile_dir(name)
            if not source.exists():
                raise FileNotFoundError(f"profile does not exist: {source}")
            protected = {"bin", "backups", "deleted"}
            if name in protected:
                raise ValueError(f"refusing to delete protected profile: {name}")
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target = self.root / "deleted" / f"{name}-{stamp}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            return target

    def restore_profile(self, deleted_name: str, profile_name: str | None = None) -> Path:
        with self.locked():
            source = self.root / "deleted" / deleted_name
            if not source.exists():
                raise FileNotFoundError(f"deleted profile does not exist: {source}")
            target_name = profile_name or strip_deleted_stamp(deleted_name)
            target = self.profile_dir(target_name)
            if target.exists():
                raise FileExistsError(f"profile already exists: {target}")
            shutil.move(str(source), str(target))
            return target

    def backup_current(self) -> Path:
        with self.locked():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = self.root / "backups" / stamp
            counter = 1
            while backup.exists():
                backup = self.root / "backups" / f"{stamp}-{counter}"
                counter += 1
            backup.mkdir(parents=True, exist_ok=True)
            self._copy_profile_files(self.codex_dir, backup)
            return backup

    def login_profile(self, name: str) -> int:
        target = self.profile_dir(name)
        with self.locked():
            target.mkdir(parents=True, exist_ok=True)
        codex_bin = self.codex_cli_path()
        if codex_bin is None:
            raise FileNotFoundError("codex CLI not found on PATH or common install locations")
        env = os.environ.copy()
        env["CODEX_HOME"] = str(target)
        return subprocess.call([codex_bin, "login"], env=env)

    def codex_cli_path(self) -> str | None:
        return find_codex_cli()

    def route_custom(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        env_key: str | None = DEFAULT_ENV_KEY,
        provider: str = DEFAULT_ACTIVE_PROVIDER,
        wire_api: str = "responses",
    ) -> Path:
        if not base_url.strip():
            raise ValueError("base_url is required")
        if not model.strip():
            raise ValueError("model is required")
        if not (api_key and api_key.strip()) and not (env_key and env_key.strip()):
            raise ValueError("api_key or env_key is required")
        if not provider.strip():
            raise ValueError("provider is required")
        safe_provider = safe_provider_name(provider)

        with self.locked():
            backup = self.backup_current()
            config_path = self.codex_dir / "config.toml"
            config = read_text(config_path)
            rewritten = rewrite_config_for_custom_route(
                config,
                provider=safe_provider,
                base_url=base_url.strip(),
                model=model.strip(),
                api_key=api_key.strip() if api_key else None,
                env_key=env_key.strip() if env_key else None,
                wire_api=wire_api.strip() or "responses",
            )
            atomic_write(config_path, rewritten)
            self._stabilize_active_provider()
            return backup

    def route_official(self, *, model: str | None = None, provider: str = DEFAULT_ACTIVE_PROVIDER) -> Path:
        if not provider.strip():
            raise ValueError("provider is required")
        with self.locked():
            backup = self.backup_current()
            config_path = self.codex_dir / "config.toml"
            config = read_text(config_path)
            rewritten = rewrite_config_for_official_route(
                config,
                provider=provider.strip(),
                model=model.strip() if model else None,
            )
            atomic_write(config_path, rewritten)
            self._stabilize_active_provider()
            return backup

    def restart_codex(self) -> int:
        schedule_codex_reopen()
        return subprocess.call(["osascript", "-e", 'tell application "Codex" to quit'])

    def active_status(self) -> ProfileStatus:
        return self.status_for_path("active", self.codex_dir)

    def profile_status(self, name: str) -> ProfileStatus:
        return self.status_for_path(name, self.profile_dir(name))

    def status_for_path(self, name: str, path: Path) -> ProfileStatus:
        config_path = path / "config.toml"
        api_config_path = path / "api.config.toml"
        config = read_text(config_path)
        api_config = read_text(api_config_path)
        combined = "\n".join(part for part in (config, api_config) if part)
        auth = read_auth(path / "auth.json")
        metadata = read_profile_metadata(path)
        provider = find_toml_scalar(combined, "model_provider") or infer_provider(combined)
        return ProfileStatus(
            name=name,
            path=path,
            exists=path.exists(),
            mode=detect_mode(combined, auth, provider),
            model=find_toml_scalar(combined, "model"),
            provider=provider,
            base_url=find_provider_scalar(combined, provider, "base_url"),
            auth_present=(path / "auth.json").exists(),
            auth_mode=auth.get("auth_mode") if isinstance(auth, dict) else None,
            config_present=config_path.exists(),
            config_empty=config_path.exists() and not config.strip(),
            api_config_present=api_config_path.exists(),
            profile_kind=metadata_string(metadata, "kind"),
        )

    def diagnose(self) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        if self.codex_cli_path() is None:
            diagnostics.append(
                Diagnostic(
                    "warning",
                    "codex-cli",
                    "codex CLI was not found; auth profile login will fail until `codex` is installed or on PATH",
                )
            )
        if not self.codex_dir.exists():
            diagnostics.append(Diagnostic("error", "active", f"Codex directory does not exist: {self.codex_dir}"))

        self._diagnose_status(self.active_status(), diagnostics, is_active=True)
        last_auth, last_route = self.read_last_mix()
        for label, profile_name in (("last auth", last_auth), ("last route", last_route)):
            if profile_name and not self.profile_dir(profile_name).exists():
                diagnostics.append(
                    Diagnostic("warning", "last-mix", f"{label} profile is missing: {profile_name}")
                )

        for name in self.list_profiles():
            self._diagnose_status(self.profile_status(name), diagnostics, is_active=False)
        return diagnostics

    def _copy_profile_files(self, source: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        self._copy_named_files(source, target, PROFILE_FILES)

    def _replace_profile_files(self, source: Path, target: Path) -> None:
        self._replace_named_files(source, target, PROFILE_FILES)

    def _copy_named_files(self, source: Path, target: Path, names: tuple[str, ...]) -> None:
        target.mkdir(parents=True, exist_ok=True)
        for name in names:
            src = source / name
            if src.exists():
                shutil.copy2(src, target / name)

    def _replace_named_files(self, source: Path, target: Path, names: tuple[str, ...]) -> None:
        target.mkdir(parents=True, exist_ok=True)
        for name in names:
            dst = target / name
            if dst.exists():
                dst.unlink()
        self._copy_named_files(source, target, names)

    def _write_profile_metadata(self, target: Path, kind: str, **extra: str | None) -> None:
        existing = read_profile_metadata(target)
        now = datetime.now().isoformat(timespec="seconds")
        created_at = metadata_string(existing, "created_at") or now
        data: dict[str, str | int] = {
            "schema_version": 1,
            "tool": "cps",
            "kind": kind,
            "created_at": created_at,
            "updated_at": now,
            "active_provider": self.active_provider,
        }
        for key, value in extra.items():
            if value is not None:
                data[key] = value
        text = json.dumps(data, indent=2, sort_keys=True) + "\n"
        atomic_write(target / PROFILE_METADATA_FILE, text)

    def _write_route_metadata_from_config(self, target: Path) -> None:
        config = read_text(target / "config.toml")
        api_config = read_text(target / "api.config.toml")
        combined = "\n".join(part for part in (config, api_config) if part)
        provider = find_toml_scalar(combined, "model_provider") or infer_provider(combined)
        section = find_toml_section(combined, provider) if provider else combined
        credential_mode = None
        env_key = None
        if "experimental_bearer_token =" in section:
            credential_mode = "bearer_token"
        elif find_toml_scalar(section, "env_key"):
            credential_mode = "env_key"
            env_key = find_toml_scalar(section, "env_key")
        self._write_profile_metadata(
            target,
            "route",
            provider=provider,
            model=find_toml_scalar(combined, "model"),
            base_url=find_toml_scalar(section, "base_url"),
            wire_api=find_toml_scalar(section, "wire_api"),
            credential_mode=credential_mode,
            env_key=env_key,
            auth_policy="preserve_on_mix",
        )

    def _diagnose_status(self, status: ProfileStatus, diagnostics: list[Diagnostic], *, is_active: bool) -> None:
        config = read_text(status.path / "config.toml")
        api_config = read_text(status.path / "api.config.toml")
        combined = "\n".join(part for part in (config, api_config) if part)
        for section in reserved_provider_sections(combined):
            diagnostics.append(
                Diagnostic(
                    "error",
                    status.name,
                    f"reserved provider override {section} will be rejected by Codex; CPS will normalize to {self.active_provider}",
                )
            )
        if status.config_present and status.config_empty:
            diagnostics.append(Diagnostic("warning", status.name, "config.toml exists but is empty"))
        if is_active and status.config_present and status.provider and status.provider != self.active_provider:
            diagnostics.append(
                Diagnostic(
                    "info",
                    status.name,
                    f"active provider is {status.provider}; the next CPS write will normalize it to {self.active_provider}",
                )
            )
        if status.route_uses_auth and not status.auth_present:
            diagnostics.append(
                Diagnostic("warning", status.name, "route requires auth.json but auth.json is missing")
            )
        if status.auth_is_ignored:
            diagnostics.append(
                Diagnostic("info", status.name, "auth.json is present but API credentials control model requests")
            )
        if status.profile_kind is None and not is_active:
            diagnostics.append(
                Diagnostic(
                    "info",
                    status.name,
                    f"missing {PROFILE_METADATA_FILE}; treating this as a legacy profile and inferring from config",
                )
            )
        if status.profile_kind == "auth" and not status.auth_present:
            diagnostics.append(Diagnostic("warning", status.name, "auth profile has no auth.json"))
        if status.profile_kind == "route" and not status.config_present and not status.api_config_present:
            diagnostics.append(Diagnostic("warning", status.name, "route profile has no config.toml or api.config.toml"))
        if status.base_url and "model_catalog_json" not in combined:
            diagnostics.append(
                Diagnostic(
                    "info",
                    status.name,
                    "custom route has no model_catalog_json; restart Codex if the model picker shows stale entries",
                )
            )

    def _ensure_file_auth_store(self, config_path: Path) -> None:
        if not config_path.exists():
            return
        text = config_path.read_text(encoding="utf-8")
        if "cli_auth_credentials_store" in text:
            return
        config_path.write_text('cli_auth_credentials_store = "file"\n' + text, encoding="utf-8")

    def _normalize_active_api_route(self, route_name: str) -> None:
        config_path = self.codex_dir / "config.toml"
        config = read_text(config_path)
        provider = find_toml_scalar(config, "model_provider")
        if not provider:
            return
        section = find_toml_section(config, provider)
        if not section or not find_toml_scalar(section, "env_key"):
            return
        route_provider = safe_provider_name(route_name)
        rewritten = rewrite_config_provider_name(
            config,
            old_provider=provider,
            new_provider=route_provider,
            use_openai_auth=True,
        )
        atomic_write(config_path, rewritten)

    def _normalize_active_home_paths(self) -> None:
        config_path = self.codex_dir / "config.toml"
        config = read_text(config_path)
        if not config:
            return
        rewritten = rewrite_embedded_home_paths(config, self.codex_dir)
        if rewritten != config:
            atomic_write(config_path, rewritten)

    def _stabilize_active_provider(self) -> None:
        """Normalize the active config to a single, Codex-valid provider name.

        Codex Desktop buckets conversation history by the active model_provider
        name, so every switch (mix / use / route) must land on the same name or
        the previous history drops out of the sidebar. Codex also *rejects* any
        `[model_providers.openai]` section (case-insensitive) because `openai` is
        a reserved built-in id, so we can never normalize onto that name.

        Rules applied here:
        - A route with custom routing (base_url / env_key / bearer) is renamed to
          the stable, non-reserved `active_provider` name, preserving its keys.
        - A pure account/official config gets an auth-backed provider section
          under the same stable name.
        - Any leftover provider sections (including the illegal reserved ones)
          are dropped so Codex can load the config.
        """
        config_path = self.codex_dir / "config.toml"
        config = read_text(config_path)
        if not config:
            return
        rewritten = normalize_active_provider_config(config, canonical=self.active_provider)
        if rewritten != config:
            atomic_write(config_path, rewritten)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def read_auth(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def read_profile_metadata(path: Path) -> dict:
    try:
        data = json.loads((path / PROFILE_METADATA_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def metadata_string(data: dict, key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def schedule_codex_reopen(timeout_seconds: int = 60) -> None:
    script = f"""
deadline=$(( $(date +%s) + {timeout_seconds} ))
while pgrep -x Codex >/dev/null 2>&1; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    exit 0
  fi
  sleep 0.5
done
open -a Codex >/dev/null 2>&1
"""
    subprocess.Popen(
        ["nohup", "sh", "-c", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(text)
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def split_toml_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current = ""
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            sections.append((current, lines))
            current = stripped
            lines = [line]
        else:
            lines.append(line)
    sections.append((current, lines))
    return sections


def render_toml_sections(sections: list[tuple[str, list[str]]]) -> str:
    text = "".join(line for _, lines in sections for line in lines)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def set_toml_string(lines: list[str], key: str, value: str) -> list[str]:
    prefix = f"{key} = "
    rendered = f'{key} = "{escape_toml_string(value)}"\n'
    for index, raw in enumerate(lines):
        if raw.strip().startswith(prefix):
            lines[index] = rendered
            return lines
    insert_at = trailing_blank_start(lines)
    lines.insert(insert_at, rendered)
    return lines


def set_toml_bool(lines: list[str], key: str, value: bool) -> list[str]:
    prefix = f"{key} = "
    rendered = f"{key} = {'true' if value else 'false'}\n"
    for index, raw in enumerate(lines):
        if raw.strip().startswith(prefix):
            lines[index] = rendered
            return lines
    insert_at = trailing_blank_start(lines)
    lines.insert(insert_at, rendered)
    return lines


def remove_toml_key(lines: list[str], key: str) -> list[str]:
    prefix = f"{key} = "
    return [line for line in lines if not line.strip().startswith(prefix)]


def trailing_blank_start(lines: list[str]) -> int:
    index = len(lines)
    while index > 0 and not lines[index - 1].strip():
        index -= 1
    return index


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def rewrite_config_for_custom_route(
    text: str,
    *,
    provider: str,
    base_url: str,
    model: str,
    api_key: str | None = None,
    env_key: str | None = DEFAULT_ENV_KEY,
    wire_api: str = "responses",
) -> str:
    provider = safe_provider_name(provider)
    use_bearer_token = bool(api_key and api_key.strip())
    credential_value = api_key.strip() if use_bearer_token and api_key else (env_key or DEFAULT_ENV_KEY).strip()
    if not credential_value:
        raise ValueError("api_key or env_key is required")
    sections = split_toml_sections(text)
    section_name = f"[model_providers.{provider}]"
    updated: list[tuple[str, list[str]]] = []
    found_provider = False

    for section, lines in sections:
        lines = list(lines)
        if section == "":
            lines = set_toml_string(lines, "model_provider", provider)
            lines = set_toml_string(lines, "model", model)
            lines = set_toml_string(lines, "preferred_auth_method", "chatgpt")
        elif section == section_name:
            found_provider = True
            lines = set_toml_string(lines, "name", provider)
            lines = set_toml_string(lines, "base_url", base_url)
            lines = set_toml_string(lines, "wire_api", wire_api)
            if use_bearer_token:
                lines = set_toml_bool(lines, "requires_openai_auth", True)
                lines = set_toml_string(lines, "experimental_bearer_token", credential_value)
                lines = remove_toml_key(lines, "env_key")
            else:
                lines = set_toml_bool(lines, "requires_openai_auth", False)
                lines = set_toml_string(lines, "env_key", credential_value)
                lines = remove_toml_key(lines, "experimental_bearer_token")
        elif section.startswith("[model_providers."):
            continue
        updated.append((section, lines))

    if not found_provider:
        if updated and updated[-1][1] and updated[-1][1][-1].strip():
            updated[-1][1].append("\n")
        updated.append(
            (
                section_name,
                [
                    f"{section_name}\n",
                    f'name = "{escape_toml_string(provider)}"\n',
                    f'base_url = "{escape_toml_string(base_url)}"\n',
                    f'wire_api = "{escape_toml_string(wire_api)}"\n',
                    (
                        "requires_openai_auth = true\n"
                        if use_bearer_token
                        else "requires_openai_auth = false\n"
                    ),
                    (
                        f'experimental_bearer_token = "{escape_toml_string(credential_value)}"\n'
                        if use_bearer_token
                        else f'env_key = "{escape_toml_string(credential_value)}"\n'
                    ),
                ],
            )
        )
    return render_toml_sections(updated)


def rewrite_config_for_auth_profile(text: str) -> str:
    sections = split_toml_sections(text)
    updated: list[tuple[str, list[str]]] = []

    for section, lines in sections:
        lines = list(lines)
        if section == "":
            for key in ("model", "model_provider", "preferred_auth_method"):
                lines = remove_toml_key(lines, key)
            updated.append((section, lines))
            continue
        if section.startswith("[model_providers."):
            continue
        updated.append((section, lines))

    return render_toml_sections(updated)


def rewrite_config_for_official_route(text: str, *, provider: str, model: str | None) -> str:
    provider = safe_provider_name(provider)
    sections = split_toml_sections(text)
    updated: list[tuple[str, list[str]]] = []
    section_name = f"[model_providers.{provider}]"
    found_provider = False
    for section, lines in sections:
        lines = list(lines)
        if section == "":
            lines = set_toml_string(lines, "model_provider", provider)
            if model:
                lines = set_toml_string(lines, "model", model)
            lines = set_toml_string(lines, "preferred_auth_method", "chatgpt")
        elif section == section_name:
            found_provider = True
            lines = set_toml_string(lines, "name", provider)
            lines = set_toml_string(lines, "wire_api", "responses")
            lines = set_toml_bool(lines, "requires_openai_auth", True)
            for key in ("base_url", "env_key", "experimental_bearer_token"):
                lines = remove_toml_key(lines, key)
        elif section.startswith("[model_providers."):
            continue
        updated.append((section, lines))
    if not found_provider:
        append_auth_provider_section(updated, provider)
    return render_toml_sections(updated)


def rewrite_config_provider_name(
    text: str,
    *,
    old_provider: str,
    new_provider: str,
    use_openai_auth: bool = False,
) -> str:
    old_section = f"[model_providers.{old_provider}]"
    new_section = f"[model_providers.{new_provider}]"
    sections = split_toml_sections(text)
    updated: list[tuple[str, list[str]]] = []
    for section, lines in sections:
        lines = list(lines)
        if section == "":
            lines = set_toml_string(lines, "model_provider", new_provider)
            lines = remove_toml_key(lines, "preferred_auth_method")
        elif section == old_section:
            section = new_section
            if lines:
                lines[0] = f"{new_section}\n"
            lines = set_toml_string(lines, "name", new_provider)
            if use_openai_auth:
                lines = set_toml_bool(lines, "requires_openai_auth", True)
                lines = remove_toml_key(lines, "env_key")
                lines = remove_toml_key(lines, "experimental_bearer_token")
            else:
                lines = remove_toml_key(lines, "experimental_bearer_token")
        updated.append((section, lines))
    return render_toml_sections(updated)


def provider_section_id(section: str) -> str | None:
    """Return the provider id for a `[model_providers.<id>...]` header, else None."""
    prefix = "[model_providers."
    if section.startswith(prefix) and section.endswith("]"):
        return section[len(prefix):-1]
    return None


def reserved_provider_sections(text: str) -> list[str]:
    reserved: list[str] = []
    for section, _lines in split_toml_sections(text):
        section_id = provider_section_id(section)
        if section_id and section_id.lower() in RESERVED_PROVIDER_IDS:
            reserved.append(section)
    return reserved


def append_auth_provider_section(sections: list[tuple[str, list[str]]], provider: str) -> None:
    section_name = f"[model_providers.{provider}]"
    if sections and sections[-1][1] and sections[-1][1][-1].strip():
        sections[-1][1].append("\n")
    sections.append(
        (
            section_name,
            [
                f"{section_name}\n",
                f'name = "{escape_toml_string(provider)}"\n',
                'wire_api = "responses"\n',
                "requires_openai_auth = true\n",
            ],
        )
    )


def normalize_active_provider_config(text: str, *, canonical: str) -> str:
    """Collapse the active config onto one Codex-valid, stable provider name.

    The provider that `model_provider` points at is treated as the active route.
    If it carries custom routing (base_url / env_key / experimental_bearer_token)
    it is renamed to ``canonical`` with all keys preserved; otherwise a
    ``requires_openai_auth`` provider section is written under the same canonical
    name. Every other `[model_providers.*]` section is dropped, which also removes
    the illegal reserved-id sections that make Codex refuse to load the config.
    """
    canonical = safe_provider_name(canonical)
    provider = find_toml_scalar(text, "model_provider") or infer_provider(text)
    sections = split_toml_sections(text)

    active_index = None
    is_route = False
    if provider:
        for index, (section, lines) in enumerate(sections):
            section_id = provider_section_id(section)
            if section_id is not None and section_id.lower() == provider.lower():
                body = "".join(lines)
                is_route = any(
                    find_toml_scalar(body, key)
                    for key in ("base_url", "env_key", "experimental_bearer_token")
                )
                active_index = index

    target_provider = canonical
    new_header = f"[model_providers.{canonical}]"
    updated: list[tuple[str, list[str]]] = []
    wrote_provider_section = False
    for index, (section, lines) in enumerate(sections):
        lines = list(lines)
        if section == "":
            lines = set_toml_string(lines, "model_provider", target_provider)
            updated.append((section, lines))
            continue
        if provider_section_id(section) is not None:
            if is_route and index == active_index:
                if lines:
                    lines[0] = f"{new_header}\n"
                lines = set_toml_string(lines, "name", canonical)
                updated.append((new_header, lines))
                wrote_provider_section = True
            # Drop every other provider section (inert customs + illegal reserved).
            continue
        updated.append((section, lines))
    if not is_route or not wrote_provider_section:
        append_auth_provider_section(updated, canonical)
    return render_toml_sections(updated)


def rewrite_embedded_home_paths(text: str, codex_dir: Path) -> str:
    sections = split_toml_sections(text)
    updated: list[tuple[str, list[str]]] = []
    home = str(codex_dir)

    for section, lines in sections:
        lines = list(lines)
        if section.endswith(".env]") or section.endswith(".env\" ]"):
            lines = set_toml_string(lines, "CODEX_HOME", home)
            lines = set_toml_string(lines, "NODE_REPL_TRUSTED_CODE_PATHS", home)
        updated.append((section, lines))
    return render_toml_sections(updated)


def find_toml_scalar(text: str, key: str) -> str | None:
    prefix = f"{key} = "
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1]
        return value
    return None


def find_provider_scalar(text: str, provider: str | None, key: str) -> str | None:
    if not provider:
        return find_toml_scalar(text, key)
    target = f"[model_providers.{provider}]"
    for section, lines in split_toml_sections(text):
        if section != target:
            continue
        return find_toml_scalar("".join(lines), key)
    return None


def infer_provider(text: str) -> str | None:
    provider_sections: list[str] = []
    for section, _lines in split_toml_sections(text):
        if section.startswith("[model_providers.") and section.endswith("]"):
            provider_sections.append(section[len("[model_providers.") : -1])
    if "OpenAI" in provider_sections:
        return "OpenAI"
    if len(provider_sections) == 1:
        return provider_sections[0]
    return None


def find_toml_section(text: str, provider: str) -> str:
    target = f"[model_providers.{provider}]"
    for section, lines in split_toml_sections(text):
        if section == target:
            return "".join(lines)
    return ""


def safe_provider_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip())
    cleaned = cleaned.strip("-_")
    if not cleaned or cleaned.lower() in RESERVED_PROVIDER_IDS:
        return DEFAULT_ACTIVE_PROVIDER
    return cleaned


def validate_profile_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("profile name is required")
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        raise ValueError(f"invalid profile name: {name}")
    return cleaned


def route_matches_active(candidate: ProfileStatus, active: ProfileStatus) -> bool:
    if not candidate.config_present or candidate.config_empty:
        return False
    if candidate.base_url or active.base_url:
        return candidate.base_url == active.base_url and candidate.model == active.model
    if candidate.mode == "auth" and active.mode == "auth":
        return True
    return candidate.provider == active.provider and candidate.model == active.model


def detect_mode(config_text: str, auth: dict, provider: str | None = None) -> str:
    provider_text = find_toml_section(config_text, provider) if provider else ""
    relevant_text = provider_text or config_text
    requires_openai_auth = "requires_openai_auth = true" in relevant_text
    has_route_key = "experimental_bearer_token =" in relevant_text or "env_key =" in relevant_text
    has_custom_base_url = bool(find_toml_scalar(relevant_text, "base_url")) and (
        not provider or provider.lower() not in RESERVED_PROVIDER_IDS
    )

    if requires_openai_auth and (has_route_key or has_custom_base_url):
        return "hybrid"
    if requires_openai_auth:
        return "auth"
    if has_route_key:
        return "api"
    if auth.get("tokens"):
        return "auth"
    return "unknown"


def strip_deleted_stamp(name: str) -> str:
    parts = name.rsplit("-", 2)
    if len(parts) == 3 and len(parts[1]) == 8 and len(parts[2]) == 6:
        return parts[0]
    return name


def find_codex_cli() -> str | None:
    found = shutil.which("codex")
    if found:
        return found
    for candidate in (
        Path.home() / ".local/bin/codex",
        Path.home() / ".npm-global/bin/codex",
        Path("/opt/homebrew/bin/codex"),
        Path("/usr/local/bin/codex"),
    ):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None
