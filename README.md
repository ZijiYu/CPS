# CPS - Codex Profile Switcher

[English](README.md) | [简体中文](docs/README.zh-CN.md) | [日本語](docs/README.ja.md) | [한국어](docs/README.ko.md)

```text
╔════════════════════════════════════════════════════════════════╗
║   CPS - Codex Profile Switcher                                 ║
╚════════════════════════════════════════════════════════════════╝

Version: 1.0.4
```

> CPS is a tiny terminal tool for composing Codex auth profiles and API routes fast.
>
> Many Codex users do not have just one account, one API key, or one configuration.

It lets you keep Auth and API / Route configs separate:

```text
Auth        -> auth.json / ChatGPT login
API / Route -> config.toml / provider / model / base_url / API key
```

Then you can combine them without manually editing `~/.codex`.

```text
$ cps
Auth profile + API route -> ~/.codex
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

Main flow:

```text
1. Choose one Auth profile
2. Choose one API / Route profile
3. Press M to Apply Selection
4. Press R to Restart Codex
```

Create profiles from the TUI:

```text
O Menu -> New Auth Login
O Menu -> New API Route
```

## CLI Quick Commands

```bash
cps init auth personal
cps init route work
cps mix personal work
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
~/.codex-profiles/deleted reversible deletes
~/.codex-profiles/backups switch-time backups
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZijiYu%2Fcodex-profile-switcher&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profile-switcher)
