#!/usr/bin/env python3
"""Standalone CPS TUI concept demo.

This is a visual and interaction prototype only. It does not import the real
profile switcher and never reads or writes ~/.codex.
"""

from __future__ import annotations

import argparse
import curses
import textwrap
from dataclasses import dataclass
from typing import Sequence


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
]

COMPACT_LOGO = [
    "CPS - Codex Profile Switcher",
    "Concept: safer draft/apply flow",
]

MIN_HEIGHT = 22
MIN_WIDTH = 84


@dataclass(frozen=True)
class AuthProfile:
    name: str
    mode: str
    note: str


@dataclass(frozen=True)
class RouteProfile:
    name: str
    kind: str
    model: str
    endpoint: str
    effect: str


AUTH_PROFILES = [
    AuthProfile("personal", "chatgpt", "Primary ChatGPT login"),
    AuthProfile("team", "chatgpt", "Shared workspace login"),
    AuthProfile("lab", "file", "Experimental auth store"),
]

ROUTE_PROFILES = [
    RouteProfile("official", "official", "gpt-5.5", "OpenAI", "uses selected auth.json"),
    RouteProfile("work-gateway", "gateway", "gpt-5.5", "gateway.acme.test", "uses selected auth + gateway"),
    RouteProfile("backup-api", "api-key", "gpt-5-mini", "fallback.example.test", "API key route; auth ignored"),
]


class Style:
    NORMAL = curses.A_NORMAL
    MUTED = curses.A_DIM
    IMPORTANT = curses.A_BOLD
    BAR = curses.A_BOLD
    FOCUS = curses.A_BOLD | curses.A_UNDERLINE
    SELECTED = curses.A_BOLD
    ERROR = curses.A_BOLD | curses.A_UNDERLINE


TRUE_BLACK_BACKGROUND = "\033]10;#ffffff\007\033]11;#000000\007\033[38;2;255;255;255m\033[48;2;0;0;0m"


def init_terminal_style(screen) -> None:
    try:
        print(TRUE_BLACK_BACKGROUND, end="", flush=True)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_CYAN, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            Style.NORMAL = curses.color_pair(1)
            Style.BAR = curses.color_pair(1) | curses.A_BOLD
            Style.FOCUS = curses.color_pair(2) | curses.A_BOLD | curses.A_UNDERLINE
            Style.ERROR = curses.color_pair(3) | curses.A_BOLD | curses.A_UNDERLINE
            screen.bkgd(" ", Style.NORMAL)
    except curses.error:
        pass


