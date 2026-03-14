# AgentToolsHub

AgentToolsHub 是一个面向个人长期维护的 AI Agent 能力仓库，用来集中管理可复用的：

- Skill
- MCP Server / MCP Tool
- CLI 工作流工具
- 配置模板与项目预设
- 平台适配器与安装脚本

当前目标不是只服务某一个平台，而是把同一份能力同时沉淀为：

- `Codex` 可安装的 skill
- `Claude Code` 可安装的 skill
- `Kimi Code` 可接入的 wrapper / MCP
- 可独立运行的 CLI 核心

## 仓库定位

本仓库按“能力”组织，而不是按平台组织。

一个能力目录通常包含：

- `core/`：真正的核心逻辑
- `adapters/`：Codex / Claude / Kimi 等平台适配层
- `configs/`：schema、示例配置、渲染模板
- `manifest.json`：统一元数据入口

这样同一个能力只维护一份核心实现，平台差异尽量收敛在 adapter 层。

## 项目接入原则

业务项目内只保留一份配置文件：

- `/.agenttools.json`

除此之外，项目仓库里不再维护：

- skill 源码副本
- adapter 副本
- portal 资源
- 安装脚本

个人信息和工具级默认项建议放在用户配置中，例如：

- `%USERPROFILE%/.agenttoolshub/user.json`

## 当前结构

```text
AgentToolsHub/
  capabilities/         # 按能力组织的主目录
  mcp-servers/          # MCP 服务或占位目录
  presets/              # 通用项目预设
  registry/             # 统一注册表与生成产物
  apps/portal/          # 简单管理页面
  scripts/              # 仓库级工具脚本
  docs/                 # 架构与规范文档
```

## 当前已落地能力

### `workspace-daily-report`

根据 Git 提交和工作区变动，按“项目 -> 模块 -> 事实”的方式生成：

- 详细日报
- 简要日报
- 结构化 JSON 摘要

当前能力已经包含：

- 核心 CLI 脚本
- Codex skill wrapper
- Claude Code skill wrapper
- Kimi 接入说明占位
- 单项目 `/.agenttools.json` 模板
- adapter 安装脚本

## 使用方式

### 1. 给项目放置 `/.agenttools.json`

示例模板见：

- [capabilities/workspace-daily-report/configs/examples/dot-agenttools.json](./capabilities/workspace-daily-report/configs/examples/dot-agenttools.json)

### 2. 管理 adapter

安装 Codex adapter：

```powershell
python scripts/install_adapter.py workspace-daily-report codex --force
```

卸载 Codex adapter：

```powershell
python scripts/uninstall_adapter.py workspace-daily-report codex --missing-ok
```

同步 Codex adapter：

```powershell
python scripts/sync_adapter.py workspace-daily-report codex
```

Claude adapter 也使用同样的三件套；如果没有默认目录，请显式传 `--target-root "<your-claude-skill-dir>"`。

### 3. 生成注册表

```powershell
python scripts/build_registry.py
```

### 4. 打开管理页

管理页位于：

- [apps/portal/index.html](./apps/portal/index.html)

页面会读取：

- [registry/generated/index.json](./registry/generated/index.json)

如果本地直接双击打开页面时浏览器禁止 `fetch(file://...)`，请用一个简单静态服务器打开目录。

## 后续方向

- 把当前 `workspace-daily-report` 继续抽象成更通用的配置驱动能力
- 为更多能力补齐 `manifest -> registry -> portal` 这一套链路
- 继续补 MCP Server 与安装脚本
- 增加 capability 初始化和配置校验脚本

## 维护约定

- 新能力优先落在 `capabilities/`
- 平台适配层尽量薄，不重复实现核心逻辑
- 所有能力统一提供 `manifest.json`
- 项目侧默认只维护 `/.agenttools.json`
- 文档尽量中文为主，必要时补少量英文元数据

