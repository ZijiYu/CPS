from __future__ import annotations

import curses
import shlex
import textwrap
from urllib.parse import urlparse

from .core import DEFAULT_ACTIVE_PROVIDER, DEFAULT_ENV_KEY, ProfileStore, ProfileStatus


API_FORM_FIELDS = [
    {"key": "name", "label": "Name", "placeholder": "work", "required": True, "secret": False},
    {"key": "base_url", "label": "Base URL", "placeholder": "https://api.example.com/v1", "required": True, "secret": False},
    {"key": "model", "label": "Model", "placeholder": "gpt-5.5", "required": True, "secret": False},
    {"key": "env_key", "label": "Env Key", "placeholder": DEFAULT_ENV_KEY, "required": False, "secret": False},
    {"key": "provider", "label": "Provider", "placeholder": DEFAULT_ACTIVE_PROVIDER, "required": False, "secret": False},
    {"key": "wire_api", "label": "Wire API", "placeholder": "responses", "required": False, "secret": False},
]


AUTH_FORM_FIELDS = [
    {"key": "name", "label": "Name", "placeholder": "personal", "required": True, "secret": False},
]

STYLE_NORMAL = curses.A_NORMAL
STYLE_BAR = curses.A_BOLD
STYLE_FOCUS = curses.A_BOLD | curses.A_UNDERLINE
STYLE_PANEL = curses.A_BOLD
STYLE_INPUT = curses.A_BOLD | curses.A_UNDERLINE
STYLE_ERROR = curses.A_BOLD | curses.A_UNDERLINE
TRUE_BLACK_BACKGROUND = "\033]10;#ffffff\007\033]11;#000000\007\033[38;2;255;255;255m\033[48;2;0;0;0m"
TIER_COMPACT = "compact"
TIER_NORMAL = "normal"
TIER_SPACIOUS = "spacious"


MENU_ITEMS = [
    ("New Gateway Route", "Create a gateway forwarding profile", "new_api"),
    ("New Auth Login", "Create an auth profile and run codex login", "new_auth"),
    ("Show Status", "Show active and saved profile state", "status"),
    ("Run Doctor", "Diagnose active config and saved profiles", "doctor"),
    ("Restart Codex", "Quit and reopen Codex Desktop", "restart"),
    ("Help", "Open the full help page", "help"),
    ("Back", "Return to the main selector", "back"),
]


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
    "  Version: 1.0.5  |  https://github.com/ZijiYu/CPS",
]

COMPACT_LOGO = [
    "CPS - Codex Profile Switcher",
    "Version: 1.0.5 | https://github.com/ZijiYu/CPS",
]

MEDIUM_LOGO = [
    "╔════════════════════════════════════════════════════════════════╗",
    "║   ██████╗ ██████╗ ███████╗                                    ║",
    "║   Codex Profile Switcher                                      ║",
    "╚════════════════════════════════════════════════════════════════╝",
]


def run_tui(store: ProfileStore) -> None:
    curses.wrapper(lambda screen: App(screen, store).run())


def init_terminal_style(screen) -> None:
    global STYLE_NORMAL, STYLE_BAR, STYLE_FOCUS, STYLE_PANEL, STYLE_INPUT, STYLE_ERROR
    try:
        print(TRUE_BLACK_BACKGROUND, end="", flush=True)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_CYAN, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            STYLE_NORMAL = curses.color_pair(1)
            STYLE_BAR = curses.color_pair(1) | curses.A_BOLD
            STYLE_FOCUS = curses.color_pair(2) | curses.A_BOLD | curses.A_UNDERLINE
            STYLE_PANEL = curses.color_pair(1) | curses.A_BOLD
            STYLE_INPUT = curses.color_pair(2) | curses.A_BOLD | curses.A_UNDERLINE
            STYLE_ERROR = curses.color_pair(3) | curses.A_BOLD | curses.A_UNDERLINE
            screen.bkgd(" ", STYLE_NORMAL)
    except curses.error:
        pass


