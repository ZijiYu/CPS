from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROFILE_FILES = ("config.toml", "account.config.toml", "api.config.toml", "auth.json")


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


class ProfileStore:
    def __init__(self, root: Path | None = None, codex_dir: Path | None = None) -> None:
        self.root = root or Path(os.environ.get("CODEX_PROFILE_ROOT", "~/.codex-profiles")).expanduser()
        self.codex_dir = codex_dir or Path(os.environ.get("CODEX_DIR", "~/.codex")).expanduser()

    def profile_dir(self, name: str) -> Path:
        return self.root / name

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
        target = self.profile_dir(name)
        target.mkdir(parents=True, exist_ok=True)
        self._copy_profile_files(self.codex_dir, target)
        self._ensure_file_auth_store(target / "config.toml")
        return target

    def init_auth_profile(self, name: str) -> Path:
        target = self.profile_dir(name)
        target.mkdir(parents=True, exist_ok=True)
        self._copy_named_files(self.codex_dir, target, ("account.config.toml", "config.toml"))
        self._ensure_file_auth_store(target / "config.toml")
        return target

    def create_auth_profile(self, name: str) -> int:
        self.init_auth_profile(name)
        return self.login_profile(name)

    def init_route_profile(self, name: str) -> Path:
        target = self.profile_dir(name)
        target.mkdir(parents=True, exist_ok=True)
        self._copy_named_files(self.codex_dir, target, ("config.toml", "api.config.toml"))
        for auth_file in ("auth.json", "account.config.toml"):
            path = target / auth_file
            if path.exists():
                path.unlink()
        self._ensure_file_auth_store(target / "config.toml")
        return target

    def save_profile(self, name: str) -> Path:
        return self.init_profile(name)

    def use_profile(self, name: str) -> Path:
        source = self.profile_dir(name)
        if not source.exists():
            raise FileNotFoundError(f"profile does not exist: {source}")
        backup = self.backup_current()
        self._copy_profile_files(source, self.codex_dir)
        return backup

    def mix_profiles(self, auth_name: str, route_name: str) -> Path:
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
        self._copy_named_files(auth_source, self.codex_dir, ("auth.json", "account.config.toml"))
        self._copy_named_files(route_source, self.codex_dir, ("config.toml", "api.config.toml"))
        route_status = self.status_for_path(route_name, route_source)
        if route_status.mode == "api":
            self._normalize_active_api_route(route_name)
        self._ensure_file_auth_store(self.codex_dir / "config.toml")
        self.write_last_mix(auth_name, route_name)
        return backup

    def delete_profile(self, name: str) -> Path:
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
        target.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["CODEX_HOME"] = str(target)
        return subprocess.call(["codex", "login"], env=env)

    def route_custom(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        provider: str = "custom",
        wire_api: str = "responses",
    ) -> Path:
        if not base_url.strip():
            raise ValueError("base_url is required")
        if not model.strip():
            raise ValueError("model is required")
        if not api_key.strip():
            raise ValueError("api_key is required")
        if not provider.strip():
            raise ValueError("provider is required")

        backup = self.backup_current()
        config_path = self.codex_dir / "config.toml"
        config = read_text(config_path)
        rewritten = rewrite_config_for_custom_route(
            config,
            provider=provider.strip(),
            base_url=base_url.strip(),
            model=model.strip(),
            api_key=api_key.strip(),
            wire_api=wire_api.strip() or "responses",
        )
        atomic_write(config_path, rewritten)
        return backup

    def route_official(self, *, model: str | None = None, provider: str = "OpenAI") -> Path:
        if not provider.strip():
            raise ValueError("provider is required")
        backup = self.backup_current()
        config_path = self.codex_dir / "config.toml"
        config = read_text(config_path)
        rewritten = rewrite_config_for_official_route(
            config,
            provider=provider.strip(),
            model=model.strip() if model else None,
        )
        atomic_write(config_path, rewritten)
        return backup

    def restart_codex(self) -> int:
        quit_code = subprocess.call(["osascript", "-e", 'tell application "Codex" to quit'])
        time.sleep(1)
        open_code = subprocess.call(["open", "-a", "Codex"])
        return quit_code or open_code

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
        provider = find_toml_scalar(combined, "model_provider")
        return ProfileStatus(
            name=name,
            path=path,
            exists=path.exists(),
            mode=detect_mode(combined, auth),
            model=find_toml_scalar(combined, "model"),
            provider=provider,
            base_url=find_provider_scalar(combined, provider, "base_url"),
            auth_present=(path / "auth.json").exists(),
            auth_mode=auth.get("auth_mode") if isinstance(auth, dict) else None,
            config_present=config_path.exists(),
            config_empty=config_path.exists() and not config.strip(),
            api_config_present=api_config_path.exists(),
        )

    def _copy_profile_files(self, source: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        self._copy_named_files(source, target, PROFILE_FILES)

    def _copy_named_files(self, source: Path, target: Path, names: tuple[str, ...]) -> None:
        target.mkdir(parents=True, exist_ok=True)
        for name in names:
            src = source / name
            if src.exists():
                shutil.copy2(src, target / name)

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
        )
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
    api_key: str,
    wire_api: str,
) -> str:
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
            lines = set_toml_bool(lines, "requires_openai_auth", True)
            lines = set_toml_string(lines, "wire_api", wire_api)
            lines = set_toml_string(lines, "experimental_bearer_token", api_key)
            lines = remove_toml_key(lines, "env_key")
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
                    "requires_openai_auth = true\n",
                    f'wire_api = "{escape_toml_string(wire_api)}"\n',
                    f'experimental_bearer_token = "{escape_toml_string(api_key)}"\n',
                ],
            )
        )
    return render_toml_sections(updated)


