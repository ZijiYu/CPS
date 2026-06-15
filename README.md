# CPS - Codex Profile Switcher

[English](README.md) | [简体中文](docs/README.zh-CN.md) | [日本語](docs/README.ja.md) | [한국어](docs/README.ko.md)

```text
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   ██████╗ ██████╗ ███████╗                                     ║
║  ██╔════╝ ██╔══██╗██╔════╝                                     ║
║  ██║      ██████╔╝███████╗                                     ║
║  ██║      ██╔═══╝ ╚════██║                                     ║
║  ╚██████╗ ██║     ███████║                                     ║
║   ╚═════╝ ╚═╝     ╚══════╝                                     ║
║                                                                ║
║   Codex Profile Switcher                                       ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

  Version: 1.0.3  |  https://github.com/ZijiYu/codex-profiles
```

CPS is a tiny terminal tool for composing Codex auth profiles and API routes fast.

It solves a practical problem: many Codex users do not have just one account or one configuration.

For example:

```text
personal  -> your ChatGPT login
work      -> company API key
proxy     -> custom base_url
test      -> temporary model or parameter experiments
```

Manually editing `~/.codex/config.toml`, swapping `auth.json`, changing environment variables, or replacing API settings by hand gets messy quickly. It also makes it easy to mix personal accounts with work credentials.

CPS keeps Codex setups as profiles, then lets you choose which profile provides `auth.json` and which profile provides the API route config. The composed result is written into the active `~/.codex` directory, which is the directory Codex Desktop actually reads.

Open the TUI:

```bash
cps
```

Select one Auth item and one API / Route item, press `m` to apply the mix, then press `R` to restart Codex.

No database. No daemon. No background service. CPS only manages local config files so multi-account, multi-API, and multi-environment Codex usage stays clean.

## Update 1.0.3

- Reworked the default TUI around two explicit columns: Auth and API / Route.
- Added hybrid composition with `cps mix <auth> <route>` and automatic last-mix restore.
- Split initialization into `cps init auth`, `cps init route`, and `cps init full`.
- Added route helpers for official and custom OpenAI-compatible API endpoints.
- Added Codex restart support from the TUI with `R` and from the CLI with `cps restart`.
- Normalized custom API providers during hybrid mix to avoid Codex treating custom routes as official ChatGPT auth refreshes.

## Why

CPS is useful if:

- You have both a ChatGPT login and an API key.
- You want separate Codex configs for personal and work projects.
- You often switch between different `base_url`, model, or provider settings.
- You do not want to edit `~/.codex/config.toml` by hand every time.
- You want to avoid mixing personal auth, work API keys, and test settings.

## How It Works

CPS stores profiles in:

```bash
~/.codex-profiles
```

The active Codex config still lives in:

```bash
~/.codex
```

When you run:

```bash
cps mix personal work
```

CPS writes `auth.json` from `personal` and route config from `work` into `~/.codex`, so Codex uses that composed active setup.

Think of it as a small Codex config switcher: keep many saved profiles, activate the one you need.

## Install

From this project directory:

```bash
cd codex-profiles
python3 -m pip install -e .
```

Confirm the command is available:

```bash
cps --help
```

Or run the script directly:

```bash
./bin/cps
```

## Quick Start

Create an Auth profile and start Codex login:

```bash
cps init auth personal
```

This prepares an isolated profile directory for `personal`, then runs `codex login` so that Auth profile gets its own `auth.json`.

Create an API / Route profile from the current `~/.codex`:

```bash
cps init route work
```

Login a profile separately:

```bash
cps login personal
```

Compose personal auth with work API route:

```bash
cps mix personal work
```

Replacing `~/.codex` with a full profile is still available as an advanced command:

```bash
cps use work
```

After switching, restart Codex so it reloads `~/.codex/config.toml`.

Route model calls through a custom OpenAI-compatible endpoint while preserving the current ChatGPT login:

```bash
cps route custom \
  --base-url https://your-endpoint.example.com/v1 \
  --model gpt-5.5 \
  --api-key sk-...
```

Switch routing back to the official provider without replacing `auth.json`:

```bash
cps route official --model gpt-5.5
```

Combine auth from one profile with route config from another:

```bash
cps mix personal work
```

## Terminal UI

Launch:

```bash
cps
```

The TUI shows:

```text
top       CPS logo and active mode
left      Auth and API / Route columns
right     activity stream
bottom    command composer
```

Keyboard:

```text
Up/Down  select a profile
Left/Right or Tab  switch Auth / API column
Enter    select current item when input is empty
m        apply selected Auth + API / Route mix
Esc      clear input
?        toggle help
r        refresh
q        quit
```

Slash commands:

```text
/status
/list
/login personal
/init auth personal
/init route work
/delete old-profile
/deleted
/restore old-profile-20260612-153000
/path work
/mix personal work
/route custom --base-url https://your-endpoint.example.com/v1 --model gpt-5.5 --api-key sk-...
/route official --model gpt-5.5
/help
/quit
```

`/use <profile>` replaces `~/.codex` with a full profile. For day-to-day Auth + API composition, prefer the two-column TUI or `cps mix <auth> <route>`.

## CLI Commands

```bash
cps status
cps list
cps deleted
cps path work
cps init auth personal
cps init route work
cps use work
cps login personal
cps delete old-profile
cps restore old-profile-20260612-153000
cps mix personal work
cps route custom --base-url https://your-endpoint.example.com/v1 --model gpt-5.5 --api-key sk-...
cps route official --model gpt-5.5
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

In the TUI, API profiles may still show an `auth.json` file if one exists in the folder, but CPS marks that auth as ignored when the profile mode is API.

Hybrid route:

```toml
model_provider = "custom"
preferred_auth_method = "chatgpt"

[model_providers.custom]
base_url = "https://your-endpoint.example.com/v1"
requires_openai_auth = true
wire_api = "responses"
experimental_bearer_token = "sk-..."
```

Hybrid routing edits `config.toml` only. It preserves the existing `auth.json`, so ChatGPT login stays in place while model calls use the custom provider.

## Safety

`delete` is reversible. It moves profiles into:

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

Restore with:

```bash
cps restore <deleted-profile>
```

CPS also backs up the current active `~/.codex` files before switching profiles.

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
