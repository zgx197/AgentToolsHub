# workspace-daily-report

`workspace-daily-report` 是 AgentToolsHub 的第一个能力示例，用来根据代码仓库最近一段时间的变动生成：

- 详细日报
- 简要日报
- 结构化 JSON 结果

## 目录说明

```text
workspace-daily-report/
  manifest.json
  README.md
  assets/                     # 模板配置等静态资源
  core/                       # 平台无关的 CLI 核心
  configs/
    config-schema.md
    examples/                 # 项目示例配置
  adapters/
    codex/
    claude/
    kimi/
```

## 当前配置模型

这个能力不再依赖 skill 自带的 workspace 配置文件。

默认配置发现顺序为：

1. `--config <path>`
2. 当前 git repo 根目录的 `/.agenttools.json`
3. 无配置时退化为单仓库默认模式

可选的用户级配置文件：

- `%USERPROFILE%/.agenttoolshub/user.json`

可用于提供：

- `default_author`
- `default_language`
- `default_mode`

## workspace 模式说明

当使用 `--mode workspace` 时，脚本会：

- 先确定当前 repo
- 默认扫描当前 repo 父目录下的同级仓库
- 只纳入包含 `/.agenttools.json` 的仓库
- 也可以通过 `--discover-root <path>` 显式指定扫描根目录

这样就不再需要单独维护一份“workspace 级配置文件”。

## 当前实现状态

- `core/` 已可运行
- `codex` wrapper 已可作为完整 skill 目录使用
- `claude` wrapper 已补齐基础 skill 目录
- `kimi` 目前保留为接入说明，后续更适合走 CLI / MCP 适配

## 推荐使用方式

优先使用 `core/generate_daily_report.py` 作为能力核心，再由平台 wrapper 调用。

## 示例命令

当前项目：

```powershell
python capabilities/workspace-daily-report/core/generate_daily_report.py --mode current-project --detail both --format markdown
```

扫描同级多个项目：

```powershell
python capabilities/workspace-daily-report/core/generate_daily_report.py --mode workspace --detail both --format markdown
```

指定扫描根目录：

```powershell
python capabilities/workspace-daily-report/core/generate_daily_report.py --mode workspace --discover-root D:/Work --detail brief --format markdown
```

## 相关资源

- 模板配置：[assets/agenttools.project.template.json](./assets/agenttools.project.template.json)
- 项目示例：[configs/examples/dot-agenttools.json](./configs/examples/dot-agenttools.json)
- 配置说明：[configs/config-schema.md](./configs/config-schema.md)

## 当前限制

- 事实提炼规则仍偏工程启发式，还没有完全配置驱动
- Kimi 侧还没有做成正式 MCP wrapper
- 管理页目前是静态展示页
