# CPX - Codex Profiles

[English](README.md) | [简体中文](docs/README.zh-CN.md) | [日本語](docs/README.ja.md) | [한국어](docs/README.ko.md)

```text
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   ██████╗ ██████╗ ██╗  ██╗                                     ║
║  ██╔════╝ ██╔══██╗╚██╗██╔╝                                     ║
║  ██║      ██████╔╝ ╚███╔╝                                      ║
║  ██║      ██╔═══╝  ██╔██╗                                      ║
║  ╚██████╗ ██║     ██╔╝ ██╗                                     ║
║   ╚═════╝ ╚═╝     ╚═╝  ╚═╝                                     ║
║                                                                ║
║   Codex Profiles                                               ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

  Version: 1.0  |  https://github.com/ZijiYu/codex-profiles
```

CPX is a tiny terminal tool for switching Codex Desktop profiles fast.

It keeps saved profiles in `~/.codex-profiles`, then copies the selected one into `~/.codex`, which is the config directory Codex Desktop actually reads.

## Why

Use it when you want one Codex setup for personal ChatGPT auth and another for API-key based work.

```text
personal -> auth login
work     -> OPENAI_API_KEY
```

No database. No daemon. No dependencies. Just small files and a terminal UI.

## Install

From this checkout:

```bash
cd /Users/ken/projects/discord/codex-profiles
python3 -m pip install -e .
```

Or run it directly:

```bash
/Users/ken/projects/discord/codex-profiles/bin/cpx
```

## Quick Start

Create or refresh profiles from the current `~/.codex`:

```bash
cpx init personal
cpx init work
```

Login a profile with its own `CODEX_HOME`:

```bash
cpx login personal
```

Switch profiles:

```bash
cpx use personal
cpx use work
```

After switching, restart Codex Desktop so it reloads `~/.codex/config.toml`.

## Terminal UI

Launch:

```bash
cpx
```

The TUI shows:

```text
top       CPX logo and active mode
left      saved profiles and deleted profiles
center    activity stream
bottom    command composer
```

Keyboard:

```text
Up/Down  select a profile
Enter    switch selected profile when input is empty
Esc      clear input
?        toggle help
r        refresh
q        quit
```

Slash commands:

```text
/status
/list
/use work
/login personal
/save work
/init personal
/delete old-profile
/deleted
/restore old-profile-20260612-153000
/path work
/help
/quit
```

## CLI Commands

```bash
cpx status
cpx list
cpx deleted
cpx path work
cpx init work
cpx save work
cpx use work
cpx login personal
cpx delete old-profile
cpx restore old-profile-20260612-153000
```

## Profile Modes

Auth profile:

```toml
[model_providers.OpenAI]
requires_openai_auth = true
```

API profile:

```toml
[model_providers.OpenAI]
env_key = "OPENAI_API_KEY"
```

In the TUI, API profiles may still show an `auth.json` file if one exists in the folder, but CPX marks that auth as ignored when the profile mode is API.

## Safety

`delete` is reversible. It moves profiles into:

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

Restore with:

```bash
cpx restore <deleted-profile>
```

CPX also backs up the current active `~/.codex` files before switching profiles.

## Files

```text
~/.codex
  active config used by Codex Desktop

~/.codex-profiles/<name>
  saved profile config

~/.codex-profiles/deleted
  reversible deletes

~/.codex-profiles/backups
  switch-time backups
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZijiYu/codex-profiles&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profiles)
