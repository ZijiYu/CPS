# CPS - Codex Profiles

[English](../README.md) | 简体中文 | 日本語 | 한국어

CPS 的核心是：先使用官方 Codex / ChatGPT auth 登录，再把模型请求转发到稳定的 gateway provider。

它可以帮助你管理：

* 官方 Codex 登录态，也就是不同 `auth.json`
* gateway 转发配置，也就是不同 `base_url` / provider / model
* 不同项目或环境下的 active `~/.codex` 配置

推荐用法是直接进入 TUI：

```bash
cps
```

在 TUI 中选择 Auth 和 Gateway 两列：按 `Space` 把当前项加入 draft，Auth 和 Gateway 都选好后按 `Enter` 查看确认提示，确认后才会写入 `~/.codex`；之后按 `R` 重启 Codex。比如你可以使用 personal 的 ChatGPT 登录态，同时让模型请求走 work 的 gateway route。

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

CPS 会把 `personal` 的 `auth.json` 和 `work` 的 `config.toml` 组合到 `~/.codex`，Codex 下次启动时就会使用这套 active 配置。组合后请看 `cps status` 里的 `auth_effect`：核心目标是让 route 使用官方登录态加 gateway 转发；如果 route 是 API-key route，`auth.json` 会被复制但模型请求会使用 API 凭据，登录态会显示为 ignored。

## 1.0.3 更新

* TUI 改为清晰的 Auth 和 Gateway 双列结构；
* 新增 `cps mix <auth> <route>`，并自动记住最近一次组合；
* 初始化拆分为 `cps init auth`、`cps init route` 和 `cps init full`；
* 新增官方 / 自定义 API route 辅助命令；
* TUI 支持按 `R` 重启 Codex，命令行支持 `cps restart`；
* 混合自定义 API route 时会自动规范 provider，避免 Codex 把自定义 route 当成官方 ChatGPT 登录态去刷新 token。

## 1.0.4 更新

* 创建 API route 和 Auth login 的流程统一放入全屏菜单；
* 新增 New Gateway Route 和 New Auth Login 全屏表单；
* TUI 会先把 Auth + Gateway 作为 draft，再通过 `Enter` + 确认应用，避免误写 active 配置；
* 全屏页面支持滚动，小窗口下自动使用紧凑 logo；
* 新增 profile 名称校验和 provider 名称规范化，减少生成异常配置的风险。
* `status` 会显示 `auth_effect`，区分登录态是被 route 使用还是只是存在于目录中。
* 新增 `cps doctor`，用于检查 Codex CLI、保留 provider、缺失 auth、last-mix 等常见问题。
* 写入 `~/.codex` 和 `~/.codex-profiles` 时会使用 `.cps.lock` 串行化，避免两个 CPS 进程互相覆盖。
* 新建 profile 会写入不含密钥的 `profile.json` 元数据，方便后续诊断和迁移。

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

* ChatGPT 登录态文件会保留；
* 当前 `auth.json` 不会被覆盖；
* 模型请求会切到自定义 provider，并按该 route 的配置决定使用 API 凭据还是 OpenAI auth；
* 切换前会自动备份当前配置。

如果想切回 ChatGPT 登录态路线：

```bash
cps route official --model gpt-5.5
```

这个命令仍会把 active `model_provider` 写成稳定的 `gateway`，但 provider section 会改成 `requires_openai_auth = true`，这样聊天记录不会因为 auth/api 切换而换分组。

Hybrid Route 适合临时切换 gateway 路由，不一定需要创建一整套新的 profile。日常使用更推荐在 TUI 中选择 Auth + Gateway，先形成 draft，再按 Enter 确认应用。

在 TUI 中，CPS 会把 profile 拆成两列展示：

```text
Auth                  Gateway
> * personal [AUTH]   > * work [API]
    ...
```

`>` 表示当前光标所在项，`*` 表示已经选中的 draft 项。用 `Tab` 或左右方向键切换列，`Space` 选择当前项为 draft；Auth 和 Gateway 都选好后，按 `Enter` 查看确认提示，确认后才会把组合写入 `~/.codex` 并记住最近一次组合；之后按 `R` 重启 Codex。

## 使用场景

如果你只是固定使用一个 Codex 账号，可能不需要 CPS。

但如果你有下面这些情况，CPS 会很方便：

