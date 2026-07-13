# CPS - Codex Profile Switcher

[English](README.md) | [简体中文](docs/README.zh-CN.md) | [日本語](docs/README.ja.md) | [한국어](docs/README.ko.md)

```text
╔════════════════════════════════════════════════════════════════╗
║   CPS - Codex Profile Switcher                                 ║
╚════════════════════════════════════════════════════════════════╝

Version: 1.0.5
```

> CPS is a tiny terminal tool for using official Codex auth login with gateway forwarding.
>
> The core flow is: log in with Codex/ChatGPT auth, then route model requests through a stable gateway provider.

It keeps official auth and gateway routing separate:

```text
Auth login    -> auth.json / ChatGPT login
Gateway route -> config.toml / provider / model / base_url
```

Then it applies the pair without manually editing `~/.codex`.

```text
$ cps
Auth login + Gateway route -> ~/.codex
```

## Install

```bash
cd codex-profiles
python3 -m pip install -e .
```

Check:

```bash
cps --help
```

## Start

Open the TUI:

```bash
cps
```

![CPS TUI preview](docs/assets/cps-tui-preview.png)

Main flow:

```text
1. Choose one Auth login
2. Choose one Gateway route
3. Press Enter to review the draft pair, then confirm to apply
4. Press R to Restart Codex
```

Create profiles from the TUI:

```text
O Menu -> New Auth Login
O Menu -> New Gateway Route
```

## CLI Quick Commands

```bash
cps init auth personal
cps init route work
cps mix personal work
cps doctor
cps restart
```

Custom API route:

```bash
cps route custom \
  --base-url https://your-endpoint.example.com/v1 \
  --model gpt-5.5 \
  --api-key sk-...
```

Restore official route:

```bash
cps route official --model gpt-5.5
```

## Where Files Live

```text
~/.codex                 active Codex config
~/.codex-profiles        saved CPS profiles
~/.codex-profiles/.cps.lock serializes CPS writes
~/.codex-profiles/<profile>/profile.json non-secret profile metadata
~/.codex-profiles/deleted reversible deletes
~/.codex-profiles/backups switch-time backups
```

## Diagnose

```bash
cps doctor
```

`doctor` checks for common switch-time problems: missing Codex CLI, reserved
provider overrides such as `[model_providers.OpenAI]`, stale last-mix pointers,
missing auth files, and custom routes that may need a Codex restart before the
model picker refreshes.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZijiYu%2Fcodex-profile-switcher&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profile-switcher)
