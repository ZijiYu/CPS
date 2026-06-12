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

CPX is a tiny terminal tool for switching Codex profiles, accounts, and API setups fast.

It solves a practical problem: many Codex users do not have just one account or one configuration.

For example:

```text
personal  -> your ChatGPT login
work      -> company API key
proxy     -> custom base_url
test      -> temporary model or parameter experiments
```

Manually editing `~/.codex/config.toml`, swapping `auth.json`, changing environment variables, or replacing API settings by hand gets messy quickly. It also makes it easy to mix personal accounts with work credentials.

CPX keeps each Codex setup as an independent profile. When you switch, CPX copies that profile into the active `~/.codex` directory, which is the directory Codex Desktop actually reads.

Use it like this:

```bash
cpx use personal
cpx use work
cpx use proxy
```

After switching, restart Codex so it reloads the active config.

No database. No daemon. No background service. CPX only manages local config files so multi-account, multi-API, and multi-environment Codex usage stays clean.

## Why

CPX is useful if:

- You have both a ChatGPT login and an API key.
- You want separate Codex configs for personal and work projects.
- You often switch between different `base_url`, model, or provider settings.
- You do not want to edit `~/.codex/config.toml` by hand every time.
- You want to avoid mixing personal auth, work API keys, and test settings.

## How It Works

CPX stores profiles in:

```bash
~/.codex-profiles
```

The active Codex config still lives in:

```bash
~/.codex
```

When you run:

```bash
cpx use work
```

CPX switches the `work` profile into `~/.codex`, so Codex uses that setup.

Think of it as a small Codex config switcher: keep many saved profiles, activate the one you need.

## Install

From this project directory:

```bash
cd codex-profiles
python3 -m pip install -e .
```

Confirm the command is available:

```bash
cpx --help
```

Or run the script directly:

```bash
./bin/cpx
```

## Quick Start

Create a profile from the current `~/.codex`:

```bash
cpx init personal
```

If you have another setup, such as a work API key, create another profile:

```bash
cpx init work
```

Login a profile separately:

```bash
cpx login personal
```

Switch to a profile:

```bash
cpx use personal
```

Or:

```bash
cpx use work
```

After switching, restart Codex so it reloads `~/.codex/config.toml`.

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

[![Star History Chart](https://api.star-history.com/svg?repos=zijiyu%2Fcodex-profiles&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profiles)
