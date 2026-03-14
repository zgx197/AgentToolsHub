---
name: "workspace-daily-report"
description: "Generate Chinese developer daily reports from recent code changes. Use when Codex needs to turn git history, working tree changes, or multiple repo summaries into a detailed report and a concise report, especially for repo-root .agenttools.json based projects and multi-repo workspaces."
---

# Workspace Daily Report

## Overview

Use this skill to convert recent code changes into Chinese daily reports.
Prefer the bundled script for fact collection, then lightly polish the generated output instead of summarizing raw diffs by hand.

## Workflow

1. Use `current-project` by default.
2. Use `workspace` only when the user explicitly asks for multiple repositories or the whole workspace.
3. Run the bundled script first and treat its result as the factual base.
4. Keep the summary grounded in changed files, commit subjects, and extracted facts.
5. Return `detailed` and `brief` outputs when the user would benefit from both.

## Commands

Current project:

```powershell
python scripts/generate_daily_report.py --mode current-project --detail both --format markdown
```

Sibling repositories with `/.agenttools.json`:

```powershell
python scripts/generate_daily_report.py --mode workspace --detail both --format markdown
```

Explicit workspace discovery root:

```powershell
python scripts/generate_daily_report.py --mode workspace --discover-root D:/Work --detail brief --format markdown
```

Override the author:

```powershell
python scripts/generate_daily_report.py --author "张国鑫" --detail brief --format markdown
```

Inspect raw structured facts:

```powershell
python scripts/generate_daily_report.py --mode current-project --format json
```

## Config

The script resolves configuration in this order:

1. `--config <path>`
2. Current git repo root `/.agenttools.json`
3. Fallback single-repo mode with no module mapping

Optional user config:

- `%USERPROFILE%/.agenttoolshub/user.json`

Read [references/config-schema.md](./references/config-schema.md) before changing the config format.
Use [assets/agenttools.project.template.json](./assets/agenttools.project.template.json) as the starter template for a new project.

## Output Guidance

- Prefer `作者 -> 昨日完成 -> 项目 -> 模块 -> 结果` for detailed output.
- Prefer `作者 -> 昨日完成 -> 3-5 条关键结果` for brief output.
- Collapse file-level noise into module-level outcomes.
- Mention tests, docs, and config/codegen work explicitly when they were part of the change set.
