---
name: "workspace-daily-report"
description: "Generate Chinese developer daily reports from recent code changes. Use when Claude Code needs to turn git history, working tree changes, or multiple repo summaries into a detailed report and a concise report, especially for repo-root .agenttools.json based projects and multi-repo workspaces."
---

# Workspace Daily Report

## Overview

Use this skill to convert recent code changes into Chinese daily reports.
Prefer the bundled script for fact collection, then lightly polish the generated output instead of manually summarizing raw diffs.

## Workflow

1. Use `current-project` by default.
2. Use `workspace` only when the user explicitly asks for multiple repositories.
3. Run the bundled script first and treat its result as the factual base.
4. Keep the summary grounded in actual changed files and extracted facts.

## Commands

```powershell
python scripts/generate_daily_report.py --mode current-project --detail both --format markdown
python scripts/generate_daily_report.py --mode workspace --detail brief --format markdown
python scripts/generate_daily_report.py --mode workspace --discover-root D:/Work --format json
```

## Config

Configuration priority:

1. `--config <path>`
2. Current repo root `/.agenttools.json`
3. Fallback single-repo mode

Optional user config:

- `%USERPROFILE%/.agenttoolshub/user.json`

Use [assets/agenttools.project.template.json](./assets/agenttools.project.template.json) as the starter template.
Read [references/config-schema.md](./references/config-schema.md) before changing the config format.
