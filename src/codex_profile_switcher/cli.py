from __future__ import annotations

import argparse
from pathlib import Path

from .core import ProfileStore
from .tui import run_tui


def main() -> None:
    parser = argparse.ArgumentParser(prog="cps")
    parser.add_argument("--root", type=Path, help="profile root, defaults to ~/.codex-profiles")
    parser.add_argument("--codex-dir", type=Path, help="active Codex dir, defaults to ~/.codex")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("tui")
    sub.add_parser("status")
    sub.add_parser("list")
    sub.add_parser("deleted")
    for command in ("init", "save", "use", "login", "path", "delete"):
        p = sub.add_parser(command)
        p.add_argument("profile")
    restore = sub.add_parser("restore")
    restore.add_argument("deleted_profile")
    restore.add_argument("profile", nargs="?")

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
    elif command == "init":
        print(store.init_profile(args.profile))
    elif command == "save":
        print(store.save_profile(args.profile))
    elif command == "use":
        backup = store.use_profile(args.profile)
        print(f"switched to {args.profile}")
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


if __name__ == "__main__":
    main()
