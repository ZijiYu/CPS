from __future__ import annotations

import argparse
from pathlib import Path

from .core import DEFAULT_ACTIVE_PROVIDER, DEFAULT_ENV_KEY, ProfileStore
from .tui import run_tui


def main() -> None:
    parser = argparse.ArgumentParser(prog="cps")
    parser.add_argument("--root", type=Path, help="profile root, defaults to ~/.codex-profiles")
    parser.add_argument("--codex-dir", type=Path, help="active Codex dir, defaults to ~/.codex")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("tui")
    sub.add_parser("status", help="show active config and saved profile structure")
    sub.add_parser("list", help="list saved profiles")
    sub.add_parser("deleted", help="list reversibly deleted profiles")
    sub.add_parser("doc", help="show full CPS documentation")
    sub.add_parser("restart", help="restart Codex Desktop")
    init = sub.add_parser("init", help="initialize auth, route, or full profile from active ~/.codex")
    init.add_argument("kind_or_profile", metavar="auth|route|full|profile")
    init.add_argument("profile", nargs="?", help="profile name when kind is auth, route, or full")
    for command in ("save", "use", "login", "path", "delete"):
        p = sub.add_parser(command)
        p.add_argument("profile")
    mix = sub.add_parser("mix", help="apply auth from one profile and route config from another")
    mix.add_argument("auth_profile")
    mix.add_argument("route_profile")
    restore = sub.add_parser("restore")
    restore.add_argument("deleted_profile")
    restore.add_argument("profile", nargs="?")
    route = sub.add_parser("route", help="edit active provider routing without replacing auth.json")
    route_sub = route.add_subparsers(dest="route_command", required=True)
    custom = route_sub.add_parser("custom", help="route model calls through a custom provider")
    custom.add_argument("--base-url", required=True)
    custom.add_argument("--model", required=True)
    custom.add_argument("--api-key")
    custom.add_argument("--env-key", default=DEFAULT_ENV_KEY)
    custom.add_argument("--provider", default=DEFAULT_ACTIVE_PROVIDER)
    custom.add_argument("--wire-api", default="responses")
    official = route_sub.add_parser("official", help="route model calls back to the official provider")
    official.add_argument("--model")
    official.add_argument("--provider", default=DEFAULT_ACTIVE_PROVIDER)

    args = parser.parse_args()
    store = ProfileStore(root=args.root, codex_dir=args.codex_dir)
    command = args.command or "tui"

    if command == "tui":
        run_tui(store)
    elif command == "status":
        print_status(store.active_status())
        for name in store.list_profiles():
            print()
            print_status(store.profile_status(name))
    elif command == "list":
        for name in store.list_profiles():
            print(name)
    elif command == "deleted":
        for name in store.list_deleted():
            print(name)
    elif command == "doc":
        print_doc()
    elif command == "restart":
        code = store.restart_codex()
        print(f"restart Codex exited with {code}")
    elif command == "init":
        kind, profile = parse_init_args(args.kind_or_profile, args.profile)
        if kind == "auth":
            raise SystemExit(store.create_auth_profile(profile))
        elif kind == "route":
            print(store.init_route_profile(profile))
        else:
            print(store.init_profile(profile))
    elif command == "save":
        print(store.save_profile(args.profile))
    elif command == "use":
        backup = store.use_profile(args.profile)
        print(f"switched to {args.profile}")
        print(f"backup: {backup}")
        print("restart Codex Desktop if it is already open")
    elif command == "mix":
        backup = store.mix_profiles(args.auth_profile, args.route_profile)
        active = store.active_status()
        print(f"mixed auth={args.auth_profile} route={args.route_profile}")
        print("auth.json: from auth profile")
        print("config.toml: from route profile")
        print(f"route_effect: {mix_effect_message(active)}")
        print(f"backup: {backup}")
        print("restart Codex Desktop if it is already open")
    elif command == "login":
        raise SystemExit(store.login_profile(args.profile))
    elif command == "path":
        print(store.profile_dir(args.profile))
    elif command == "delete":
        deleted_path = store.delete_profile(args.profile)
        print(f"deleted {args.profile}")
        print(f"moved to: {deleted_path}")
    elif command == "restore":
        restored_path = store.restore_profile(args.deleted_profile, args.profile)
        print(f"restored to: {restored_path}")
    elif command == "route":
        if args.route_command == "custom":
            backup = store.route_custom(
                base_url=args.base_url,
                model=args.model,
                api_key=args.api_key,
                env_key=None if args.api_key else args.env_key,
                provider=args.provider,
                wire_api=args.wire_api,
            )
            print(f"routed to custom provider: {store.active_status().provider or args.provider}")
            print(f"model: {args.model}")
            print(f"base_url: {args.base_url}")
            print("auth.json: preserved")
            print(f"backup: {backup}")
            print("restart Codex Desktop if it is already open")
        elif args.route_command == "official":
            backup = store.route_official(model=args.model, provider=args.provider)
            print(f"routed to official provider: {store.active_status().provider or args.provider}")
            if args.model:
                print(f"model: {args.model}")
            print("auth.json: preserved")
            print(f"backup: {backup}")
            print("restart Codex Desktop if it is already open")


