# CPS - Codex Profiles

[English](../README.md) | 简体中文 | 日本語 | 한국어

CPS 是一个 Codex 配置组合工具，用来管理不同的 Codex profile，并把登录态和 API 路由清晰地组合起来。

它可以帮助你快速切换：

* 不同 Codex 账号
* 不同 OpenAI API Key
* 不同 `base_url`
* 不同 provider / model 配置
* 不同 `config.toml`
* 不同 `auth.json`
* 不同项目或环境下的 Codex 配置

推荐用法是直接进入 TUI：

```bash
cps
```

在 TUI 中选择 Auth 和 API / Route 两列，按 `m` 应用组合，按 `R` 重启 Codex。比如你可以使用 personal 的 ChatGPT 登录态，同时让模型请求走 work 的 API route。

CPS 会把多套 Codex 配置保存在：

```bash
~/.codex-profiles
```

当前正在使用的配置仍然放在 Codex 默认目录：

```bash
~/.codex
```

也可以用命令行直接组合：

```bash
cps mix personal work
```

CPS 会把 `personal` 的 `auth.json` 和 `work` 的 `config.toml` 组合到 `~/.codex`，Codex 下次启动时就会使用这套 active 配置。

## 1.0.3 更新

* TUI 改为清晰的 Auth 和 API / Route 双列结构；
* 新增 `cps mix <auth> <route>`，并自动记住最近一次组合；
* 初始化拆分为 `cps init auth`、`cps init route` 和 `cps init full`；
* 新增官方 / 自定义 API route 辅助命令；
* TUI 支持按 `R` 重启 Codex，命令行支持 `cps restart`；
* 混合自定义 API route 时会自动规范 provider，避免 Codex 把自定义 route 当成官方 ChatGPT 登录态去刷新 token。

## 1.0.4 更新

* 创建 API route 和 Auth login 的流程统一放入全屏菜单；
* 新增 New API Route 和 New Auth Login 全屏表单；
* 主操作改名为 Apply Selection，强调应用当前选中的 Auth + API；
* 全屏页面支持滚动，小窗口下自动使用紧凑 logo；
* 新增 profile 名称校验和 provider 名称规范化，减少生成异常配置的风险。

## Hybrid Route

除了 Auth + Route 组合，CPS 也支持只编辑当前模型请求路由。

这适合一种很常见的情况：你想保留当前 ChatGPT 登录态，但让模型请求走自定义 OpenAI-compatible API。

比如：

```bash
cps route custom \
  --base-url https://your-endpoint.example.com/v1 \
  --model gpt-5.5 \
  --api-key sk-...
```

这个命令只会更新当前 `~/.codex/config.toml` 里的 provider、model、base_url 和 API token，不会替换 `auth.json`。

也就是说：

* ChatGPT 登录态会保留；
* 当前 `auth.json` 不会被覆盖；
* 模型请求会切到自定义 provider；
* 切换前会自动备份当前配置。

如果想切回官方 OpenAI provider：

```bash
cps route official --model gpt-5.5
```

Hybrid Route 适合临时切换 API 路由，不一定需要创建一整套新的 profile。日常使用更推荐在 TUI 中选择 Auth + API / Route 后按 `m` 应用。

在 TUI 中，CPS 会把 profile 拆成两列展示：

```text
Auth                  API / Route
> * personal [AUTH]   > * work [API]
    ...
```

`>` 表示当前光标所在项，`*` 表示已经选中的项。用 `Tab` 或左右方向键切换列，`Enter` 选择当前项，选好 Auth 和 API / Route 后按 `m` 应用组合，按 `R` 重启 Codex。组合后，CPS 会从 Auth profile 取 `auth.json`，从 Route profile 取 `config.toml` / `api.config.toml`，自动生成当前 active 配置，并记住最近一次组合。

## 使用场景

如果你只是固定使用一个 Codex 账号，可能不需要 CPS。

但如果你有下面这些情况，CPS 会很方便：

