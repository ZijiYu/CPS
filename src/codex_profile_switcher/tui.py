from __future__ import annotations

import curses
import shlex
import textwrap
from urllib.parse import urlparse

from .core import ProfileStore, ProfileStatus


LOGO = [
    "╔════════════════════════════════════════════════════════════════╗",
    "║                                                                ║",
    "║   ██████╗ ██████╗ ███████╗                                     ║",
    "║  ██╔════╝ ██╔══██╗██╔════╝                                     ║",
    "║  ██║      ██████╔╝███████╗                                     ║",
    "║  ██║      ██╔═══╝ ╚════██║                                     ║",
    "║  ╚██████╗ ██║     ███████║                                     ║",
    "║   ╚═════╝ ╚═╝     ╚══════╝                                     ║",
    "║                                                                ║",
    "║   Codex Profile Switcher                                       ║",
    "║                                                                ║",
    "╚════════════════════════════════════════════════════════════════╝",
    "",
    "  Version: 1.0.3  |  https://github.com/ZijiYu/codex-profiles",
]

COMPACT_LOGO = [
    "CPS - Codex Profile Switcher",
    "Version: 1.0.3 | https://github.com/ZijiYu/codex-profiles",
]


def run_tui(store: ProfileStore) -> None:
    curses.wrapper(lambda screen: App(screen, store).run())