def rewrite_config_for_official_route(text: str, *, provider: str, model: str | None) -> str:
    sections = split_toml_sections(text)
    updated: list[tuple[str, list[str]]] = []
    for section, lines in sections:
        lines = list(lines)
        if section == "":
            lines = set_toml_string(lines, "model_provider", provider)
            if model:
                lines = set_toml_string(lines, "model", model)
            lines = set_toml_string(lines, "preferred_auth_method", "chatgpt")
        elif section.startswith("[model_providers.") and section != f"[model_providers.{provider}]":
            lines = remove_toml_key(lines, "experimental_bearer_token")
        updated.append((section, lines))
    return render_toml_sections(updated)


def rewrite_config_provider_name(text: str, *, old_provider: str, new_provider: str) -> str:
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
            lines = remove_toml_key(lines, "requires_openai_auth")
            lines = remove_toml_key(lines, "experimental_bearer_token")
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


def find_toml_section(text: str, provider: str) -> str:
    target = f"[model_providers.{provider}]"
    for section, lines in split_toml_sections(text):
        if section == target:
            return "".join(lines)
    return ""


def safe_provider_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip())
    cleaned = cleaned.strip("-_")
    return cleaned or "custom"


def route_matches_active(candidate: ProfileStatus, active: ProfileStatus) -> bool:
    if not candidate.config_present or candidate.config_empty:
        return False
    if candidate.base_url or active.base_url:
        return candidate.base_url == active.base_url and candidate.model == active.model
    return candidate.provider == active.provider and candidate.model == active.model


def detect_mode(config_text: str, auth: dict) -> str:
    if "experimental_bearer_token =" in config_text:
        return "hybrid" if auth.get("tokens") else "api"
    if 'env_key = "OPENAI_API_KEY"' in config_text or "env_key =" in config_text:
        return "hybrid" if auth.get("tokens") else "api"
    if "requires_openai_auth = true" in config_text:
        return "auth"
    if auth.get("tokens"):
        return "auth"
    return "unknown"


def strip_deleted_stamp(name: str) -> str:
    parts = name.rsplit("-", 2)
    if len(parts) == 3 and len(parts[1]) == 8 and len(parts[2]) == 6:
        return parts[0]
    return name