class ConceptApp:
    def __init__(self, screen) -> None:
        self.screen = screen
        self.focus = "auth"
        self.auth_cursor = 0
        self.route_cursor = 1
        self.active_auth = "personal"
        self.active_route = "official"
        self.draft_auth = self.active_auth
        self.draft_route = "work-gateway"
        self.confirming = False
        self.logs = [
            ("INFO", "Demo only: no files are read or written."),
            ("NEXT", "Space changes the draft. Enter reviews before apply."),
        ]

    def run(self) -> None:
        curses.curs_set(0)
        self.screen.keypad(True)
        init_terminal_style(self.screen)
        while True:
            self.draw()
            key = self.screen.getch()
            if key in (ord("q"), ord("Q")) and not self.confirming:
                return
            if self.confirming:
                self.handle_confirm_key(key)
            else:
                self.handle_key(key)

    def handle_key(self, key: int) -> None:
        if key in (curses.KEY_LEFT, curses.KEY_RIGHT, 9):
            self.focus = "route" if self.focus == "auth" else "auth"
        elif key == curses.KEY_UP:
            self.move(-1)
        elif key == curses.KEY_DOWN:
            self.move(1)
        elif key == ord(" "):
            self.select_current()
        elif key in (10, 13, curses.KEY_ENTER):
            if self.has_pending_change():
                self.confirming = True
            else:
                self.log("OK", "Active config already matches the draft pair.")
        elif key in (ord("d"), ord("D")):
            self.log("WARN", "Delete would open a separate, reversible confirm flow.")
        elif key == ord("?"):
            self.log("INFO", "This concept keeps the old look, but separates draft from apply.")

    def handle_confirm_key(self, key: int) -> None:
        if key in (27, ord("n"), ord("N"), ord("q"), ord("Q")):
            self.confirming = False
            self.log("INFO", "Apply canceled. Draft remains visible.")
            return
        if key in (ord("y"), ord("Y")):
            self.confirming = False
            self.active_auth = self.draft_auth
            self.active_route = self.draft_route
            self.log("OK", f"Demo applied auth={self.active_auth} gateway={self.active_route}.")
            self.log("NEXT", "Real CPS would now suggest restarting Codex.")

    def move(self, delta: int) -> None:
        if self.focus == "auth":
            self.auth_cursor = (self.auth_cursor + delta) % len(AUTH_PROFILES)
        else:
            self.route_cursor = (self.route_cursor + delta) % len(ROUTE_PROFILES)

    def select_current(self) -> None:
        if self.focus == "auth":
            self.draft_auth = AUTH_PROFILES[self.auth_cursor].name
            self.log("INFO", f"Draft auth set to {self.draft_auth}. Nothing applied yet.")
        else:
            self.draft_route = ROUTE_PROFILES[self.route_cursor].name
            self.log("INFO", f"Draft gateway set to {self.draft_route}. Nothing applied yet.")

    def has_pending_change(self) -> bool:
        return self.active_auth != self.draft_auth or self.active_route != self.draft_route

    def draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        if height < MIN_HEIGHT or width < MIN_WIDTH:
            self.draw_too_small(height, width)
            return

        logo_height = self.draw_logo(width, height)
        top = logo_height + 1
        self.draw_status_bar(top, width)

        content_top = top + 3
        left_col = 2
        selector_width = min(max(60, width - 44), 86)
        activity_col = left_col + selector_width + 4
        activity_width = max(26, width - activity_col - 2)

        self.draw_selector(content_top, left_col, selector_width, height)
        if activity_col < width - 20:
            self.draw_activity(content_top, activity_col, activity_width, height)
        self.draw_footer(height, width)
        if self.confirming:
            self.draw_confirm(height, width)
        self.screen.refresh()

    def draw_too_small(self, height: int, width: int) -> None:
        self.add(0, 0, f"CPS concept needs at least {MIN_WIDTH}x{MIN_HEIGHT}.", Style.ERROR)
        self.add(2, 0, "Resize the terminal or run with --static.", Style.MUTED)
        self.screen.refresh()

    def draw_logo(self, width: int, height: int) -> int:
        lines = COMPACT_LOGO[:1] if height < 30 else LOGO if width >= 72 else COMPACT_LOGO
        for y, line in enumerate(lines):
            if y >= height - 10:
                break
            x = max(0, (width - len(line)) // 2)
            attr = Style.IMPORTANT if y in (0, len(lines) - 1) else Style.NORMAL
            self.add(y, x, line, attr)
        return min(len(lines), max(0, height - 10))

    def draw_status_bar(self, row: int, width: int) -> None:
        status = "pending draft" if self.has_pending_change() else "draft matches active"
        self.add(row, 0, " " * (width - 1), Style.BAR | curses.A_BOLD)
        self.add(row, 1, " Codex Profile Switcher  concept=v2-draft-apply ", Style.BAR | curses.A_BOLD)
        self.add(row, max(1, width - len(status) - 3), status, Style.BAR | curses.A_BOLD)
        self.add(row + 1, 2, f"Active: auth={self.active_auth}  gateway={self.active_route}"[: max(0, width - 4)], Style.MUTED)

    def draw_selector(self, row: int, col: int, width: int, height: int) -> None:
        auth_width = max(24, min(34, width // 2 - 2))
        gap = 3
        route_width = max(28, width - auth_width - gap)
        route_col = col + auth_width + gap

        self.add(row, col, focus_title("Auth", self.focus == "auth"), title_attr(self.focus == "auth"))
        self.add(row, route_col, focus_title("Gateway", self.focus == "route"), title_attr(self.focus == "route"))

        for index, item in enumerate(AUTH_PROFILES):
            self.draw_item(
                row + 2 + index * 2,
                col,
                auth_width,
                name=item.name,
                state="active" if item.name == self.active_auth else item.mode,
                detail=item.note,
                cursor=self.focus == "auth" and index == self.auth_cursor,
                selected=item.name == self.draft_auth,
            )

        for index, item in enumerate(ROUTE_PROFILES):
            self.draw_item(
                row + 2 + index * 2,
                route_col,
                route_width,
                name=item.name,
                state="active" if item.name == self.active_route else item.kind,
                detail=f"{item.endpoint}  {item.model}",
                cursor=self.focus == "route" and index == self.route_cursor,
                selected=item.name == self.draft_route,
            )

        preview_row = row + 9
        if preview_row < height - 8:
            self.draw_apply_preview(preview_row, col, width)

    def draw_item(
        self,
        row: int,
        col: int,
        width: int,
        *,
        name: str,
        state: str,
        detail: str,
        cursor: bool,
        selected: bool,
    ) -> None:
        pointer = ">" if cursor else " "
        marker = "*" if selected else " "
        attr = Style.FOCUS if cursor else Style.SELECTED if selected else Style.NORMAL
        self.add(row, col, f"{pointer}{marker} {name:<14} {state}"[:width].ljust(width), attr)
        self.add(row + 1, col + 4, detail[: max(0, width - 4)], Style.MUTED)

    def draw_apply_preview(self, row: int, col: int, width: int) -> None:
        route = next(item for item in ROUTE_PROFILES if item.name == self.draft_route)
        self.add(row, col, "Apply preview", Style.IMPORTANT)
        self.add(row + 1, col, rule(width), Style.MUTED)
        lines = [
            f"auth.json      <- {self.draft_auth}",
            f"config.toml    <- {self.draft_route} ({route.kind}, {route.model})",
            f"request path   -> {route.effect}",
        ]
        for offset, line in enumerate(lines, start=2):
            self.add(row + offset, col + 2, line[: max(0, width - 4)])
        if self.has_pending_change():
            self.add(row + 6, col + 2, "Enter: review and confirm before writing", Style.IMPORTANT)
            self.add(row + 7, col + 2, "Space: change draft only", Style.MUTED)
        else:
            self.add(row + 6, col + 2, "No changes pending", Style.IMPORTANT)

    def draw_activity(self, row: int, col: int, width: int, height: int) -> None:
        self.add(row, col, "Activity", Style.IMPORTANT)
        self.add(row + 1, col, rule(width, max_width=36), Style.MUTED)
        max_rows = max(1, height - row - 4)
        for offset, (level, message) in enumerate(render_logs(self.logs, width)[-max_rows:]):
            y = row + 2 + offset
            if level:
                self.add(y, col, f"{level:<5}", level_attr(level))
                self.add(y, col + 6, message[: max(0, width - 6)])
            else:
                self.add(y, col + 6, message[: max(0, width - 6)])

    def draw_footer(self, height: int, width: int) -> None:
        hint = "[Tab] focus   [↑/↓] move   [Space] select draft   [Enter] confirm apply   [D] delete   [?] help   [Q] quit"
        self.add(height - 1, 0, " " * (width - 1), Style.BAR)
        self.add(height - 1, 2, hint[: max(0, width - 4)], Style.BAR)

    def draw_confirm(self, height: int, width: int) -> None:
        panel_width = min(76, width - 8)
        panel_height = 9
        top = max(2, (height - panel_height) // 2)
        left = max(2, (width - panel_width) // 2)
        self.panel(top, left, panel_width, panel_height, "Review apply")
        self.add(top + 2, left + 3, "This is the only step that would write active config.", Style.IMPORTANT)
        self.add(top + 4, left + 5, f"auth.json   <- {self.draft_auth}")
        self.add(top + 5, left + 5, f"config.toml <- {self.draft_route}")
        self.add(top + 7, left + 3, "Y confirm   N/Esc cancel", Style.BAR | curses.A_BOLD)

    def panel(self, row: int, col: int, width: int, height: int, title: str) -> None:
        top = "╭" + "─" * (width - 2) + "╮"
        mid = "│" + " " * (width - 2) + "│"
        bottom = "╰" + "─" * (width - 2) + "╯"
        self.add(row, col, top, Style.FOCUS)
        for y in range(row + 1, row + height - 1):
            self.add(y, col, mid, Style.FOCUS)
        self.add(row + height - 1, col, bottom, Style.FOCUS)
        self.add(row, col + 2, f" {title} ", Style.FOCUS)

    def log(self, level: str, message: str) -> None:
        self.logs.append((level, message))
        self.logs = self.logs[-80:]

    def add(self, y: int, x: int, text: str, attr: int = Style.NORMAL) -> None:
        height, width = self.screen.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= width:
            return
        self.screen.addstr(y, x, text[: max(0, width - x - 1)], attr)


def render_logs(logs: Sequence[tuple[str, str]], width: int) -> list[tuple[str, str]]:
    rendered: list[tuple[str, str]] = []
    for level, message in logs[-20:]:
        chunks = textwrap.wrap(message, max(12, width - 8)) or [""]
        rendered.append((level, chunks[0]))
        rendered.extend(("", chunk) for chunk in chunks[1:])
    return rendered


def rule(width: int, *, max_width: int = 82) -> str:
    return "─" * min(width, max_width)


def title_attr(focused: bool) -> int:
    return Style.FOCUS if focused else Style.IMPORTANT


def level_attr(level: str) -> int:
    return {
        "ERR": Style.ERROR,
        "WARN": Style.IMPORTANT,
        "OK": Style.IMPORTANT,
        "NEXT": Style.SELECTED,
        "INFO": Style.MUTED,
    }.get(level, Style.MUTED)


def focus_title(text: str, focused: bool) -> str:
    return f" {text.upper()} " if focused else text


def static_preview(width: int = 108) -> str:
    width = max(88, width)
    logo = [
        "╔════════════════════════════════════════════════════════════════╗",
        "║   ██████╗ ██████╗ ███████╗                                    ║",
        "║   Codex Profile Switcher                                      ║",
        "╚════════════════════════════════════════════════════════════════╝",
    ]
    bar = " Codex Profile Switcher  concept=v2-draft-apply ".ljust(width - 16) + "pending draft"
    return "\n".join(
        [
            *[line.center(width) for line in logo],
            bar,
            "  Active: auth=personal  gateway=official",
            "",
            "  AUTH                               GATEWAY",
            "  >* personal      active            >  official       active    gpt-5.5",
            "      Primary ChatGPT login             OpenAI",
            "    team          chatgpt             * work-gateway  gateway   gpt-5.5",
            "      Shared workspace login            gateway.acme.test",
            "    lab           file                  backup-api    api-key   gpt-5-mini",
            "",
            "  Apply preview",
            "  " + "─" * min(width - 4, 82),
            "    auth.json      <- personal",
            "    config.toml    <- work-gateway (gateway, gpt-5.5)",
            "    request path   -> uses selected auth + gateway",
            "    Enter: review and confirm before writing",
            "",
            "  Activity",
            "  " + "─" * 36,
            "  INFO  Demo only: no files are read or written.",
            "  NEXT  Space changes the draft. Enter reviews before apply.",
            "",
            "  [Tab] focus   [↑/↓] move   [Space] select draft   [Enter] confirm apply   [D] delete   [?] help   [Q] quit",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone CPS TUI concept demo.")
    parser.add_argument("--static", action="store_true", help="print a static preview instead of opening curses")
    args = parser.parse_args()
    if args.static:
        print(static_preview())
        return
    curses.wrapper(lambda screen: ConceptApp(screen).run())


if __name__ == "__main__":
    main()
