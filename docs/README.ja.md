# CPS - Codex Profile Switcher

[English](../README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

> Note: this translation may lag behind the latest Auth + API / Route two-column TUI. See the English or Simplified Chinese README for the current interaction model.

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

CPS は、Codex の設定をすばやく切り替えるための小さなターミナルツールです。

多くの Codex ユーザーは、アカウントや設定を 1 つだけ使っているわけではありません。

たとえば：

```text
personal  -> 自分の ChatGPT アカウントでログイン
work      -> 会社の API key
proxy     -> カスタム base_url
test      -> 別のモデルやパラメータを一時的にテスト
```

毎回 `~/.codex/config.toml` を手で編集したり、`auth.json`、環境変数、API 設定を入れ替えたりすると、すぐに混乱します。個人アカウントと仕事用設定が混ざる原因にもなります。

CPS の仕組みはシンプルです。各 Codex 設定を独立した profile として保存し、必要なときに選択した profile を現在 Codex が使う `~/.codex` ディレクトリへ切り替えます。

次のように使えます：

```bash
cps use personal
cps use work
cps use proxy
```

切り替え後は Codex を再起動し、設定を再読み込みしてください。

CPS はデータベースを使わず、バックグラウンドにも常駐しません。ローカル設定ファイルを管理するだけなので、複数アカウント、複数 API、複数環境の Codex 利用を整理できます。

## Why

次のような場合に CPS は便利です：

- ChatGPT アカウントと API key の両方を持っている。
- 個人プロジェクトと仕事プロジェクトの Codex 設定を分けたい。
- `base_url`、モデル、provider をよく切り替える。
- 毎回 `~/.codex/config.toml` を手で編集したくない。
- 個人 auth、仕事用 API key、テスト設定を混ぜたくない。

## How It Works

CPS は profile を次の場所に保存します：

```bash
~/.codex-profiles
```

現在 Codex が使う設定は引き続き次の場所にあります：

```bash
~/.codex
```

次を実行すると：

```bash
cps use work
```

CPS は `work` profile を `~/.codex` に切り替え、Codex がその設定を使うようにします。

複数の設定を保存しておき、必要なものを有効化する小さな Codex 設定スイッチャーとして考えると分かりやすいです。

## Install

このプロジェクトディレクトリからインストール：

```bash
cd codex-profiles
python3 -m pip install -e .
```

コマンドが使えることを確認：

```bash
cps --help
```

またはスクリプトを直接実行：

```bash
./bin/cps
```

## Quick Start

まず現在の `~/.codex` から profile を作成します：

```bash
cps init personal
```

仕事用 API key など別の設定がある場合は、もう 1 つ作成します：

```bash
cps init work
```

profile ごとに Codex へログインします：

```bash
cps login personal
```

profile に切り替えます：

```bash
cps use personal
```

または：

```bash
cps use work
```

切り替え後は Codex を再起動し、`~/.codex/config.toml` を再読み込みしてください。

## Terminal UI

起動：

```bash
cps
```

TUI の構成：

```text
top       CPS logo と現在の active mode
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
cps status
cps list
cps deleted
cps path work
cps init work
cps save work
cps use work
cps login personal
cps delete old-profile
cps restore old-profile-20260612-153000
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

TUI では、API profile のディレクトリに `auth.json` が存在する場合があります。ただし profile mode が API の場合、CPS はその auth を ignored と表示します。

## Safety

`delete` は復元可能です。profile は次の場所に移動されます：

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

復元：

```bash
cps restore <deleted-profile>
```

CPS は profile を切り替える前に、現在 active な `~/.codex` ファイルもバックアップします。

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

[![Star History Chart](https://api.star-history.com/svg?repos=zijiyu%2Fcodex-profiles&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profiles)
