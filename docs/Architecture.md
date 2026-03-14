# AgentToolsHub 架构说明

## 1. 设计目标

AgentToolsHub 不是单纯的 skill 收藏仓库，而是一个统一的 AI Agent 能力中心。

它要同时满足：

- 同一能力可被多个平台复用
- 核心逻辑与平台适配解耦
- 可通过 manifest 和 registry 做统一管理
- 可通过 portal 页面做简单浏览和检索

## 2. 分层结构

### 2.1 Capability Core

每个能力优先沉淀为平台无关的核心实现，例如：

- Python CLI
- 通用配置解析
- 事实提炼逻辑
- 输出渲染逻辑

### 2.2 Adapters

平台适配层只负责把核心能力包装成特定平台可消费的形式，例如：

- Codex skill
- Claude Code skill
- Kimi wrapper
- MCP 接入

### 2.3 Registry

仓库通过统一 `manifest.json` 收集能力元数据，再由脚本生成：

- 能力列表
- 平台支持情况
- 状态与版本
- 标签、入口、说明路径

### 2.4 Portal

Portal 是静态管理页，当前只承担：

- 浏览能力列表
- 查看 manifest 信息
- 跳转到仓库路径和文档

第一版不做在线编辑后台。

## 3. Manifest 约定

每个能力目录都应该提供一个 `manifest.json`，至少包含：

- `id`
- `name`
- `kind`
- `source_type`
- `status`
- `version`
- `description`
- `platforms`
- `tags`

## 4. 当前第一批能力

- `workspace-daily-report`

## 5. 推荐扩展方向

- 增加 capability 初始化脚本
- 增加 manifest 校验脚本
- 增加 MCP server skeleton
- 为 portal 增加筛选和搜索