* 一个电脑上同时使用个人 Codex 账号和工作 Codex 账号；
* 有多个 OpenAI API Key，需要按项目切换；
* 有时使用官方 OpenAI API，有时使用自定义 `base_url`；
* 想保留 ChatGPT 登录态，但临时把模型请求路由到自定义 API；
* 需要在不同模型、不同 provider、不同配置文件之间切换；
* 不想每次都手动编辑 `~/.codex/config.toml`；
* 不想把个人账号、工作账号、代理配置混在一起。

## 安装

从当前项目目录安装：

```bash
cd codex-profiles
python3 -m pip install -e .
```

安装完成后检查命令：

```bash
cps --help
```

也可以直接运行：

```bash
./bin/cps
```

## 快速开始

创建一个 Auth profile，并进入 Codex 登录流程：

```bash
cps init auth personal
```

这个命令会为 `personal` 准备独立 profile 目录，然后运行 `codex login`，让这个 Auth profile 拥有自己的 `auth.json`。

从当前 `~/.codex` 创建一个 API / Route profile：

```bash
cps init route work
```

给指定 profile 登录 Codex：

```bash
cps login personal
```

组合 personal 登录态和 work API 路由：

```bash
cps mix personal work
```

只切换模型请求路由，保留当前 ChatGPT 登录态：

```bash
cps route custom \
  --base-url https://your-endpoint.example.com/v1 \
  --model gpt-5.5 \
  --api-key sk-...
```

完整替换为某个 profile 仍然可用，但这是高级用法：

```bash
cps use work
```

切换后重启 Codex，让它重新读取当前的 `~/.codex` 配置。

## 终端 UI

启动：

```bash
cps
```

TUI 布局：

```text
top       CPS logo 和当前 active 模式
left      Auth 和 API / Route 两列
right     activity 事件流
bottom    当前界面的快捷键状态栏
```

快捷键：

```text
Up/Down  选择 profile
Left/Right 或 Tab  切换 Auth / API 列
Enter    输入框为空时选择当前项
m        应用当前选择的 Auth + API / Route
o        打开菜单
R        重启 Codex
Esc      清空输入
?        显示/隐藏帮助
r        刷新
q        退出
```

Slash 命令：

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
/api new
/route custom --base-url https://your-endpoint.example.com/v1 --model gpt-5.5 --api-key sk-...
/route official --model gpt-5.5
/help
/quit
```

如果要创建新的 API route 或新的 Auth login，推荐在 TUI 中按 `o` 打开菜单。`/api new` 仍然作为高级命令保留；按 `?` 可以打开独立帮助页。

其中 `/use <profile>` 会用某个 profile 整套替换 `~/.codex`。日常组合 Auth 和 API / Route 时，优先使用 TUI 的两列选择或 `cps mix <auth> <route>`。

## CLI 命令

```bash
cps status
cps list
cps deleted
cps path work
cps init auth personal
cps init route work
cps login personal
cps delete old-profile
cps restore old-profile-20260612-153000
cps mix personal work
cps use work
cps route custom --base-url https://your-endpoint.example.com/v1 --model gpt-5.5 --api-key sk-...
cps route official --model gpt-5.5
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

Hybrid route：

```toml
model_provider = "custom"
preferred_auth_method = "chatgpt"

[model_providers.custom]
base_url = "https://your-endpoint.example.com/v1"
requires_openai_auth = true
wire_api = "responses"
experimental_bearer_token = "sk-..."
```

API profile 的目录里可能仍然存在 `auth.json`，但当 profile 模式是 API 时，CPS 会把这个 auth 标记为 ignored。

Hybrid routing 只编辑 `config.toml`。它会保留现有 `auth.json`，所以 ChatGPT 登录态仍然存在，而模型请求会走自定义 provider。

## 安全性

`delete` 是可恢复的。它会把 profile 移动到：

```text
~/.codex-profiles/deleted/<profile>-<timestamp>
```

恢复：

```bash
cps restore <deleted-profile>
```

CPS 在切换 profile 或 route 前，会备份当前 active 的 `~/.codex` 配置。

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