class App:
    def __init__(self, screen, store: ProfileStore) -> None:
        self.screen = screen
        self.store = store
        self.selected = 0
        self.focus = "auth"
        self.auth_selected = 0
        self.route_selected = 0
        self.chosen_auth, self.chosen_route = store.initial_mix_selection()
        self.command = ""
        self.history = ["Tab changes column. Enter selects. * is chosen, > is cursor. m apply, R restart."]
        self.show_help = False

    def run(self) -> None:
        curses.curs_set(0)
        self.screen.keypad(True)
        while True:
            self.draw()
            key = self.screen.getch()
            if key == curses.KEY_RESIZE:
                continue
            if key == 3:
                return
            if key in (curses.KEY_UP,):
                self.move_selection(-1)
            elif key in (curses.KEY_DOWN,):
                self.move_selection(1)
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT, 9):
                self.toggle_focus()
            elif key in (10, 13, curses.KEY_ENTER):
                self.submit()
            elif key in (27,):
                self.command = ""
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.command = self.command[:-1]
            elif key == ord("?"):
                self.show_help = not self.show_help
            elif key == ord("q") and not self.command:
                return
            elif key == ord("r") and not self.command:
                self.log("Refreshed profile state.")
            elif key == ord("m") and not self.command:
                self.mix_chosen()
            elif key == ord("R") and not self.command:
                self.restart_codex()
            elif 32 <= key <= 126:
                self.command += chr(key)

    def draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        active = self.store.active_status()
        profiles = [self.store.profile_status(name) for name in self.store.list_profiles()]
        deleted = self.store.list_deleted()
        logo_height = self.draw_logo(width, height)
        top = logo_height + 1

        self.draw_header(top, width, active)
        content_top = top + 4
        left_col = 2
        gap = 4
        left_width = max(34, min(58, width - left_col - gap - 34))
        activity_col = left_col + left_width + gap
        self.draw_sidebar(content_top, left_col, left_width, height, profiles, deleted)
        if activity_col < width - 20:
            self.draw_activity(content_top, activity_col, height, width)
        self.draw_composer(height, width)
        self.screen.refresh()

    def draw_logo(self, width: int, height: int) -> int:
        if height < 18:
            lines = COMPACT_LOGO[:1]
        elif width >= 70:
            lines = LOGO
        else:
            lines = COMPACT_LOGO

        for y, line in enumerate(lines):
            if y >= height - 6:
                break
            x = max(0, (width - len(line)) // 2)
            attr = curses.A_BOLD if y in (0, len(lines) - 1) else curses.A_NORMAL
            self.add(y, x, line, attr)
        return min(len(lines), max(0, height - 6))

    def draw_header(self, row: int, width: int, active: ProfileStatus) -> None:
        self.add(row, 0, " " * max(0, width - 1), curses.A_REVERSE)
        label = f" Codex Profile Switcher  active={active.mode}  model={active.model or '-'} "
        self.add(row, 1, label[: max(0, width - 2)], curses.A_REVERSE | curses.A_BOLD)
        self.add(row + 1, 2, "Saved profiles live in ~/.codex-profiles. Active Desktop config lives in ~/.codex.")
        self.add(row + 2, 2, "Shortcuts: Tab column  Enter select  m apply  R restart  / command  ? help  q quit")

    def draw_sidebar(
        self,
        row: int,
        col: int,
        panel_width: int,
        height: int,
        profiles: list[ProfileStatus],
        deleted: list[str],
    ) -> None:
        next_row = self.draw_mix_columns(row, col, panel_width, profiles)
        deleted_row = min(next_row + 1, max(row, height - 9))
        self.draw_deleted(deleted_row, col, panel_width, height, deleted)

    def draw_mix_columns(self, row: int, col: int, panel_width: int, profiles: list[ProfileStatus]) -> int:
        self.add(
            row,
            col,
            "Auth",
            curses.A_BOLD | (curses.A_REVERSE if self.focus == "auth" else curses.A_NORMAL),
        )
        auth_width = max(16, min(26, panel_width // 2 - 1))
        route_width = max(16, panel_width - auth_width - 3)
        route_col = col + auth_width + 2
        self.add(
            row,
            route_col,
            "API / Route",
            curses.A_BOLD | (curses.A_REVERSE if self.focus == "route" else curses.A_NORMAL),
        )
        if not profiles:
            self.add(row + 2, col, "No profiles yet. Type /init work.")
            return row + 4

        auth_profiles = auth_candidates(profiles)
        route_profiles = route_candidates(profiles)
        self.auth_selected = clamp_index(self.auth_selected, auth_profiles)
        self.route_selected = clamp_index(self.route_selected, route_profiles)
        if self.chosen_auth is None and auth_profiles:
            self.chosen_auth = auth_profiles[self.auth_selected].name
        if self.chosen_route is None and route_profiles:
            self.chosen_route = route_profiles[self.route_selected].name

        max_items = max(len(auth_profiles), len(route_profiles), 1)
        y = row + 2
        for i in range(max_items):
            if i < len(auth_profiles):
                self.draw_mix_item(
                    y + i,
                    col,
                    auth_width,
                    auth_profiles[i],
                    kind="auth",
                    cursor=self.focus == "auth" and i == self.auth_selected,
                    chosen=auth_profiles[i].name == self.chosen_auth,
                )
            if i < len(route_profiles):
                self.draw_mix_item(
                    y + i,
                    route_col,
                    route_width,
                    route_profiles[i],
                    kind="route",
                    cursor=self.focus == "route" and i == self.route_selected,
                    chosen=route_profiles[i].name == self.chosen_route,
                )

        summary_row = y + max_items + 1
        self.draw_mix_preview(summary_row, col, panel_width, profiles)
        return summary_row + 5

    def draw_mix_item(
        self,
        row: int,
        col: int,
        width: int,
        status: ProfileStatus,
        *,
        kind: str,
        cursor: bool,
        chosen: bool,
    ) -> None:
        pointer = ">" if cursor else " "
        star = "*" if chosen else " "
        detail = auth_detail(status) if kind == "auth" else route_detail(status)
        text = f"{pointer}{star} {status.name}  {detail}"
        attr = curses.A_REVERSE if cursor else curses.A_NORMAL
        self.add(row, col, text.ljust(width)[:width], attr)

    def draw_mix_preview(self, row: int, col: int, panel_width: int, profiles: list[ProfileStatus]) -> None:
        by_name = {status.name: status for status in profiles}
        auth = by_name.get(self.chosen_auth or "")
        route = by_name.get(self.chosen_route or "")
        self.add(row, col, "Selected structure:", curses.A_BOLD)
        self.add(row + 1, col, f"auth.json      <- {self.chosen_auth or '-'} ({auth_detail(auth) if auth else '-'})"[:panel_width])
        self.add(row + 2, col, f"config.toml    <- {self.chosen_route or '-'} ({route_detail(route) if route else '-'})"[:panel_width])
        self.add(row + 3, col, "m Apply selected mix   R Restart Codex"[:panel_width], curses.A_DIM)

    def draw_deleted(self, row: int, col: int, panel_width: int, height: int, deleted: list[str]) -> None:
        if row >= height - 4:
            return
        self.add(row, col, "Deleted", curses.A_BOLD)
        if not deleted:
            self.add(row + 2, col, "none")
            return
        max_items = max(1, height - row - 6)
        for i, name in enumerate(deleted[:max_items]):
            self.add(row + 2 + i, col, f" {name}"[:panel_width])
        if len(deleted) > max_items:
            self.add(row + 2 + max_items, col, f" ... +{len(deleted) - max_items} more"[:panel_width])
        self.add(min(height - 4, row + 3 + min(len(deleted), max_items)), col, "/restore <name>", curses.A_DIM)

    def draw_activity(self, row: int, col: int, height: int, width: int) -> None:
        available_width = max(20, width - col - 2)
        bottom = height - 5
        self.add(row, col, "Activity", curses.A_BOLD)
        lines: list[str] = []
        if self.show_help:
            lines.extend(
                [
                    "Main flow",
                    "  Tab / Left / Right      switch Auth and API / Route columns",
                    "  Up / Down               move cursor in current column",
                    "  Enter                   choose the current item",
                    "  m                       apply chosen Auth + API / Route to ~/.codex",
                    "  R                       restart Codex Desktop",
                    "",
                    "Profile management",
                    "  /status                 show active and profile structure",
                    "  /list                   list profiles",
                    "  /init auth <name>      create Auth profile and run codex login",
                    "  /init route <name>     create API / Route profile from active ~/.codex",
                    "  /login <profile>        login into a profile directory",
                    "  /delete <profile>       move profile into deleted/",
                    "  /deleted                list deleted profiles",
                    "  /restore <deleted> [as] restore a deleted profile",
                    "",
                    "Advanced commands",
                    "  /mix <auth> <route>     apply a mix directly",
                    "  /route custom ...       edit active route without replacing auth.json",
                    "  /route official ...     switch active route back to official",
                    "  /init full <name>      snapshot current ~/.codex as a full profile",
                    "  /use <profile>          replace ~/.codex with a full profile",
                    "  /save <profile>         legacy alias for /init full",
                    "  /path <profile>         print profile path",
                    "  /help                   toggle this help",
                    "  /quit                   exit",
                ]
            )
        else:
            lines.extend(self.history[-80:])

        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(textwrap.wrap(line, available_width) or [""])
        visible = wrapped[-max(1, bottom - row - 2) :]
        for i, line in enumerate(visible):
            self.add(row + 2 + i, col, line)

    def draw_composer(self, height: int, width: int) -> None:
        y = height - 3
        self.add(y - 1, 0, "-" * max(0, width - 1))
        prompt = "> "
        text = self.command
        hint = "Tab columns, Enter select, m apply, R restart"
        if not text:
            self.add(y, 2, prompt + hint, curses.A_DIM)
        else:
            self.add(y, 2, prompt + text)
        self.add(y + 1, 2, "Empty Enter selects current item. Type a command to submit. Esc clears input.")

    def draw_status(self, row: int, col: int, title: str, status: ProfileStatus) -> None:
        marker = {"api": "[API]", "auth": "[AUTH]", "hybrid": "[HYB]"}.get(status.mode, "[?]")
        self.add(row, col, f"{title} {marker}", curses.A_BOLD)
        self.add(row + 1, col, f"path: {status.path}")
        self.add(row + 2, col, f"model: {status.model or '-'}")
        self.add(row + 3, col, f"provider: {status.provider or '-'}")
        self.add(row + 4, col, f"base_url: {status.base_url or '-'}")
        auth = "yes" if status.auth_present else "no"
        config_state = "missing"
        if status.config_present:
            config_state = "empty" if status.config_empty else "ok"
        self.add(
            row + 5,
            col,
            f"config: {config_state}  api.config: {'yes' if status.api_config_present else 'no'}  auth: {auth}/{status.auth_mode or '-'}",
        )

    def config_state(self, status: ProfileStatus) -> str:
        if not status.config_present:
            return "missing"
        return "empty" if status.config_empty else "ok"

    def auth_state(self, status: ProfileStatus) -> str:
        if status.mode == "api":
            return "ignored" if status.auth_present else "-"
        if status.mode == "hybrid":
            return "preserved" if status.auth_present else "missing"
        if status.mode == "auth":
            return "used" if status.auth_present else "missing"
        return status.auth_mode or ("present" if status.auth_present else "-")

    def add(self, y: int, x: int, text: str, attr: int = curses.A_NORMAL) -> None:
        height, width = self.screen.getmaxyx()
        if y < 0 or y >= height or x >= width:
            return
        self.screen.addstr(y, x, text[: max(0, width - x - 1)], attr)

    def move_selection(self, delta: int) -> None:
        profiles = [self.store.profile_status(name) for name in self.store.list_profiles()]
        candidates = auth_candidates(profiles) if self.focus == "auth" else route_candidates(profiles)
        if not candidates:
            return
        if self.focus == "auth":
            self.auth_selected = (self.auth_selected + delta) % len(candidates)
        else:
            self.route_selected = (self.route_selected + delta) % len(candidates)

    def toggle_focus(self) -> None:
        self.focus = "route" if self.focus == "auth" else "auth"

    def submit(self) -> None:
        command = self.command.strip()
        self.command = ""
        if command:
            self.run_command(command)
            return
        self.choose_current()

    def choose_current(self) -> None:
        profiles = [self.store.profile_status(name) for name in self.store.list_profiles()]
        if self.focus == "auth":
            candidates = auth_candidates(profiles)
            if candidates:
                self.auth_selected = clamp_index(self.auth_selected, candidates)
                self.chosen_auth = candidates[self.auth_selected].name
                self.log(f"Chosen auth: {self.chosen_auth}")
        else:
            candidates = route_candidates(profiles)
            if candidates:
                self.route_selected = clamp_index(self.route_selected, candidates)
                self.chosen_route = candidates[self.route_selected].name
                self.log(f"Chosen route: {self.chosen_route}")

    def run_command(self, command: str) -> None:
        self.log(f"> {redact_command(command)}")
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            self.log(f"Parse failed: {exc}")
            return
        if not parts:
            return
        name = parts[0].lower()
        args = parts[1:]
        if name in {"/quit", "/exit", "quit", "exit"}:
            raise SystemExit
        if name in {"/help", "help"}:
            self.show_help = not self.show_help
            return
        self.show_help = False
        if name in {"/status", "status"}:
            self.log_status()
            return
        if name in {"/list", "list"}:
            profiles = ", ".join(self.store.list_profiles()) or "none"
            self.log(f"Profiles: {profiles}")
            return
        if name in {"/deleted", "deleted"}:
            deleted_profiles = self.store.list_deleted()
            if not deleted_profiles:
                self.log("Deleted profiles: none")
            else:
                self.log(f"Deleted profiles ({len(deleted_profiles)}):")
                for deleted_name in deleted_profiles:
                    self.log(f"  {deleted_name}  -> /restore {deleted_name}")
            return
        if name in {"/use", "use"}:
            self.require_args(name, args, self.use_profile)
            return
        if name in {"/login", "login"}:
            self.require_args(name, args, self.login_profile)
            return
        if name in {"/save", "save"}:
            self.require_args(name, args, self.save_profile)
            return
        if name in {"/init", "init"}:
            self.init_profile_command(args)
            return
        if name in {"/delete", "delete", "/remove", "remove"}:
            self.require_args(name, args, self.delete_profile)
            return
        if name in {"/restore", "restore"}:
            if not args:
                self.log("Usage: /restore <deleted-profile> [profile-name]")
            else:
                self.restore_profile(args[0], args[1] if len(args) > 1 else None)
            return
        if name in {"/path", "path"}:
            if not args:
                self.log("Usage: /path <profile>")
            else:
                self.log(str(self.store.profile_dir(args[0])))
            return
        if name in {"/route", "route"}:
            self.route(args)
            return
        if name in {"/mix", "mix"}:
            if len(args) != 2:
                self.log("Usage: /mix <auth-profile> <route-profile>")
            else:
                self.mix_profiles(args[0], args[1])
            return
        self.log(f"Unknown command: {command}. Type /help.")

    def require_args(self, command: str, args: list[str], fn) -> None:
        if not args:
            self.log(f"Usage: {command} <profile>")
            return
        fn(args[0])

    def use_profile(self, name: str) -> None:
        try:
            backup = self.store.use_profile(name)
        except Exception as exc:
            self.log(f"Switch failed: {exc}")
            return
        self.log(f"Switched to {name}.")
        self.log(f"Backup: {backup}")
        self.log("Restart Codex Desktop so it reloads ~/.codex.")

    def login_profile(self, name: str) -> None:
        self.screen.clear()
        self.screen.refresh()
        code = self.store.login_profile(name)
        self.log(f"codex login {name} exited with {code}.")

    def save_profile(self, name: str) -> None:
        try:
            path = self.store.save_profile(name)
        except Exception as exc:
            self.log(f"Save failed: {exc}")
            return
        self.log(f"Saved active config into {path}.")

    def init_profile(self, name: str) -> None:
        try:
            path = self.store.init_profile(name)
        except Exception as exc:
            self.log(f"Init failed: {exc}")
            return
        self.log(f"Initialized {path} from active config.")

    def init_profile_command(self, args: list[str]) -> None:
        if not args:
            self.log("Usage: /init auth <name> | /init route <name> | /init full <name>")
            return
        if len(args) == 1:
            self.init_profile(args[0])
            return
        kind, profile = args[0], args[1]
        if kind == "auth":
            self.screen.clear()
            self.screen.refresh()
            try:
                code = self.store.create_auth_profile(profile)
            except Exception as exc:
                self.log(f"Init failed: {exc}")
                return
            self.log(f"Initialized auth profile {profile}; codex login exited with {code}.")
            return
        try:
            if kind == "route":
                path = self.store.init_route_profile(profile)
            elif kind == "full":
                path = self.store.init_profile(profile)
            else:
                self.log("Usage: /init auth <name> | /init route <name> | /init full <name>")
                return
        except Exception as exc:
            self.log(f"Init failed: {exc}")
            return
        self.log(f"Initialized {kind} profile at {path}.")

    def delete_profile(self, name: str) -> None:
        try:
            path = self.store.delete_profile(name)
        except Exception as exc:
            self.log(f"Delete failed: {exc}")
            return
        self.log(f"Deleted {name}.")
        self.log(f"Moved to {path}. Use /restore {path.name} to recover.")

    def restore_profile(self, deleted_name: str, profile_name: str | None) -> None:
        try:
            path = self.store.restore_profile(deleted_name, profile_name)
        except Exception as exc:
            self.log(f"Restore failed: {exc}")
            return
        self.log(f"Restored profile to {path}.")

    def mix_chosen(self) -> None:
        if not self.chosen_auth or not self.chosen_route:
            self.log("Choose one auth and one route first.")
            return
        self.mix_profiles(self.chosen_auth, self.chosen_route)

    def mix_profiles(self, auth_name: str, route_name: str) -> None:
        try:
            backup = self.store.mix_profiles(auth_name, route_name)
        except Exception as exc:
            self.log(f"Mix failed: {exc}")
            return
        self.chosen_auth = auth_name
        self.chosen_route = route_name
        self.log(f"Mixed auth={auth_name} route={route_name}.")
        self.log(f"Backup: {backup}")
        self.log("Restart Codex Desktop so it reloads ~/.codex.")

    def restart_codex(self) -> None:
        self.screen.clear()
        self.screen.refresh()
        try:
            code = self.store.restart_codex()
        except Exception as exc:
            self.log(f"Restart failed: {exc}")
            return
        self.log(f"Restart Codex exited with {code}.")

    def route(self, args: list[str]) -> None:
        if not args:
            self.log("Usage: /route custom --base-url URL --model MODEL --api-key KEY")
            self.log("   or: /route official [--model MODEL] [--provider OpenAI]")
            return
        mode = args[0].lower()
        try:
            options = parse_options(args[1:])
        except ValueError as exc:
            self.log(f"Route failed: {exc}")
            return
        if mode == "custom":
            self.route_custom(options)
            return
        if mode == "official":
            self.route_official(options)
            return
        self.log("Usage: /route custom|official ...")

    def route_custom(self, options: dict[str, str]) -> None:
        base_url = options.get("--base-url")
        model = options.get("--model")
        api_key = options.get("--api-key")
        if not base_url or not model or not api_key:
            self.log("Usage: /route custom --base-url URL --model MODEL --api-key KEY")
            return
        provider = options.get("--provider", "custom")
        wire_api = options.get("--wire-api", "responses")
        try:
            backup = self.store.route_custom(
                base_url=base_url,
                model=model,
                api_key=api_key,
                provider=provider,
                wire_api=wire_api,
            )
        except Exception as exc:
            self.log(f"Route failed: {exc}")
            return
        self.log(f"Routed to custom provider {provider}.")
        self.log(f"Model: {model}; base_url: {base_url}")
        self.log("auth.json preserved.")
        self.log(f"Backup: {backup}")
        self.log("Restart Codex Desktop so it reloads ~/.codex.")

    def route_official(self, options: dict[str, str]) -> None:
        model = options.get("--model")
        provider = options.get("--provider", "OpenAI")
        try:
            backup = self.store.route_official(model=model, provider=provider)
        except Exception as exc:
            self.log(f"Route failed: {exc}")
            return
        self.log(f"Routed to official provider {provider}.")
        if model:
            self.log(f"Model: {model}")
        self.log("auth.json preserved.")
        self.log(f"Backup: {backup}")
        self.log("Restart Codex Desktop so it reloads ~/.codex.")

    def log_status(self) -> None:
        statuses = [self.store.active_status()]
        statuses.extend(self.store.profile_status(name) for name in self.store.list_profiles())
        for status in statuses:
            self.log(
                f"{status.name}: {status.mode}, model={status.model or '-'}, "
                f"config={self.config_state(status)}, auth={self.auth_state(status)}"
            )

    def log(self, message: str) -> None:
        self.history.append(message)
        self.history = self.history[-120:]


def parse_options(args: list[str]) -> dict[str, str]:
    options: dict[str, str] = {}
    index = 0
    while index < len(args):
        key = args[index]
        if not key.startswith("--"):
            raise ValueError(f"unexpected argument: {key}")
        if index + 1 >= len(args) or args[index + 1].startswith("--"):
            raise ValueError(f"missing value for {key}")
        options[key] = args[index + 1]
        index += 2
    return options


def auth_candidates(profiles: list[ProfileStatus]) -> list[ProfileStatus]:
    return [status for status in profiles if status.auth_present and not status.base_url]


def route_candidates(profiles: list[ProfileStatus]) -> list[ProfileStatus]:
    return [
        status
        for status in profiles
        if status.config_present and not status.config_empty and status.provider
    ]


def clamp_index(index: int, items: list[object]) -> int:
    if not items:
        return 0
    return max(0, min(index, len(items) - 1))


def route_detail(status: ProfileStatus) -> str:
    if status is None:
        return "-"
    route_type = "api" if status.mode in {"api", "hybrid"} and status.base_url else "official"
    if status.base_url:
        parsed = urlparse(status.base_url)
        endpoint = parsed.netloc or status.base_url
    elif status.provider:
        endpoint = status.provider
    else:
        endpoint = "-"
    return f"{route_type}:{endpoint} {status.model or '-'}"


def auth_detail(status: ProfileStatus | None) -> str:
    if status is None:
        return "-"
    if not status.auth_present:
        return "auth:no"
    return f"auth:{status.auth_mode or 'file'}"


def redact_command(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        return command
    redacted: list[str] = []
    hide_next = False
    for part in parts:
        if hide_next:
            redacted.append("***")
            hide_next = False
            continue
        redacted.append(part)
        if part == "--api-key":
            hide_next = True
    return " ".join(redacted)