class App:
    def __init__(self, screen, store: ProfileStore) -> None:
        self.screen = screen
        self.store = store
        self.mode = "main"
        self.focus = "auth"
        self.auth_selected = 0
        self.route_selected = 0
        self.menu_selected = 0
        self.help_scroll = 0
        self.chosen_auth, self.chosen_route = store.initial_mix_selection()
        self.command = ""
        self.api_form = ApiRouteForm()
        self.auth_form = AuthProfileForm()
        self.history = ["Tab changes column. Space selects draft. Enter reviews the draft before applying."]
        self.pending_delete: str | None = None
        self.pending_apply: tuple[str, str] | None = None

    def run(self) -> None:
        curses.curs_set(0)
        self.screen.keypad(True)
        init_terminal_style(self.screen)
        try:
            curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
            curses.mouseinterval(0)
        except curses.error:
            pass
        while True:
            self.draw()
            key = self.screen.getch()
            if key == curses.KEY_RESIZE:
                continue
            if key == curses.KEY_MOUSE:
                self.handle_mouse()
                continue
            if key == 3:
                return
            if self.mode == "api_form":
                self.handle_api_form_key(key)
                continue
            if self.mode == "auth_form":
                self.handle_auth_form_key(key)
                continue
            if self.mode == "menu":
                self.handle_menu_key(key)
                continue
            if self.mode == "help":
                self.handle_help_key(key)
                continue
            if self.pending_apply:
                self.handle_apply_confirmation(key)
                continue
            if self.pending_delete:
                self.handle_delete_confirmation(key)
                continue
            if key in (curses.KEY_UP,):
                self.move_selection(-1)
            elif key in (curses.KEY_DOWN,):
                self.move_selection(1)
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT, 9):
                self.toggle_focus()
            elif key in (10, 13, curses.KEY_ENTER):
                self.submit()
            elif key == ord(" ") and not self.command:
                self.choose_current()
            elif key in (27,):
                self.command = ""
            elif key in (curses.KEY_BACKSPACE, curses.KEY_DC, 127, 8):
                if self.command:
                    self.command = self.command[:-1]
            elif key in (ord("d"), ord("D")) and not self.command:
                self.request_delete_current()
            elif key == ord("?"):
                self.mode = "help"
            elif key in (ord("q"), ord("Q")) and not self.command:
                return
            elif key in (ord("o"), ord("O")) and not self.command:
                self.mode = "menu"
            elif key in (ord("r"), ord("R")) and not self.command:
                self.restart_codex()
            elif 32 <= key <= 126:
                self.command += chr(key)

    def draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        if self.mode == "api_form":
            self.draw_api_form_page(height, width)
        elif self.mode == "auth_form":
            self.draw_auth_form_page(height, width)
        elif self.mode == "menu":
            self.draw_menu_page(height, width)
        elif self.mode == "help":
            self.draw_help_page(height, width)
        else:
            self.draw_main_page(height, width)
        self.screen.refresh()

    def draw_main_page(self, height: int, width: int) -> None:
        active = self.store.active_status()
        profiles = [self.store.profile_status(name) for name in self.store.list_profiles()]
        deleted = self.store.list_deleted()
        active_auth, active_route = self.active_mix()
        tier = layout_tier(height, width)
        logo_height = self.draw_logo(width, height, tier)
        top = logo_height + (1 if logo_height else 0)

        self.draw_header(top, width, active, active_auth, active_route)
        content_top = top + 3
        left_col = 2
        gap = 4 if tier != TIER_COMPACT else 2
        if tier == TIER_COMPACT:
            left_width = max(34, width - left_col - 2)
        elif width >= 104:
            left_width = min(86, max(60, width - left_col - gap - 34))
        else:
            left_width = max(34, width - left_col - 2)
        activity_col = left_col + left_width + gap
        self.draw_sidebar(content_top, left_col, left_width, height, profiles, deleted, active_auth, active_route, tier)
        if tier != TIER_COMPACT and activity_col < width - 20:
            self.draw_activity(content_top, activity_col, height, width)
        self.draw_footer(
            height,
            width,
            main_footer_hint(width, tier),
        )
        if self.pending_apply:
            self.draw_apply_confirmation_panel(height, width)
        elif self.pending_delete:
            self.draw_delete_confirmation_panel(height, width)

    def draw_logo(self, width: int, height: int, tier: str) -> int:
        if tier == TIER_COMPACT:
            lines = [] if height < 26 else COMPACT_LOGO[:1]
        elif tier == TIER_SPACIOUS and width >= 70:
            lines = LOGO
        elif height >= 34 and width >= 70:
            lines = MEDIUM_LOGO
        else:
            lines = COMPACT_LOGO[:1]

        for y, line in enumerate(lines):
            if y >= height - 6:
                break
            x = max(0, (width - len(line)) // 2)
            attr = curses.A_BOLD if y in (0, len(lines) - 1) else curses.A_NORMAL
            self.add(y, x, line, attr)
        return min(len(lines), max(0, height - 6))

    def draw_header(
        self,
        row: int,
        width: int,
        active: ProfileStatus,
        active_auth: str | None,
        active_route: str | None,
    ) -> None:
        status = self.draft_status_label(active_auth, active_route)
        self.add(row, 0, " " * max(0, width - 1), STYLE_BAR)
        label = f" Codex Profile Switcher  active={active.mode} "
        status_col = max(1, width - len(status) - 3)
        self.add(row, 1, label[: max(0, status_col - 2)], STYLE_BAR)
        self.add(row, status_col, status[: max(0, width - status_col - 1)], STYLE_BAR)
        active_text = f"Active: auth={active_auth or '-'}  gateway={active_route or '-'}  model={active.model or '-'}"
        self.add(row + 1, 2, active_text[: max(0, width - 4)], curses.A_DIM)

    def draw_sidebar(
        self,
        row: int,
        col: int,
        panel_width: int,
        height: int,
        profiles: list[ProfileStatus],
        deleted: list[str],
        active_auth: str | None,
        active_route: str | None,
        tier: str,
    ) -> None:
        next_row = self.draw_mix_columns(row, col, panel_width, height, profiles, active_auth, active_route, tier)
        self.draw_deleted(next_row + 1, col, panel_width, height, deleted)

    def draw_mix_columns(
        self,
        row: int,
        col: int,
        panel_width: int,
        height: int,
        profiles: list[ProfileStatus],
        active_auth: str | None,
        active_route: str | None,
        tier: str,
    ) -> int:
        self.add(
            row,
            col,
            focus_title("Auth", self.focus == "auth"),
            STYLE_FOCUS if self.focus == "auth" else curses.A_BOLD,
        )
        compact = tier == TIER_COMPACT
        item_height = 1 if compact else 2
        auth_width = max(18 if compact else 24, min(30 if compact else 34, panel_width // 2 - 2))
        gap = 3
        route_width = max(22 if compact else 28, panel_width - auth_width - gap)
        route_col = col + auth_width + gap
        self.add(
            row,
            route_col,
            focus_title("Gateway", self.focus == "route"),
            STYLE_FOCUS if self.focus == "route" else curses.A_BOLD,
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
        preview_rows = 6 if compact else 9
        available_rows = max(1, height - row - preview_rows - 5)
        visible_items = max(1, min(max_items, available_rows // item_height))
        auth_start = scroll_start(self.auth_selected, visible_items, len(auth_profiles))
        route_start = scroll_start(self.route_selected, visible_items, len(route_profiles))
        y = row + 2
        for i in range(visible_items):
            auth_index = auth_start + i
            route_index = route_start + i
            if auth_index < len(auth_profiles):
                status = auth_profiles[auth_index]
                self.draw_mix_item(
                    y + i * item_height,
                    col,
                    auth_width,
                    status,
                    kind="auth",
                    cursor=self.focus == "auth" and auth_index == self.auth_selected,
                    chosen=status.name == self.chosen_auth,
                    active=status.name == active_auth,
                    compact=compact,
                )
            if route_index < len(route_profiles):
                status = route_profiles[route_index]
                self.draw_mix_item(
                    y + i * item_height,
                    route_col,
                    route_width,
                    status,
                    kind="route",
                    cursor=self.focus == "route" and route_index == self.route_selected,
                    chosen=status.name == self.chosen_route,
                    active=status.name == active_route,
                    compact=compact,
                )

        more_row = y + visible_items * item_height
        if auth_start + visible_items < len(auth_profiles):
            self.add(more_row, col, f"... +{len(auth_profiles) - auth_start - visible_items} more"[:auth_width], curses.A_DIM)
        if route_start + visible_items < len(route_profiles):
            self.add(more_row, route_col, f"... +{len(route_profiles) - route_start - visible_items} more"[:route_width], curses.A_DIM)

        summary_row = more_row + (1 if compact else 2)
        self.draw_mix_preview(summary_row, col, panel_width, profiles, tier)
        return summary_row + preview_rows

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
        active: bool,
        compact: bool = False,
    ) -> None:
        pointer = ">" if cursor else " "
        star = "*" if chosen else " "
        badge = item_badge(status, kind, active)
        detail = item_detail(status, kind)
        if compact:
            text = f"{pointer}{star} {status.name:<12} {badge:<8} {detail}"
        else:
            text = f"{pointer}{star} {status.name:<14} {badge}"
        attr = STYLE_FOCUS if cursor else curses.A_BOLD if chosen else curses.A_NORMAL
        self.add(row, col, text.ljust(width)[:width], attr)
        if not compact:
            self.add(row + 1, col + 4, detail[: max(0, width - 4)], curses.A_DIM)

    def draw_mix_preview(self, row: int, col: int, panel_width: int, profiles: list[ProfileStatus], tier: str) -> None:
        by_name = {status.name: status for status in profiles}
        auth = by_name.get(self.chosen_auth or "")
        route = by_name.get(self.chosen_route or "")
        compact = tier == TIER_COMPACT
        self.add(row, col, "Apply preview", curses.A_BOLD)
        self.add(row + 1, col, rule(panel_width), curses.A_DIM)
        self.add(row + 2, col + 2, f"auth.json      <- {self.chosen_auth or '-'} ({auth_detail(auth) if auth else '-'})"[: max(0, panel_width - 2)])
        self.add(row + 3, col + 2, f"config.toml    <- {self.chosen_route or '-'} ({route_detail(route) if route else '-'})"[: max(0, panel_width - 2)])
        if compact:
            if self.selection_needs_apply():
                self.add(row + 4, col + 2, "Enter: review/apply   Space: draft"[: max(0, panel_width - 2)], curses.A_BOLD)
            else:
                self.add(row + 4, col + 2, "No changes pending"[: max(0, panel_width - 2)], curses.A_BOLD)
            return
        self.add(
            row + 4,
            col + 2,
            f"request path   -> {route_effect_label(route, has_auth=bool(self.chosen_auth))}"[: max(0, panel_width - 2)],
        )
        if self.selection_needs_apply():
            hint = "Enter: review and confirm before writing"
            hint_attr = curses.A_BOLD
        else:
            hint = "No changes pending"
            hint_attr = curses.A_BOLD
        self.add(row + 6, col + 2, hint[: max(0, panel_width - 2)], hint_attr)
        self.add(row + 7, col + 2, "Space: change draft only   O: menu"[: max(0, panel_width - 2)], curses.A_DIM)

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
        bottom = height - 3
        self.add(row, col, "Activity", curses.A_BOLD)
        self.add(row + 1, col, rule(available_width, max_width=36), curses.A_DIM)
        visible = render_history(self.history, available_width)[-max(1, bottom - row - 2) :]
        for i, (level, message) in enumerate(visible):
            y = row + 2 + i
            if level:
                self.add(y, col, f"{level:<5}", level_attr(level))
                self.add(y, col + 6, message[: max(0, available_width - 6)])
            else:
                self.add(y, col + 6, message[: max(0, available_width - 6)])

    def draw_footer(self, height: int, width: int, hint: str) -> None:
        y = height - 1
        if self.pending_apply:
            auth_name, route_name = self.pending_apply
            text = f" Apply auth={auth_name} gateway={route_name}? Press y to confirm, n/Esc to cancel"
        elif self.pending_delete:
            text = f" Delete {self.pending_delete}? Press y to confirm, n/Esc to cancel"
        elif self.command:
            text = f" Command: {self.command}"
        else:
            text = f" {hint}"
        self.add(y, 0, " " * max(0, width - 1), STYLE_BAR)
        self.add(y, 2, text[: max(0, width - 4)], STYLE_BAR)

    def draw_apply_confirmation_panel(self, height: int, width: int) -> None:
        if height < 14 or width < 52:
            return
        auth_name, route_name = self.pending_apply or ("-", "-")
        panel_width = min(76, width - 8)
        panel_height = 9
        top = max(2, (height - panel_height) // 2)
        left = max(2, (width - panel_width) // 2)
        self.panel(top, left, panel_width, panel_height, "Review apply")
        self.add(top + 2, left + 3, "This is the only step that writes active config.", curses.A_BOLD)
        self.add(top + 4, left + 5, f"auth.json   <- {auth_name}"[: max(0, panel_width - 8)])
        self.add(top + 5, left + 5, f"config.toml <- {route_name}"[: max(0, panel_width - 8)])
        self.add(top + 7, left + 3, "Y confirm   N/Esc cancel", STYLE_FOCUS)

    def draw_delete_confirmation_panel(self, height: int, width: int) -> None:
        if height < 12 or width < 48:
            return
        name = self.pending_delete or "-"
        panel_width = min(70, width - 8)
        panel_height = 7
        top = max(2, (height - panel_height) // 2)
        left = max(2, (width - panel_width) // 2)
        self.panel(top, left, panel_width, panel_height, "Review delete")
        self.add(top + 2, left + 3, f"Move {name} to ~/.codex-profiles/deleted."[: max(0, panel_width - 6)], curses.A_BOLD)
        self.add(top + 4, left + 3, "Y confirm   N/Esc cancel", STYLE_FOCUS)

    def panel(self, row: int, col: int, width: int, height: int, title: str) -> None:
        top = "╭" + "─" * (width - 2) + "╮"
        mid = "│" + " " * (width - 2) + "│"
        bottom = "╰" + "─" * (width - 2) + "╯"
        self.add(row, col, top, STYLE_PANEL)
        for y in range(row + 1, row + height - 1):
            self.add(y, col, mid, STYLE_PANEL)
        self.add(row + height - 1, col, bottom, STYLE_PANEL)
        self.add(row, col + 2, f" {title} ", STYLE_PANEL)

    def draw_page_title(self, height: int, width: int, title: str, subtitle: str = "") -> int:
        self.add(0, 0, " " * max(0, width - 1), STYLE_BAR)
        self.add(0, 1, f" {title} "[: max(0, width - 2)], STYLE_BAR)
        if subtitle:
            self.add(2, 4, subtitle[: max(0, width - 8)])
        return 4 if subtitle else 2

    def draw_api_form_page(self, height: int, width: int) -> None:
        top = self.draw_page_title(
            height,
            width,
            "New Gateway Route",
            "Create a gateway forwarding profile. Auth is added from the selected login.",
        )
        left = max(2, min(8, width // 10))
        form_width = max(30, min(88, width - left - 4))
        bottom = max(top, height - 2)

        label_width = 12
        value_col = left + label_width + 4
        value_width = max(8, form_width - label_width - 5)
        visible_rows = max(1, bottom - top)
        scroll = clamp_scroll(self.api_form.focus, visible_rows, len(API_FORM_FIELDS))
        for index, field in enumerate(API_FORM_FIELDS[scroll : scroll + visible_rows], start=scroll):
            y = top + index - scroll
            focused = index == self.api_form.focus
            label = field["label"]
            value = self.api_form.values[field["key"]]
            shown = mask_secret(value) if field["secret"] else value
            if not shown and field["placeholder"]:
                shown = field["placeholder"]
                attr = curses.A_DIM
            else:
                attr = STYLE_INPUT if focused else curses.A_NORMAL
            pointer = ">" if focused else " "
            self.add(y, left, f"{pointer} {label}".ljust(label_width), curses.A_BOLD if focused else curses.A_NORMAL)
            self.add(y, value_col, shown.ljust(value_width)[:value_width], attr)

        error = self.api_form.error or ""
        if error and bottom > top:
            self.add(bottom - 1, left, error[:form_width], curses.A_BOLD)
        elif len(API_FORM_FIELDS) > visible_rows:
            self.add(bottom - 1, left, f"Fields {scroll + 1}-{min(len(API_FORM_FIELDS), scroll + visible_rows)} of {len(API_FORM_FIELDS)}"[:form_width], curses.A_DIM)
        self.draw_footer(height, width, "[Enter] Next/Save   [Tab] Next   [Scroll/Up/Down] Move   [Esc] Cancel")

    def draw_auth_form_page(self, height: int, width: int) -> None:
        top = self.draw_page_title(
            height,
            width,
            "New Auth Login",
            "Create an auth profile, then run codex login in that isolated profile.",
        )
        left = max(2, min(8, width // 10))
        form_width = max(30, min(72, width - left - 4))

        field = AUTH_FORM_FIELDS[0]
        value = self.auth_form.values[field["key"]]
        shown = value or field["placeholder"]
        attr = STYLE_INPUT if value else curses.A_DIM
        self.add(top, left, "> Name".ljust(12), curses.A_BOLD)
        self.add(top, left + 16, shown.ljust(form_width - 16)[: max(8, form_width - 16)], attr)

        if self.auth_form.error:
            self.add(top + 2, left, self.auth_form.error[:form_width], curses.A_BOLD)
        self.add(top + 4, left, "After login, the profile appears in the Auth column.", curses.A_DIM)
        self.draw_footer(height, width, "[Enter] Create/Login   [Esc] Cancel")

    def draw_menu_page(self, height: int, width: int) -> None:
        top = self.draw_page_title(height, width, "Menu", "Choose an action. Advanced slash commands still work from the main page.")
        left = max(2, min(8, width // 10))
        item_width = max(24, min(72, width - left - 4))
        content_rows = []
        for index, (label, description, _action) in enumerate(MENU_ITEMS):
            selected = index == self.menu_selected
            pointer = ">" if selected else " "
            content_rows.append((f"{pointer} {label}".ljust(item_width)[:item_width], STYLE_FOCUS if selected else curses.A_NORMAL))
            content_rows.append(("  " + description[: max(0, item_width - 2)], curses.A_DIM))
        visible_rows = max(1, height - top - 1)
        selected_row = self.menu_selected * 2
        scroll = clamp_scroll(selected_row, visible_rows, len(content_rows))
        for offset, (line, attr) in enumerate(content_rows[scroll : scroll + visible_rows]):
            self.add(top + offset, left, line, attr)
        self.draw_footer(height, width, "[Scroll/Up/Down] Move   [Enter] Open   [Esc/Q] Back")

    def draw_help_page(self, height: int, width: int) -> None:
        top = self.draw_page_title(height, width, "Help", "Main actions are split into separate screens.")
        left = max(2, min(8, width // 10))
        lines = [
            "Main selector",
            "  Tab / Left / Right      switch Auth and Gateway columns",
            "  Up / Down               move cursor in current column",
            "  Space                   choose the current item as draft only",
            "  Enter                   review and apply the selected Auth + Gateway draft",
            "  D                       ask to delete the current item",
            "  O -> New Gateway Route  create a gateway forwarding profile",
            "  O -> New Auth Login     create an auth profile and run codex login",
            "  O                       open the menu",
            "  R / r                   restart Codex Desktop",
            "",
            "API form",
            "  Enter / Tab             move to the next field",
            "  Enter on last field     save the gateway route and stage it as draft",
            "  Esc                     cancel and return to main",
            "",
            "Advanced commands",
            "  Slash commands are still available from the main page for power users.",
            "  Examples: /status, /doctor, /mix <auth> <route>, /api new, /route official",
        ]
        visible_rows = max(1, height - top - 1)
        self.help_scroll = max(0, min(self.help_scroll, max(0, len(lines) - visible_rows)))
        for index, line in enumerate(lines[self.help_scroll : self.help_scroll + visible_rows]):
            attr = curses.A_BOLD if line and not line.startswith(" ") else curses.A_NORMAL
            self.add(top + index, left, line[: max(0, width - left - 2)], attr)
        hint = "[Scroll/Up/Down] Scroll   [Esc/Q] Back" if len(lines) > visible_rows else "[Esc/Q] Back"
        self.draw_footer(height, width, hint)

    def config_state(self, status: ProfileStatus) -> str:
        if not status.config_present:
            return "missing"
        return "empty" if status.config_empty else "ok"

    def auth_state(self, status: ProfileStatus) -> str:
        if status.auth_is_ignored:
            return "ignored" if status.auth_present else "-"
        if status.mode == "hybrid":
            return "preserved" if status.auth_present else "missing"
        if status.mode == "auth":
            return "used" if status.auth_present else "missing"
        return status.auth_mode or ("present" if status.auth_present else "-")

    def add(self, y: int, x: int, text: str, attr: int = curses.A_NORMAL) -> None:
        height, width = self.screen.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= width:
            return
        self.screen.addstr(y, x, text[: max(0, width - x - 1)], attr)

    def active_mix(self) -> tuple[str | None, str | None]:
        try:
            return self.store.infer_active_mix()
        except Exception:
            return None, None

    def draft_status_label(self, active_auth: str | None, active_route: str | None) -> str:
        if not self.chosen_auth or not self.chosen_route:
            return "incomplete draft"
        if (active_auth, active_route) == (self.chosen_auth, self.chosen_route):
            return "draft matches active"
        return "pending draft"

    def handle_mouse(self) -> None:
        try:
            _id, _x, _y, _z, button_state = curses.getmouse()
        except curses.error:
            return
        scroll_up = bool(
            button_state
            & (
                getattr(curses, "BUTTON4_PRESSED", 0)
                | getattr(curses, "BUTTON4_CLICKED", 0)
            )
        )
        # Some Python/macOS curses builds do not expose BUTTON5_* names, but
        # terminals may still report wheel-down using ncurses' extended bit.
        wheel_down_mask = (
            getattr(curses, "BUTTON5_PRESSED", 0)
            | getattr(curses, "BUTTON5_CLICKED", 0)
            | 0x800000
        )
        scroll_down = bool(button_state & wheel_down_mask)
        if not scroll_up and not scroll_down:
            return
        delta = -1 if scroll_up else 1
        self.scroll_current_view(delta)

    def scroll_current_view(self, delta: int) -> None:
        if self.mode == "help":
            self.help_scroll = max(0, self.help_scroll + delta)
            return
        if self.mode == "menu":
            self.menu_selected = (self.menu_selected + delta) % len(MENU_ITEMS)
            return
        if self.mode == "api_form":
            self.api_form.move(delta)
            return
        if self.mode == "auth_form":
            return
        self.move_selection(delta)

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
        self.request_apply_selection()

    def choose_current(self) -> None:
        profiles = [self.store.profile_status(name) for name in self.store.list_profiles()]
        if self.focus == "auth":
            candidates = auth_candidates(profiles)
            if candidates:
                self.auth_selected = clamp_index(self.auth_selected, candidates)
                self.chosen_auth = candidates[self.auth_selected].name
                self.log(f"Draft auth login: {self.chosen_auth}. Press Enter to review/apply.")
        else:
            candidates = route_candidates(profiles)
            if candidates:
                self.route_selected = clamp_index(self.route_selected, candidates)
                self.chosen_route = candidates[self.route_selected].name
                self.log(f"Draft gateway route: {self.chosen_route}. Press Enter to review/apply.")

    def current_profile_name(self) -> str | None:
        profiles = [self.store.profile_status(name) for name in self.store.list_profiles()]
        if self.focus == "auth":
            candidates = auth_candidates(profiles)
            if not candidates:
                return None
            self.auth_selected = clamp_index(self.auth_selected, candidates)
            return candidates[self.auth_selected].name
        candidates = route_candidates(profiles)
        if not candidates:
            return None
        self.route_selected = clamp_index(self.route_selected, candidates)
        return candidates[self.route_selected].name

    def request_delete_current(self) -> None:
        name = self.current_profile_name()
        if not name:
            self.log(f"No {self.focus} profile selected to delete.")
            return
        self.pending_delete = name
        self.log(f"Delete {name}? Press y to confirm, n or Esc to cancel.")

    def handle_delete_confirmation(self, key: int) -> None:
        name = self.pending_delete
        if not name:
            return
        if key in (ord("y"), ord("Y")):
            self.pending_delete = None
            self.delete_profile(name)
            if self.chosen_auth == name:
                self.chosen_auth = None
            if self.chosen_route == name:
                self.chosen_route = None
            return
        if key in (27, ord("n"), ord("N"), ord("q")):
            self.pending_delete = None
            self.log(f"Canceled delete {name}.")
            return
        self.log(f"Delete {name}? Press y to confirm, n or Esc to cancel.")

    def request_apply_selection(self) -> None:
        if not self.chosen_auth or not self.chosen_route:
            if self.chosen_auth:
                self.log("Draft auth selected. Choose a gateway route with Space before applying.")
            elif self.chosen_route:
                self.log("Draft gateway selected. Choose an auth login with Space before applying.")
            else:
                self.log("Choose one auth login and one gateway route with Space before applying.")
            return
        if not self.selection_needs_apply():
            self.log(f"Active config already uses auth={self.chosen_auth} gateway={self.chosen_route}.")
            return
        self.pending_apply = (self.chosen_auth, self.chosen_route)
        self.log(f"Apply auth={self.chosen_auth} gateway={self.chosen_route}? Press y to confirm, n or Esc to cancel.")

    def selection_needs_apply(self) -> bool:
        if not self.chosen_auth or not self.chosen_route:
            return False
        try:
            current_auth, current_route = self.store.infer_active_mix()
        except Exception:
            return True
        return (current_auth, current_route) != (self.chosen_auth, self.chosen_route)

    def handle_apply_confirmation(self, key: int) -> None:
        pending = self.pending_apply
        if not pending:
            return
        auth_name, route_name = pending
        if key in (ord("y"), ord("Y")):
            self.pending_apply = None
            self.mix_profiles(auth_name, route_name)
            return
        if key in (27, ord("n"), ord("N"), ord("q")):
            self.pending_apply = None
            self.log(f"Canceled apply auth={auth_name} gateway={route_name}.")
            return
        self.log(f"Apply auth={auth_name} gateway={route_name}? Press y to confirm, n or Esc to cancel.")

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
            self.mode = "help"
            return
        if name in {"/status", "status"}:
            self.log_status()
            return
        if name in {"/doctor", "doctor"}:
            self.log_doctor()
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
        if name in {"/api", "api"}:
            if args and args[0].lower() == "new":
                self.open_api_form()
            else:
                self.log("Usage: /api new")
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
        if code == 0 and self.store.profile_status(name).auth_present:
            self.chosen_auth = name
            self.log(f"Draft auth login: {name}. Press Enter to review/apply.")

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
            if code == 0 and self.store.profile_status(profile).auth_present:
                self.chosen_auth = profile
                self.log(f"Draft auth login: {profile}. Press Enter to review/apply.")
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
        if kind == "route":
            self.chosen_route = profile
            self.log(f"Draft gateway route: {profile}. Press Enter to review/apply.")

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

    def mix_profiles(self, auth_name: str, route_name: str) -> None:
        try:
            backup = self.store.mix_profiles(auth_name, route_name)
        except Exception as exc:
            self.log(f"Mix failed: {exc}")
            return
        self.chosen_auth = auth_name
        self.chosen_route = route_name
        self.log(f"Applied auth={auth_name} gateway={route_name}.")
        self.log(mix_effect_message(self.store.active_status()))
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

    def open_api_form(self) -> None:
        self.mode = "api_form"
        self.command = ""
        self.api_form = ApiRouteForm()

    def open_auth_form(self) -> None:
        self.mode = "auth_form"
        self.command = ""
        self.auth_form = AuthProfileForm()

    def handle_menu_key(self, key: int) -> None:
        if key in (27, ord("q")):
            self.mode = "main"
            return
        if key in (curses.KEY_UP,):
            self.menu_selected = (self.menu_selected - 1) % len(MENU_ITEMS)
            return
        if key in (curses.KEY_DOWN, 9):
            self.menu_selected = (self.menu_selected + 1) % len(MENU_ITEMS)
            return
        if key in (10, 13, curses.KEY_ENTER):
            self.run_menu_action(MENU_ITEMS[self.menu_selected][2])

    def handle_help_key(self, key: int) -> None:
        if key in (27, ord("q"), ord("?")):
            self.mode = "main"
            return
        if key in (curses.KEY_UP,):
            self.help_scroll = max(0, self.help_scroll - 1)
            return
        if key in (curses.KEY_DOWN,):
            self.help_scroll += 1
            return
        if key in (curses.KEY_PPAGE,):
            self.help_scroll = max(0, self.help_scroll - 5)
            return
        if key in (curses.KEY_NPAGE,):
            self.help_scroll += 5

    def run_menu_action(self, action: str) -> None:
        if action == "new_api":
            self.open_api_form()
            return
        if action == "new_auth":
            self.open_auth_form()
            return
        if action == "status":
            self.mode = "main"
            self.log_status()
            return
        if action == "doctor":
            self.mode = "main"
            self.log_doctor()
            return
        if action == "restart":
            self.mode = "main"
            self.restart_codex()
            return
        if action == "help":
            self.mode = "help"
            return
        if action == "back":
            self.mode = "main"

    def handle_api_form_key(self, key: int) -> None:
        if key in (27,):
            self.mode = "main"
            self.log("Canceled new gateway route.")
            return
        if key in (curses.KEY_UP,):
            self.api_form.move(-1)
            return
        if key in (curses.KEY_DOWN, 9):
            self.api_form.move(1)
            return
        if key in (10, 13, curses.KEY_ENTER):
            if self.api_form.focus == len(API_FORM_FIELDS) - 1:
                self.save_api_form()
            else:
                self.api_form.move(1)
            return
        if key in (curses.KEY_BACKSPACE, 127, 8):
            self.api_form.backspace()
            return
        if 32 <= key <= 126:
            self.api_form.type_char(chr(key))

    def handle_auth_form_key(self, key: int) -> None:
        if key in (27,):
            self.mode = "main"
            self.log("Canceled new auth login.")
            return
        if key in (10, 13, curses.KEY_ENTER):
            self.save_auth_form()
            return
        if key in (curses.KEY_BACKSPACE, 127, 8):
            self.auth_form.backspace()
            return
        if 32 <= key <= 126:
            self.auth_form.type_char(chr(key))

    def save_api_form(self) -> None:
        values = self.api_form.cleaned_values()
        missing = [field["label"] for field in API_FORM_FIELDS if field["required"] and not values[field["key"]]]
        if missing:
            self.api_form.error = "Required: " + ", ".join(missing)
            return
        provider = values["provider"] or DEFAULT_ACTIVE_PROVIDER
        wire_api = values["wire_api"] or "responses"
        try:
            path = self.store.create_route_profile(
                values["name"],
                base_url=values["base_url"],
                model=values["model"],
                env_key=values["env_key"] or DEFAULT_ENV_KEY,
                provider=provider,
                wire_api=wire_api,
            )
        except Exception as exc:
            self.api_form.error = f"Create failed: {exc}"
            return
        self.chosen_route = values["name"]
        self.mode = "main"
        self.log(f"Created gateway route profile {values['name']}.")
        self.log(f"Path: {path}")
        self.log(f"Draft gateway route: {values['name']}. Press Enter to review/apply.")

    def save_auth_form(self) -> None:
        values = self.auth_form.cleaned_values()
        name = values["name"]
        if not name:
            self.auth_form.error = "Required: Name"
            return
        self.screen.clear()
        self.screen.refresh()
        try:
            code = self.store.create_auth_profile(name)
        except Exception as exc:
            self.auth_form.error = f"Create failed: {exc}"
            return
        self.chosen_auth = name
        self.mode = "main"
        self.log(f"Initialized auth profile {name}; codex login exited with {code}.")
        if code == 0 and self.store.profile_status(name).auth_present:
            self.log(f"Draft auth login: {name}. Press Enter to review/apply.")
        else:
            self.log("Auth login was not completed, so no gateway route was applied.")

    def route(self, args: list[str]) -> None:
        if not args:
            self.log("Usage: /route custom --base-url URL --model MODEL [--env-key OPENAI_API_KEY]")
            self.log("   or: /route custom --base-url URL --model MODEL --api-key KEY")
            self.log(f"   or: /route official [--model MODEL] [--provider {DEFAULT_ACTIVE_PROVIDER}]")
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
        env_key = options.get("--env-key", DEFAULT_ENV_KEY)
        if not base_url or not model:
            self.log("Usage: /route custom --base-url URL --model MODEL [--env-key OPENAI_API_KEY]")
            return
        provider = options.get("--provider", DEFAULT_ACTIVE_PROVIDER)
        wire_api = options.get("--wire-api", "responses")
        try:
            backup = self.store.route_custom(
                base_url=base_url,
                model=model,
                api_key=api_key,
                env_key=None if api_key else env_key,
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
        provider = options.get("--provider", DEFAULT_ACTIVE_PROVIDER)
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
                f"{status.name}: {status.mode}, kind={status.profile_kind or '-'}, model={status.model or '-'}, "
                f"config={self.config_state(status)}, auth={self.auth_state(status)}"
            )

    def log_doctor(self) -> None:
        try:
            diagnostics = self.store.diagnose()
        except Exception as exc:
            self.log(f"Doctor failed: {exc}")
            return
        if not diagnostics:
            self.log("Doctor: ok")
            return
        self.log(f"Doctor: {len(diagnostics)} finding(s)")
        for item in diagnostics:
            self.log(f"{item.level}: {item.subject}: {item.message}")

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


class ApiRouteForm:
    def __init__(self) -> None:
        self.values = {field["key"]: "" for field in API_FORM_FIELDS}
        self.focus = 0
        self.error = ""

    def move(self, delta: int) -> None:
        self.focus = (self.focus + delta) % len(API_FORM_FIELDS)
        self.error = ""

    def backspace(self) -> None:
        key = API_FORM_FIELDS[self.focus]["key"]
        self.values[key] = self.values[key][:-1]
        self.error = ""

    def type_char(self, char: str) -> None:
        key = API_FORM_FIELDS[self.focus]["key"]
        self.values[key] += char
        self.error = ""

    def cleaned_values(self) -> dict[str, str]:
        return {key: value.strip() for key, value in self.values.items()}


class AuthProfileForm:
    def __init__(self) -> None:
        self.values = {field["key"]: "" for field in AUTH_FORM_FIELDS}
        self.error = ""

    def backspace(self) -> None:
        self.values["name"] = self.values["name"][:-1]
        self.error = ""

    def type_char(self, char: str) -> None:
        self.values["name"] += char
        self.error = ""

    def cleaned_values(self) -> dict[str, str]:
        return {key: value.strip() for key, value in self.values.items()}


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:3] + "*" * max(4, len(value) - 6) + value[-3:]


def auth_candidates(profiles: list[ProfileStatus]) -> list[ProfileStatus]:
    return [status for status in profiles if status.auth_present and not status.base_url]


def route_candidates(profiles: list[ProfileStatus]) -> list[ProfileStatus]:
    return [
        status
        for status in profiles
        if status.config_present and not status.config_empty and (status.provider or status.mode == "auth")
    ]


def clamp_index(index: int, items: list[object]) -> int:
    if not items:
        return 0
    return max(0, min(index, len(items) - 1))


def clamp_scroll(index: int, visible_rows: int, total_rows: int) -> int:
    if total_rows <= visible_rows:
        return 0
    if index < 0:
        return 0
    max_scroll = max(0, total_rows - visible_rows)
    if index >= visible_rows:
        return min(max_scroll, index - visible_rows + 1)
    return 0


def layout_tier(height: int, width: int) -> str:
    if height < 30 or width < 100:
        return TIER_COMPACT
    if height < 38 or width < 130:
        return TIER_NORMAL
    return TIER_SPACIOUS


def main_footer_hint(width: int, tier: str) -> str:
    if tier == TIER_COMPACT or width < 92:
        return "[Tab] focus  [Space] draft  [Enter] apply  [Q] quit"
    if tier == TIER_NORMAL or width < 128:
        return "[Tab] focus   [↑/↓] move   [Space] draft   [Enter] apply   [?] help   [Q] quit"
    return "[Tab] focus   [↑/↓] move   [Space] select draft   [Enter] confirm apply   [D] delete   [?] help   [Q] quit"


def scroll_start(index: int, visible_items: int, total_items: int) -> int:
    if total_items <= visible_items:
        return 0
    if index < 0:
        return 0
    max_start = max(0, total_items - visible_items)
    return min(max_start, max(0, index - visible_items + 1))


def focus_title(text: str, focused: bool) -> str:
    return f" {text.upper()} " if focused else text


def rule(width: int, *, max_width: int = 82) -> str:
    return "─" * max(0, min(width, max_width))


def render_history(history: list[str], width: int) -> list[tuple[str, str]]:
    rendered: list[tuple[str, str]] = []
    for line in history[-30:]:
        level, message = history_level(line)
        chunks = textwrap.wrap(message, max(12, width - 8)) or [""]
        rendered.append((level, chunks[0]))
        rendered.extend(("", chunk) for chunk in chunks[1:])
    return rendered


def history_level(message: str) -> tuple[str, str]:
    lower = message.lower()
    if lower.startswith(">"):
        return "CMD", message
    if "failed" in lower or lower.startswith("error") or lower.startswith("mix failed"):
        return "ERR", message
    if lower.startswith("doctor:") or lower.startswith("warning") or "canceled" in lower:
        return "WARN", message
    if lower.startswith("applied") or lower.startswith("deleted") or lower.startswith("restored"):
        return "OK", message
    if lower.startswith("draft") or "press enter" in lower:
        return "NEXT", message
    return "INFO", message


def level_attr(level: str) -> int:
    return {
        "ERR": STYLE_ERROR,
        "WARN": curses.A_BOLD,
        "OK": curses.A_BOLD,
        "NEXT": curses.A_BOLD,
        "CMD": curses.A_DIM,
        "INFO": curses.A_DIM,
    }.get(level, curses.A_DIM)


def item_badge(status: ProfileStatus, kind: str, active: bool) -> str:
    if active:
        return "active"
    if kind == "auth":
        return status.auth_mode or "auth"
    if status.base_url:
        return "gateway"
    if status.mode == "auth":
        return "official"
    return status.mode or "route"


def item_detail(status: ProfileStatus, kind: str) -> str:
    if kind == "auth":
        if status.auth_present:
            return "ChatGPT auth.json"
        return "missing auth.json"
    if status.base_url:
        parsed = urlparse(status.base_url)
        endpoint = parsed.netloc or status.base_url
    else:
        endpoint = status.provider or "OpenAI"
    return f"{endpoint}  {status.model or '-'}"


def route_effect_label(status: ProfileStatus | None, *, has_auth: bool) -> str:
    if status is None:
        return "choose a gateway route"
    if status.auth_is_ignored:
        return "API credentials; copied auth ignored"
    if has_auth and status.base_url:
        return "uses selected auth + gateway"
    if status.mode == "hybrid":
        return "uses selected auth + gateway"
    if status.mode == "auth":
        return "uses selected auth.json"
    if status.base_url:
        return "custom route behavior unknown"
    return "check cps status"


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


def mix_effect_message(status: ProfileStatus) -> str:
    if status.auth_is_ignored:
        return "Route uses API credentials; copied auth.json is present but ignored by model requests."
    if status.mode == "hybrid":
        return "Route uses the selected auth.json with a custom endpoint."
    if status.mode == "auth":
        return "Route uses the selected auth.json."
    return "Route auth behavior is unknown; check cps status."


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
