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

CPX는 Codex Desktop의 profile, 계정, 호출 방식을 빠르게 전환하기 위한 작은 터미널 도구입니다.

여러 profile을 `~/.codex-profiles`에 저장하고, 선택한 profile을 `~/.codex`로 복사합니다. `~/.codex`는 Codex Desktop이 실제로 설정을 읽는 디렉터리입니다.

## Why

개인용 ChatGPT auth 로그인과 업무용 API key 설정을 분리하고 싶을 때 유용합니다.

```text
personal -> auth login
work     -> OPENAI_API_KEY
```

데이터베이스도 없고, 데몬도 없고, 외부 의존성도 없습니다. 작은 파일들과 터미널 UI만 있습니다.

## Install

현재 checkout에서 설치:

```bash
cd /Users/ken/projects/discord/codex-profiles
python3 -m pip install -e .
```

또는 직접 실행:

```bash
/Users/ken/projects/discord/codex-profiles/bin/cpx
```

## Quick Start

현재 `~/.codex`에서 profile을 만들거나 갱신합니다:

```bash
cpx init personal
cpx init work
```

독립적인 `CODEX_HOME`으로 profile에 로그인합니다:

```bash
cpx login personal
```

profile 전환:

```bash
cpx use personal
cpx use work
```

전환 후에는 Codex Desktop을 재시작해서 `~/.codex/config.toml`을 다시 읽게 하세요.

## Terminal UI

실행:

```bash
cpx
```

TUI 구성:

```text
top       CPX logo와 현재 active mode
left      저장된 profiles와 삭제된 profiles
center    activity stream
bottom    command composer
```

키보드:

```text
Up/Down  profile 선택
Enter    입력창이 비어 있을 때 선택한 profile로 전환
Esc      입력 지우기
?        도움말 표시/숨김
r        새로고침
q        종료
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

TUI에서 API profile 폴더에 `auth.json` 파일이 남아 있을 수 있습니다. 하지만 profile mode가 API이면 CPX는 해당 auth를 ignored로 표시합니다.

## Safety

`delete`는 복구 가능합니다. profile은 다음 위치로 이동됩니다:

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

복구:

```bash
cpx restore <deleted-profile>
```

CPX는 profile을 전환하기 전에 현재 active 상태인 `~/.codex` 파일도 백업합니다.

## Files

```text
~/.codex
  Codex Desktop이 사용하는 active config

~/.codex-profiles/<name>
  저장된 profile config

~/.codex-profiles/deleted
  복구 가능한 삭제

~/.codex-profiles/backups
  전환 시 자동 백업
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZijiYu/codex-profiles&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profiles)
