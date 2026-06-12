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

CPX 是一个很小的终端工具，用来快速切换 Codex Desktop 的 profile、账号和调用方式。

它会把多套 profile 保存到 `~/.codex-profiles`，切换时再把选中的 profile 复制到 `~/.codex`。`~/.codex` 是 Codex Desktop 实际读取配置的目录。

## 为什么需要它

当你想让一套 Codex 配置用于个人 ChatGPT 登录，另一套配置用于工作 API key 时，CPX 会很方便。

```text
personal -> auth login
work     -> OPENAI_API_KEY
```

没有数据库。没有守护进程。没有第三方依赖。只有一些小文件和一个终端 UI。

## 安装

从当前 checkout 安装：

```bash
cd /Users/ken/projects/discord/codex-profiles
python3 -m pip install -e .
```

也可以直接运行：

```bash
/Users/ken/projects/discord/codex-profiles/bin/cpx
```

## 快速开始

从当前 `~/.codex` 创建或刷新 profile：

```bash
cpx init personal
cpx init work
```

使用独立的 `CODEX_HOME` 登录某个 profile：

```bash
cpx login personal
```

切换 profile：

```bash
cpx use personal
cpx use work
```

切换后请重启 Codex Desktop，让它重新读取 `~/.codex/config.toml`。

## 终端 UI

启动：

```bash
cpx
```

TUI 布局：

```text
top       CPX logo 和当前 active 模式
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

在 TUI 中，API profile 的目录里可能仍然存在 `auth.json`，但当 profile 模式是 API 时，CPX 会把这个 auth 标记为 ignored。

## 安全性

`delete` 是可恢复的。它会把 profile 移动到：

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

恢复：

```bash
cpx restore <deleted-profile>
```

CPX 在切换 profile 前，也会备份当前 active 的 `~/.codex` 文件。

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

[![Star History Chart](https://api.star-history.com/svg?repos=ZijiYu/codex-profiles&type=Date)](https://www.star-history.com/?type=date&repos=ZijiYu%2Fcodex-profiles)
