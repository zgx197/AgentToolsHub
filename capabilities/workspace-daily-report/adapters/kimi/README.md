# Kimi Adapter Plan

`workspace-daily-report` 在 Kimi Code 侧更适合通过以下两种方式接入：

1. 直接调用 `core/generate_daily_report.py`
2. 后续包装成 MCP tool / MCP server

当前阶段先保留：

- 能力描述
- 单项目 `/.agenttools.json` 配置模型说明
- 后续接入方向

后续如需正式支持 Kimi Code，建议优先补：

- CLI 包装命令
- MCP server wrapper