* 一个电脑上同时使用个人 Codex 账号和工作 Codex 账号；
* 想保留官方 ChatGPT 登录态，但让模型请求走 gateway；
* 有多个 gateway `base_url`，需要按项目切换；
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

从当前 `~/.codex` 创建一个 Gateway route profile：

```bash
cps init route work
```

给指定 profile 登录 Codex：

```bash
cps login personal
```

组合 personal 登录态和 work gateway 路由：

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

检查当前配置和 profile：

```bash
cps doctor
```

`doctor` 会报告常见风险，比如找不到 Codex CLI、存在 Codex 保留的 `[model_providers.OpenAI]` 覆盖段、最近一次组合指向了已删除 profile、Auth profile 缺少 `auth.json`，以及自定义 route 可能需要重启 Codex 才能刷新模型列表。

## 终端 UI

启动：

```bash
cps
```

TUI 布局：

```text
top       CPS logo 和当前 active 模式
left      Auth 和 Gateway 两列
right     activity 事件流
bottom    当前界面的快捷键状态栏
```

快捷键：

```text
Up/Down  选择 profile
Left/Right 或 Tab  切换 Auth / Gateway 列
Space    选择当前项为 draft
Enter    输入框为空时查看并确认应用当前 Auth + Gateway draft
D        删除当前 profile（会先确认）
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

如果要创建新的 Gateway route 或新的 Auth login，推荐在 TUI 中按 `o` 打开菜单。`/api new` 仍然作为高级命令保留；按 `?` 可以打开独立帮助页。

其中 `/use <profile>` 会用某个 profile 整套替换 `~/.codex`。日常组合 Auth 和 Gateway 时，优先使用 TUI 两列选择；`cps mix <auth> <route>` 保留给脚本或高级命令行使用。

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
model_provider = "gateway"

[model_providers.gateway]
name = "gateway"
wire_api = "responses"
requires_openai_auth = true
```

API profile：

```toml
model_provider = "gateway"
model = "gpt-5.5"

[model_providers.gateway]
name = "gateway"
base_url = "https://your-endpoint.example.com/v1"
wire_api = "responses"
env_key = "OPENAI_API_KEY"
requires_openai_auth = false
```

Hybrid route：

```toml
model_provider = "gateway"
preferred_auth_method = "chatgpt"

[model_providers.gateway]
name = "gateway"
base_url = "https://your-endpoint.example.com/v1"
requires_openai_auth = true
wire_api = "responses"
experimental_bearer_token = "sk-..."
```

API profile 的目录里可能仍然存在 `auth.json`，但当 profile 模式是 API 时，CPS 会把这个 auth 标记为 ignored。也就是说文件在，不代表模型请求会使用这个登录账号。

Hybrid routing 只编辑 `config.toml`。它会保留现有 `auth.json`。只有 route 本身声明 `requires_openai_auth = true` 时，模型请求才会使用这个登录态；如果 route 使用 `env_key` 或 API token，则模型请求使用 API 凭据。

## 聊天记录不丢失

Codex Desktop 按 active 配置里的 `model_provider` 名字给聊天记录分组：一旦这个名字变了，旧名字下的对话就会从侧边栏消失（数据并没有删，只是被过滤掉了）。

为避免切换 profile 时聊天记录"消失"，CPS 会在每次写入 active 配置后（`mix` / `use` / `route custom` / `route official`）把 `model_provider` 统一归一化成同一个稳定名字，默认是 `gateway`：

* **自定义路由**（api / hybrid，带 `base_url` / `env_key` / `experimental_bearer_token`）会改名成 `[model_providers.gateway]`，路由键原样保留。
* **纯账号 / 官方**（没有自定义路由）也会写成 `[model_providers.gateway]`，但只保留 `wire_api = "responses"` 和 `requires_openai_auth = true`。

> 注意：`openai` 是 Codex 的保留内置 provider ID，配置里**不允许**出现 `[model_providers.openai]`（大小写都不行），否则 Codex 会报 `reserved built-in provider IDs` 并拒绝加载。所以稳定名必须是非保留的自定义名，CPS 也会自动清理掉历史遗留的非法 `[model_providers.OpenAI]` section。

如需自定义这个稳定名字（不能用 `openai`）：

```bash
export CODEX_ACTIVE_PROVIDER=gateway
```

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
