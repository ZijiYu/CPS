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

  Version: 1.0.4  |  https://github.com/ZijiYu/codex-profiles
```

CPS는 Codex 설정을 빠르게 전환하기 위한 작은 터미널 도구입니다.

많은 Codex 사용자는 계정이나 설정을 하나만 쓰지 않습니다.

예를 들면:

```text
personal  -> 개인 ChatGPT 계정으로 로그인
work      -> 회사 API key
proxy     -> 커스텀 base_url
test      -> 다른 모델이나 파라미터 임시 테스트
```

매번 `~/.codex/config.toml`을 직접 수정하거나, `auth.json`, 환경 변수, API 설정을 바꾸다 보면 쉽게 헷갈립니다. 개인 계정과 업무 설정이 섞일 수도 있습니다.

CPS의 방식은 단순합니다. 각 Codex 설정을 독립적인 profile로 저장하고, 필요할 때 선택한 profile을 현재 Codex가 사용하는 `~/.codex` 디렉터리로 전환합니다.

다음처럼 사용할 수 있습니다:

```bash
cps use personal
cps use work
cps use proxy
```

전환 후에는 Codex를 재시작해서 설정을 다시 읽게 하면 됩니다.

CPS는 데이터베이스를 사용하지 않고, 백그라운드에 상주하지도 않습니다. 로컬 설정 파일만 관리해서 여러 계정, 여러 API, 여러 환경을 더 깔끔하게 사용할 수 있게 합니다.

## Why

다음과 같은 경우 CPS가 유용합니다:

- ChatGPT 계정과 API key를 모두 가지고 있다.
- 개인 프로젝트와 업무 프로젝트의 Codex 설정을 분리하고 싶다.
- 서로 다른 `base_url`, 모델, provider를 자주 전환한다.
- 매번 `~/.codex/config.toml`을 직접 편집하고 싶지 않다.
- 개인 auth, 업무 API key, 테스트 설정이 섞이는 것을 피하고 싶다.

## How It Works

CPS는 profile을 다음 위치에 저장합니다:

```bash
~/.codex-profiles
```

현재 Codex가 사용하는 설정은 계속 다음 위치에 있습니다:

```bash
~/.codex
```

다음을 실행하면:

```bash
cps use work
```

CPS는 `work` profile을 `~/.codex`로 전환하고, Codex가 해당 설정을 사용하게 합니다.

여러 설정을 저장해 두고 필요한 설정만 활성화하는 작은 Codex 설정 전환기로 이해하면 됩니다.

## Install

현재 프로젝트 디렉터리에서 설치:

```bash
cd codex-profiles
python3 -m pip install -e .
```

명령이 사용 가능한지 확인:

```bash
cps --help
```

또는 스크립트를 직접 실행:

```bash
./bin/cps
```

## Quick Start

먼저 현재 `~/.codex`에서 profile을 만듭니다:

```bash
cps init personal
```

업무 API key 같은 다른 설정이 있다면 하나 더 만듭니다:

```bash
cps init work
```

profile별로 Codex에 로그인합니다:

```bash
cps login personal
```

profile로 전환:

```bash
cps use personal
```

또는:

```bash
cps use work
```

전환 후에는 Codex를 재시작해서 `~/.codex/config.toml`을 다시 읽게 하세요.

## Terminal UI

실행:

```bash
cps
```

TUI 구성:

```text
top       CPS logo와 현재 active mode
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

TUI에서 API profile 폴더에 `auth.json` 파일이 남아 있을 수 있습니다. 하지만 profile mode가 API이면 CPS는 해당 auth를 ignored로 표시합니다.

## Safety

`delete`는 복구 가능합니다. profile은 다음 위치로 이동됩니다:

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

복구:

```bash
cps restore <deleted-profile>
```

CPS는 profile을 전환하기 전에 현재 active 상태인 `~/.codex` 파일도 백업합니다.

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

[![Star History Chart](https://api.star-history.com/svg?repos=zijiyu%2Fcodex-profiles&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profiles)