def print_status(status) -> None:
    print(f"{status.name}: {status.mode}")
    print(f"  path: {status.path}")
    print(f"  model: {status.model or '-'}")
    print(f"  provider: {status.provider or '-'}")
    print(f"  base_url: {status.base_url or '-'}")
    if status.config_present:
        config_state = "empty" if status.config_empty else "ok"
    else:
        config_state = "missing"
    print(f"  config.toml: {config_state}")
    print(f"  api.config.toml: {'yes' if status.api_config_present else 'no'}")
    print(f"  auth.json: {'yes' if status.auth_present else 'no'}")
    print(f"  auth_mode: {status.auth_mode or '-'}")
    if status.auth_is_ignored:
        print("  auth_effect: ignored by API route")
    elif status.route_uses_auth:
        print("  auth_effect: used by selected route")
    elif status.auth_present:
        print("  auth_effect: present, route usage unknown")


def mix_effect_message(status) -> str:
    if status.auth_is_ignored:
        return "API credentials are used; copied auth.json is present but ignored by model requests"
    if status.mode == "hybrid":
        return "selected auth.json is used with a custom endpoint"
    if status.mode == "auth":
        return "selected auth.json is used"
    return "unknown; run cps status"


def print_doc() -> None:
    print(
        """CPS - Codex Profile Switcher

Purpose:
  CPS separates Codex auth from model routing, then lets you compose them.

Core idea:
  Auth profile        -> auth.json / ChatGPT login
  API / Route profile -> config.toml / provider / model / base_url / API key
  Apply Selection     -> writes the selected Auth + API / Route into ~/.codex

Route effect:
  cps status reports auth_effect so API-key routes are not mistaken for
  ChatGPT-account routes. If auth_effect is ignored, auth.json is present but
  model requests use API credentials.

TUI:
  cps

Main keys:
  Up/Down             move in current column
  Tab or Left/Right   switch Auth / API column
  Enter               select current item
  M                   apply selected Auth + API / Route
  O                   open menu
  R                   restart Codex
  ?                   help
  Q                   quit

Menu:
  New Auth Login      create an auth profile and run codex login
  New API Route       create a route-only API profile from a form

Common CLI:
  cps init auth personal
  cps init route work
  cps mix personal work
  cps restart

Custom API route:
  cps route custom --base-url URL --model MODEL [--env-key OPENAI_API_KEY]
  cps route custom --base-url URL --model MODEL --api-key KEY
  # default provider: gateway

Official route:
  cps route official --model MODEL
  # default provider: gateway

State:
  ~/.codex                 active Codex config
  ~/.codex-profiles        saved CPS profiles
  ~/.codex-profiles/deleted reversible deletes
  ~/.codex-profiles/backups switch-time backups

Safety:
  delete is reversible:
    cps delete <profile>
    cps deleted
    cps restore <deleted-profile>

Release notes:
  1.0.4
    - Full-screen menu for creation flows
    - New API Route and New Auth Login forms
    - Apply Selection wording
    - auth_effect status for API routes that ignore copied auth.json
    - Scroll-aware pages for smaller terminals
    - Safer profile and provider name handling

  1.0.3
    - Auth and API / Route columns in the TUI
    - File composition with cps mix <auth> <route>
    - Split init auth / init route / init full commands
    - Route helpers for official and custom API endpoints
    - Codex restart support

More:
  cps --help
  cps status
"""
    )


def parse_init_args(kind_or_profile: str, profile: str | None) -> tuple[str, str]:
    if profile is None:
        return "full", kind_or_profile
    if kind_or_profile not in {"auth", "route", "full"}:
        raise SystemExit("usage: cps init [auth|route|full] <profile>")
    return kind_or_profile, profile


if __name__ == "__main__":
    main()
