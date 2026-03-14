# Config Schema

`workspace-daily-report` 的项目配置文件固定放在 git repo 根目录：

- `/.agenttools.json`

## 项目配置结构

```json
{
  "project": {
    "id": "project-alpha",
    "name": "Project Alpha"
  },
  "capabilities": {
    "workspace-daily-report": {
      "report_title": "Project Alpha 开发",
      "ignore_globs": [
        "UnityProject/Library/**"
      ],
      "module_rules": []
    }
  }
}
```

## `project` 字段

```json
{
  "id": "project-alpha",
  "name": "Project Alpha"
}
```

字段说明：

- `id`：稳定的机器可读项目标识
- `name`：人类可读项目名称

如果缺失，脚本会退化为使用 git repo 目录名。

## `capabilities.workspace-daily-report` 字段

```json
{
  "report_title": "Project Alpha 开发",
  "ignore_globs": [
    "UnityProject/Library/**"
  ],
  "module_rules": []
}
```

字段说明：

- `report_title`：日报里显示的项目标题
- `ignore_globs`：项目级忽略规则
- `module_rules`：模块归类规则，按顺序匹配，首个命中即生效

## `module_rules` 结构

```json
{
  "module": "Runtime 功能",
  "paths": [
    "UnityProject/Packages",
    "UnityProject/Assets/Scripts/Runtime"
  ]
}
```

字段说明：

- `module`：用于日报分组的人类可读模块名
- `paths`：相对于 repo root 的路径前缀或 glob

## 用户级配置

可选的用户级配置文件：

- `%USERPROFILE%/.agenttoolshub/user.json`

示例：

```json
{
  "default_author": "张三",
  "default_language": "zh-CN",
  "default_mode": "current-project"
}
```

这些字段不建议放进项目仓库。

## workspace 模式发现逻辑

当使用 `--mode workspace` 时：

1. 先确定当前 repo
2. 默认扫描当前 repo 父目录下的同级目录
3. 只采集同时满足以下条件的目录：
   - 是一个 git repo 根目录
   - 包含 `/.agenttools.json`
4. 也可通过 `--discover-root <path>` 指定扫描根目录

## 兼容性

当前脚本仍兼容旧的 legacy workspace config：

- 顶层存在 `projects` 字段的 JSON

这只是迁移期兼容，不建议继续新增此类配置。
