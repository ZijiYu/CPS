from __future__ import annotations

import curses
import textwrap

from .core import ProfileStore, ProfileStatus


LOGO = [
    "╔════════════════════════════════════════════════════════════════╗",
    "║                                                                ║",
    "║   ██████╗ ██████╗ ██╗  ██╗                                     ║",
    "║  ██╔════╝ ██╔══██╗╚██╗██╔╝                                     ║",
    "║  ██║      ██████╔╝ ╚███╔╝                                      ║",
    "║  ██║      ██╔═══╝  ██╔██╗                                      ║",
    "║  ╚██████╗ ██║     ██╔╝ ██╗                                     ║",
    "║   ╚═════╝ ╚═╝     ╚═╝  ╚═╝                                     ║",
    "║                                                                ║",
    "║   Codex Profiles                                               ║",
    "║                                                                ║",
    "╚════════════════════════════════════════════════════════════════╝",
    "",
    "  Version: 1.0  |  https://github.com/ZijiYu/codex-profiles",
]

COMPACT_LOGO = [
    "CPX - Codex Profiles",
    "Version: 1.0 | https://github.com/ZijiYu/codex-profiles",
]


def run_tui(store: ProfileStore) -> None:
    curses.wrapper(lambda screen: App(screen, store).run())


class App:
    def __init__(self, screen, store: ProfileStore) -> None:
        self.screen = screen
        self.store = store
        self.selected = 0
        self.command = ""
        self.history = ["Type /help for commands. Up/Down selects a profile, Enter switches it."]
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
            elif key in (9,):
                self.move_selection(1)
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
        left_width = min(34, max(24, width // 3))
        self.draw_sidebar(content_top, 2, left_width, height, profiles, deleted)
        self.draw_activity(content_top, min(40, max(36, width // 3 + 5)), height, width)
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
        self.add(row + 2, 2, "Shortcuts: Enter switch  / command  ? help  r refresh  q quit")

    def draw_sidebar(
        self,
        row: int,
        col: int,
        panel_width: int,
        height: int,
        profiles: list[ProfileStatus],
        deleted: list[str],
    ) -> None:
        next_row = self.draw_profiles(row, col, panel_width, profiles)
        deleted_row = min(next_row + 1, max(row, height - 9))
        self.draw_deleted(deleted_row, col, panel_width, height, deleted)

    def draw_profiles(self, row: int, col: int, panel_width: int, profiles: list[ProfileStatus]) -> int:
        self.add(row, col, "Profiles", curses.A_BOLD)
        if not profiles:
            self.add(row + 2, col, "No profiles yet. Type /init work.")
            return row + 4

        self.selected = min(self.selected, len(profiles) - 1)
        y = row + 2
        for i, status in enumerate(profiles):
            attr = curses.A_REVERSE if i == self.selected else curses.A_NORMAL
            marker = {"api": "API", "auth": "AUTH"}.get(status.mode, "?")
            title = f" {status.name} [{marker}]"
            self.add(y, col, title.ljust(panel_width)[:panel_width], attr | curses.A_BOLD)
            self.add(y + 1, col + 2, f"model    {status.model or '-'}"[: panel_width - 2])
            self.add(y + 2, col + 2, f"config   {self.config_state(status)}"[: panel_width - 2])
            self.add(y + 3, col + 2, f"auth     {self.auth_state(status)}"[: panel_width - 2])
            y += 5
        return y

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
                    "/status                 show active and saved profile state",
                    "/list                   list profile names",
                    "/use <profile>          copy profile into ~/.codex",
                    "/login <profile>        run codex login with CODEX_HOME set",
                    "/save <profile>         save active ~/.codex into profile",
                    "/init <profile>         create profile from active ~/.codex",
                    "/delete <profile>       move profile into deleted/",
                    "/deleted                list deleted profiles",
                    "/restore <deleted> [as] restore a deleted profile",
                    "/path <profile>         print profile path",
                    "/help                   toggle this help",
                    "/quit                   exit",
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
        hint = "type /help, /use work, /delete worek, /restore name"
        if not text:
            self.add(y, 2, prompt + hint, curses.A_DIM)
        else:
            self.add(y, 2, prompt + text)
        self.add(y + 1, 2, "Enter submits. Empty Enter switches selected profile. Esc clears input.")

    def draw_status(self, row: int, col: int, title: str, status: ProfileStatus) -> None:
        marker = {"api": "[API]", "auth": "[AUTH]"}.get(status.mode, "[?]")
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
        if status.mode == "auth":
            return "used" if status.auth_present else "missing"
        return status.auth_mode or ("present" if status.auth_present else "-")

    def add(self, y: int, x: int, text: str, attr: int = curses.A_NORMAL) -> None:
        height, width = self.screen.getmaxyx()
        if y < 0 or y >= height or x >= width:
            return
        self.screen.addstr(y, x, text[: max(0, width - x - 1)], attr)

    def move_selection(self, delta: int) -> None:
        profiles = self.store.list_profiles()
        if not profiles:
            self.selected = 0
            return
        self.selected = (self.selected + delta) % len(profiles)

    def submit(self) -> None:
        command = self.command.strip()
        self.command = ""
        if command:
            self.run_command(command)
            return
        profiles = self.store.list_profiles()
        if profiles:
            self.use_profile(profiles[self.selected])

    def run_command(self, command: str) -> None:
        self.log(f"> {command}")
        parts = command.split()
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
            self.require_args(name, args, self.init_profile)
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
