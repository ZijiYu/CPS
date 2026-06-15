# CPS - Codex Profile Switcher

[English](../README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

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

  Version: 1.0.2  |  https://github.com/ZijiYu/codex-profiles
```

CPS 是一个用来快速切换 Codex 配置的小工具。

它主要解决一个很实际的问题：很多人使用 Codex 时，并不是只有一种账号和配置。

比如：

```text
personal  -> 用自己的 ChatGPT 账号登录
work      -> 用公司的 API key
proxy     -> 使用自定义 base_url
test      -> 临时测试另一套模型或参数
```

如果每次都手动改 `~/.codex/config.toml`，或者来回替换 `auth.json`、环境变量和 API 配置，很容易乱，也很容易把个人账号和工作配置混在一起。

CPS 的做法很简单：把每一套 Codex 配置保存成一个独立的 profile。需要切换时，直接选择对应 profile，CPS 会把它切换到当前 Codex 使用的 `~/.codex` 目录。

也就是说，你可以像这样使用：

```bash
cps use personal
cps use work
cps use proxy
```

切换完成后，重启 Codex，让它重新读取配置即可。

CPS 不依赖数据库，也不会常驻后台。它只是帮你管理几套本地配置文件，让“多账号、多 API、多环境”的 Codex 使用方式变得更干净。

## 为什么需要它

如果你有下面这些情况，CPS 会比较有用：

- 你有一个 ChatGPT 账号，同时也有 API key；
- 你想把个人项目和工作项目的 Codex 配置分开；
- 你经常需要在不同 `base_url`、模型、provider 之间切换；
- 你不想每次都手动编辑 `~/.codex/config.toml`；
- 你担心把个人账号、工作 API key 或测试配置混在一起。

## 它怎么工作

CPS 会把 profile 保存在：

```bash
~/.codex-profiles
```

当前正在使用的 Codex 配置仍然放在：

```bash
~/.codex
```

当你运行：

```bash
cps use work
```

CPS 会把 `work` 这套 profile 切换到 `~/.codex`，让 Codex 使用这套配置。

你可以把它理解成一个 Codex 配置切换器：平时保存多套配置，需要哪套就切到哪套。

## 安装

从当前项目目录安装：

```bash
cd codex-profiles
python3 -m pip install -e .
```

安装后确认命令可用：

```bash
cps --help
```

也可以直接运行项目里的脚本：

```bash
./bin/cps
```

## 快速开始

先从当前 `~/.codex` 创建一个 profile：

```bash
cps init personal
```

如果你还有另一套配置，比如工作 API key，可以再创建一个：

```bash
cps init work
```

给某个 profile 单独登录 Codex：

```bash
cps login personal
```

切换到某个 profile：

```bash
cps use personal
```

或者：

```bash
cps use work
```

切换后请重启 Codex，让它重新读取 `~/.codex/config.toml`。

## 终端 UI

启动：

```bash
cps
```

TUI 布局：

```text
top       CPS logo 和当前 active 模式
left      已保存 profiles 和已删除 profiles
center    activity 事件流
bottom    命令输入框
```

快捷键：

```text
Up/Down  选择 profile
Enter    输入框为空时切换选中的 profile
Esc      清空输入
?        显示/隐藏帮助
r        刷新
q        退出
```

Slash 命令：

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

## CLI 命令

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

## Profile 模式

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

在 TUI 中，API profile 的目录里可能仍然存在 `auth.json`，但当 profile 模式是 API 时，CPS 会把这个 auth 标记为 ignored。

## 安全性

`delete` 是可恢复的。它会把 profile 移动到：

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

恢复：

```bash
cps restore <deleted-profile>
```

CPS 在切换 profile 前，也会备份当前 active 的 `~/.codex` 文件。

## 文件结构

```text
~/.codex
  Codex Desktop 正在使用的 active 配置

~/.codex-profiles/<name>
  已保存的 profile 配置

~/.codex-profiles/deleted
  可恢复删除

~/.codex-profiles/backups
  切换时自动备份
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=zijiyu%2Fcodex-profiles&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profiles)
