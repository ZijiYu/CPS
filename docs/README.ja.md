# CPX - Codex Profiles

[English](../README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

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

CPX は、Codex Desktop の profile、アカウント、呼び出し方式をすばやく切り替えるための小さなターミナルツールです。

複数の profile を `~/.codex-profiles` に保存し、選択した profile を `~/.codex` にコピーします。`~/.codex` は Codex Desktop が実際に設定を読むディレクトリです。

## Why

個人用の ChatGPT auth ログインと、仕事用の API key 設定を分けたいときに便利です。

```text
personal -> auth login
work     -> OPENAI_API_KEY
```

データベースなし。デーモンなし。依存パッケージなし。小さなファイルとターミナル UI だけです。

## Install

この checkout からインストール：

```bash
cd /Users/ken/projects/discord/codex-profiles
python3 -m pip install -e .
```

または直接実行：

```bash
/Users/ken/projects/discord/codex-profiles/bin/cpx
```

## Quick Start

現在の `~/.codex` から profile を作成または更新します：

```bash
cpx init personal
cpx init work
```

独立した `CODEX_HOME` で profile にログインします：

```bash
cpx login personal
```

profile を切り替えます：

```bash
cpx use personal
cpx use work
```

切り替え後は、Codex Desktop を再起動して `~/.codex/config.toml` を再読み込みしてください。

## Terminal UI

起動：

```bash
cpx
```

TUI の構成：

```text
top       CPX logo と現在の active mode
left      保存済み profiles と削除済み profiles
center    activity stream
bottom    command composer
```

キーボード：

```text
Up/Down  profile を選択
Enter    入力欄が空のとき、選択中の profile に切り替え
Esc      入力をクリア
?        ヘルプを表示/非表示
r        更新
q        終了
```

Slash commands：

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

Auth profile：

```toml
[model_providers.OpenAI]
requires_openai_auth = true
```

API profile：

```toml
[model_providers.OpenAI]
env_key = "OPENAI_API_KEY"
```

TUI では、API profile のディレクトリに `auth.json` が存在する場合があります。ただし profile mode が API の場合、CPX はその auth を ignored と表示します。

## Safety

`delete` は復元可能です。profile は次の場所に移動されます：

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

復元：

```bash
cpx restore <deleted-profile>
```

CPX は profile を切り替える前に、現在 active な `~/.codex` ファイルもバックアップします。

## Files

```text
~/.codex
  Codex Desktop が使用する active config

~/.codex-profiles/<name>
  保存済み profile config

~/.codex-profiles/deleted
  復元可能な削除

~/.codex-profiles/backups
  切り替え時の自動バックアップ
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZijiYu/codex-profiles&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profiles)
