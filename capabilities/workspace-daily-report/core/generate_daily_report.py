from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable


PROJECT_CONFIG_NAME = ".agenttools.json"
DEFAULT_LOOKBACK_DAYS = 2
MAX_DIFF_LINES = 220
MAX_GROUP_FACTS = 5
MAX_COMMIT_SUBJECTS_PER_MODULE = 3
DEFAULT_BUILTIN_IGNORE_GLOBS = [
    "**/.git/**",
    "**/.vs/**",
    "**/.vscode/**",
    "**/Library/**",
    "**/Temp/**",
    "**/Obj/**",
    "**/obj/**",
    "**/bin/**",
    "**/Logs/**",
    "**/UserSettings/**",
    "**/*.meta",
    "**/*.csproj",
    "**/*.sln",
    "**/*.dll",
    "**/*.pdb",
    "**/*.exe",
    "**/*.png",
    "**/*.jpg",
    "**/*.jpeg",
    "**/*.tga",
    "**/*.psd",
    "**/*.fbx",
    "**/*.mat",
    "**/*.prefab",
    "**/*.unity",
    "**/*.asset",
    "**/*.sqlite",
    "**/*.bytes",
    "**/*.log",
]


@dataclass
class ModuleRule:
    module: str
    paths: list[str]


@dataclass
class ProjectConfig:
    id: str
    display_name: str
    repo_root: Path
    report_title: str
    ignore_globs: list[str] = field(default_factory=list)
    module_rules: list[ModuleRule] = field(default_factory=list)


@dataclass
class UserConfig:
    default_author: str = ""
    default_language: str = "zh-CN"
    default_mode: str = "current-project"


@dataclass
class WorkspaceConfig:
    default_author: str
    default_language: str
    default_mode: str
    builtin_ignore_globs: list[str]
    projects: list[ProjectConfig]


@dataclass
class FileChange:
    project_id: str
    project_name: str
    report_title: str
    module: str
    path: str
    abs_path: Path | None
    status: str
    source: str
    changed_at: datetime | None
    diff_excerpt: str = ""
    tags: set[str] = field(default_factory=set)


@dataclass
class CommitFact:
    project_id: str
    project_name: str
    report_title: str
    module: str
    subject: str
    commit_id: str
    committed_at: datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate detailed and brief Chinese daily reports from git repositories using repo-root .agenttools.json config."
    )
    parser.add_argument("--mode", choices=("current-project", "workspace"), default=None)
    parser.add_argument("--config", help="Optional path to a repo project config or legacy workspace config JSON.")
    parser.add_argument("--user-config", help="Optional path to user-level config JSON.")
    parser.add_argument("--discover-root", help="Optional root directory used when workspace mode scans sibling repositories.")
    parser.add_argument("--author", help="Override report author.")
    parser.add_argument("--since", help="Inclusive start date/time, e.g. 2026-03-13 or 2026-03-13T09:00:00.")
    parser.add_argument("--until", help="Exclusive end date/time, e.g. 2026-03-15 or 2026-03-15T09:00:00.")
    parser.add_argument("--detail", choices=("detailed", "brief", "both"), default="both")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--cwd", help="Working directory used to detect the current project. Defaults to process cwd.")
    return parser.parse_args()


def parse_datetime(value: str) -> datetime:
    normalized = value.strip()
    if "T" in normalized:
        return datetime.fromisoformat(normalized)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        return datetime.fromisoformat(normalized)
    return datetime.fromisoformat(normalized.replace(" ", "T"))


def load_user_config(args: argparse.Namespace) -> UserConfig:
    explicit_path = Path(args.user_config).resolve() if args.user_config else None
    env_path = Path(os.environ["AGENTTOOLS_USER_CONFIG"]).resolve() if os.environ.get("AGENTTOOLS_USER_CONFIG") else None
    default_path = Path.home() / ".agenttoolshub" / "user.json"

    config_path = explicit_path or env_path or default_path
    if not config_path.exists():
        return UserConfig()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    return UserConfig(
        default_author=data.get("default_author", ""),
        default_language=data.get("default_language", "zh-CN"),
        default_mode=data.get("default_mode", "current-project"),
    )


def load_workspace_config(args: argparse.Namespace, cwd: Path, requested_mode: str, user_config: UserConfig) -> WorkspaceConfig:
    if args.config:
        config_path = Path(args.config).resolve()
        bundle = parse_config_bundle(config_path, cwd, user_config)
        if requested_mode == "workspace":
            if len(bundle.projects) > 1:
                return bundle
            current_project = select_current_project(bundle.projects, cwd)
            discovered = discover_workspace_projects(current_project, args.discover_root)
            return WorkspaceConfig(
                default_author=user_config.default_author or bundle.default_author,
                default_language=user_config.default_language or bundle.default_language,
                default_mode=requested_mode,
                builtin_ignore_globs=bundle.builtin_ignore_globs,
                projects=discovered,
            )
        current_project = select_current_project(bundle.projects, cwd)
        return WorkspaceConfig(
            default_author=user_config.default_author or bundle.default_author,
            default_language=user_config.default_language or bundle.default_language,
            default_mode=requested_mode,
            builtin_ignore_globs=bundle.builtin_ignore_globs,
            projects=[current_project],
        )

    repo_root = safe_git_repo_root(cwd)
    if repo_root is None:
        raise RuntimeError("Unable to resolve git repo root from cwd.")

    current_project = load_project_config_from_repo_root(repo_root)
    projects = [current_project]
    if requested_mode == "workspace":
        projects = discover_workspace_projects(current_project, args.discover_root)

    return WorkspaceConfig(
        default_author=user_config.default_author,
        default_language=user_config.default_language,
        default_mode=requested_mode,
        builtin_ignore_globs=list(DEFAULT_BUILTIN_IGNORE_GLOBS),
        projects=projects,
    )


def parse_config_bundle(config_path: Path, cwd: Path, user_config: UserConfig) -> WorkspaceConfig:
    if not config_path.exists():
        raise RuntimeError(f"Config file does not exist: {config_path}")

    data = json.loads(config_path.read_text(encoding="utf-8"))
    if "projects" in data:
        return parse_legacy_workspace_config(data, user_config)

    repo_root = safe_git_repo_root(cwd) or config_path.parent
    project = parse_project_file(data, repo_root)
    return WorkspaceConfig(
        default_author=user_config.default_author,
        default_language=user_config.default_language,
        default_mode=user_config.default_mode,
        builtin_ignore_globs=list(DEFAULT_BUILTIN_IGNORE_GLOBS),
        projects=[project],
    )


def parse_legacy_workspace_config(data: dict, user_config: UserConfig) -> WorkspaceConfig:
    projects: list[ProjectConfig] = []
    for project_data in data.get("projects", []):
        module_rules = [
            ModuleRule(module=item["module"], paths=item.get("paths", []))
            for item in project_data.get("module_rules", [])
        ]
        projects.append(
            ProjectConfig(
                id=project_data["id"],
                display_name=project_data.get("display_name", project_data["id"]),
                repo_root=Path(project_data["repo_root"]),
                report_title=project_data.get("report_title", f'{project_data["id"]} 开发'),
                ignore_globs=project_data.get("ignore_globs", []),
                module_rules=module_rules,
            )
        )

    return WorkspaceConfig(
        default_author=user_config.default_author or data.get("default_author", ""),
        default_language=user_config.default_language or data.get("default_language", "zh-CN"),
        default_mode=user_config.default_mode or data.get("default_mode", "current-project"),
        builtin_ignore_globs=data.get("builtin_ignore_globs", list(DEFAULT_BUILTIN_IGNORE_GLOBS)),
        projects=projects,
    )


def load_project_config_from_repo_root(repo_root: Path) -> ProjectConfig:
    config_path = repo_root / PROJECT_CONFIG_NAME
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return parse_project_file(data, repo_root)
    return build_fallback_project(repo_root)


def parse_project_file(data: dict, repo_root: Path) -> ProjectConfig:
    project_meta = data.get("project", {})
    capability_meta = data.get("capabilities", {}).get("workspace-daily-report", {})
    module_rules = [
        ModuleRule(module=item["module"], paths=item.get("paths", []))
        for item in capability_meta.get("module_rules", [])
    ]

    project_id = project_meta.get("id", repo_root.name)
    display_name = (
        project_meta.get("name")
        or project_meta.get("display_name")
        or project_meta.get("title")
        or project_id
    )
    report_title = capability_meta.get("report_title", f"{display_name} 开发")

    return ProjectConfig(
        id=project_id,
        display_name=display_name,
        repo_root=repo_root,
        report_title=report_title,
        ignore_globs=capability_meta.get("ignore_globs", []),
        module_rules=module_rules,
    )


def discover_workspace_projects(current_project: ProjectConfig, discover_root_arg: str | None) -> list[ProjectConfig]:
    discover_root = Path(discover_root_arg).resolve() if discover_root_arg else current_project.repo_root.parent
    projects_by_root: dict[Path, ProjectConfig] = {current_project.repo_root.resolve(): current_project}

    candidates: list[Path] = []
    if discover_root.exists():
        candidates.append(discover_root)
        candidates.extend(child for child in discover_root.iterdir() if child.is_dir())

    for candidate in candidates:
        config_path = candidate / PROJECT_CONFIG_NAME
        if not config_path.exists():
            continue

        repo_root = safe_git_repo_root(candidate)
        if repo_root is None or repo_root.resolve() != candidate.resolve():
            continue

        projects_by_root.setdefault(repo_root.resolve(), load_project_config_from_repo_root(repo_root))

    return sorted(projects_by_root.values(), key=lambda item: item.display_name.lower())


def select_current_project(projects: list[ProjectConfig], cwd: Path) -> ProjectConfig:
    if not projects:
        raise RuntimeError("No project configuration was resolved.")

    matched = [project for project in projects if is_subpath(cwd, project.repo_root)]
    if matched:
        return matched[0]

    repo_root = safe_git_repo_root(cwd)
    if repo_root is not None:
        for project in projects:
            if project.repo_root.resolve() == repo_root.resolve():
                return project

    return projects[0]


def safe_git_repo_root(path: Path) -> Path | None:
    try:
        completed = run_git(path, ["rev-parse", "--show-toplevel"])
        text = completed.stdout.strip()
        return Path(text) if text else None
    except RuntimeError:
        return None


def run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    command = ["C:\\Program Files\\Git\\cmd\\git.exe", *args]
    completed = subprocess.run(
        command,
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"git command failed: {' '.join(args)}")
    return completed


def build_fallback_project(repo_root: Path) -> ProjectConfig:
    return ProjectConfig(
        id=repo_root.name,
        display_name=repo_root.name,
        repo_root=repo_root,
        report_title=f"{repo_root.name} 开发",
        ignore_globs=[],
        module_rules=[],
    )


def is_subpath(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def determine_window(args: argparse.Namespace) -> tuple[datetime, datetime]:
    now = datetime.now()
    since = parse_datetime(args.since) if args.since else (now - timedelta(days=DEFAULT_LOOKBACK_DAYS))
    until = parse_datetime(args.until) if args.until else now + timedelta(seconds=1)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.until or ""):
        until = until + timedelta(days=1)

    if since >= until:
        raise RuntimeError("--since must be earlier than --until.")

    return since, until


def collect_project_data(project: ProjectConfig, builtin_ignore_globs: list[str], since: datetime, until: datetime) -> tuple[list[FileChange], list[CommitFact]]:
    file_changes: list[FileChange] = []
    commit_facts: list[CommitFact] = []

    if not project.repo_root.exists():
        return file_changes, commit_facts

    for subject, commit_id, committed_at, changed_paths in collect_commit_subjects(project, since, until):
        touched_modules = sorted(
            {
                classify_module(project, path)
                for path in changed_paths
                if not should_ignore(path, builtin_ignore_globs, project.ignore_globs)
            }
        )
        if not touched_modules:
            touched_modules = [project.report_title]

        for module in touched_modules[:MAX_COMMIT_SUBJECTS_PER_MODULE]:
            commit_facts.append(
                CommitFact(
                    project_id=project.id,
                    project_name=project.display_name,
                    report_title=project.report_title,
                    module=module,
                    subject=subject,
                    commit_id=commit_id,
                    committed_at=committed_at,
                )
            )

    for path, status in collect_working_tree_changes(project):
        if should_ignore(path, builtin_ignore_globs, project.ignore_globs):
            continue

        abs_path = project.repo_root / path if status != "D" else None
        changed_at = get_changed_at(abs_path)
        if status != "D" and changed_at is not None and not (since <= changed_at < until):
            continue

        module = classify_module(project, path)
        diff_excerpt = collect_diff_excerpt(project, path, status)
        tags = infer_tags(path, diff_excerpt)
        file_changes.append(
            FileChange(
                project_id=project.id,
                project_name=project.display_name,
                report_title=project.report_title,
                module=module,
                path=path,
                abs_path=abs_path,
                status=status,
                source="working-tree",
                changed_at=changed_at,
                diff_excerpt=diff_excerpt,
                tags=tags,
            )
        )

    return file_changes, commit_facts


def collect_commit_subjects(project: ProjectConfig, since: datetime, until: datetime) -> list[tuple[str, str, datetime, list[str]]]:
    try:
        completed = run_git(
            project.repo_root,
            [
                "log",
                f"--since={since.isoformat(sep=' ')}",
                f"--until={until.isoformat(sep=' ')}",
                "--date=iso",
                "--name-status",
                "--format=__COMMIT__%H|%ad|%s",
            ],
        )
    except RuntimeError:
        return []

    items: list[tuple[str, str, datetime, list[str]]] = []
    current_subject = ""
    current_id = ""
    current_time = since
    current_paths: list[str] = []

    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("__COMMIT__"):
            if current_id:
                items.append((current_subject, current_id, current_time, current_paths))
            payload = line[len("__COMMIT__") :]
            parts = payload.split("|", 2)
            if len(parts) != 3:
                current_subject = payload
                current_id = ""
                current_paths = []
                current_time = since
                continue
            current_id = parts[0]
            current_time = parse_git_datetime(parts[1])
            current_subject = parts[2].strip()
            current_paths = []
            continue

        if "\t" in line:
            segments = line.split("\t")
            path = segments[-1].strip()
            if path:
                current_paths.append(path.replace("\\", "/"))

    if current_id:
        items.append((current_subject, current_id, current_time, current_paths))

    return items


def parse_git_datetime(value: str) -> datetime:
    cleaned = value.strip()
    cleaned = re.sub(r" ([+-]\d{4})$", "", cleaned)
    return datetime.fromisoformat(cleaned.replace(" ", "T"))


def collect_working_tree_changes(project: ProjectConfig) -> list[tuple[str, str]]:
    changes: dict[str, str] = {}

    for command in (
        ["diff", "--name-status", "--find-renames", "HEAD", "--"],
        ["diff", "--cached", "--name-status", "--find-renames", "--"],
    ):
        try:
            completed = run_git(project.repo_root, command)
        except RuntimeError:
            continue

        for line in completed.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0].strip()
            path = parts[-1].strip().replace("\\", "/")
            if path:
                changes[path] = normalize_status(status)

    try:
        untracked = run_git(project.repo_root, ["ls-files", "--others", "--exclude-standard"])
        for line in untracked.stdout.splitlines():
            path = line.strip().replace("\\", "/")
            if path:
                changes[path] = "A"
    except RuntimeError:
        pass

    return sorted(changes.items())


def normalize_status(status: str) -> str:
    if not status:
        return "M"
    leading = status[0]
    if leading in {"A", "M", "D", "R", "C"}:
        return leading
    return "M"


def get_changed_at(path: Path | None) -> datetime | None:
    if path is None or not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime)


def should_ignore(path: str, builtin_ignore_globs: list[str], project_ignore_globs: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    globs = [*builtin_ignore_globs, *project_ignore_globs]
    return any(fnmatch(normalized, pattern) for pattern in globs)


def classify_module(project: ProjectConfig, path: str) -> str:
    normalized = path.replace("\\", "/")
    for rule in project.module_rules:
        for prefix in rule.paths:
            normalized_prefix = prefix.replace("\\", "/")
            if "*" in normalized_prefix:
                if fnmatch(normalized, normalized_prefix):
                    return rule.module
            elif normalized.startswith(normalized_prefix.rstrip("/") + "/") or normalized == normalized_prefix.rstrip("/"):
                return rule.module
    return "其他改动"


def collect_diff_excerpt(project: ProjectConfig, path: str, status: str) -> str:
    if status == "A":
        abs_path = project.repo_root / path
        if abs_path.exists() and abs_path.suffix.lower() in {".cs", ".md", ".json", ".sbdef", ".asmdef", ".yaml", ".yml"}:
            try:
                return "\n".join(abs_path.read_text(encoding="utf-8", errors="replace").splitlines()[:MAX_DIFF_LINES])
            except OSError:
                return ""

    for command in (
        ["diff", "--unified=0", "HEAD", "--", path],
        ["diff", "--cached", "--unified=0", "--", path],
    ):
        try:
            completed = run_git(project.repo_root, command)
        except RuntimeError:
            continue
        if completed.stdout:
            return "\n".join(completed.stdout.splitlines()[:MAX_DIFF_LINES])
    return ""


def infer_tags(path: str, excerpt: str) -> set[str]:
    tags: set[str] = set()
    lower_path = path.lower()
    lower_excerpt = excerpt.lower()

    if "/tests/" in lower_path or "[test]" in lower_excerpt:
        tags.add("tests")
    if lower_path.endswith(".md") or "/documentation" in lower_path or "/documentations~/" in lower_path:
        tags.add("docs")
    if "/generated/" in lower_path or "/definitions/" in lower_path or lower_path.endswith(".sbdef") or lower_path.endswith(".asmdef"):
        tags.add("definition_chain")
    if "nodestatedescriptor" in lower_excerpt or "nodeprivateexecutionstatesupport" in lower_excerpt:
        tags.add("state_migration")
    if "snapshotexporter" in lower_excerpt or "snapshotreplayer" in lower_excerpt or "runtimesnapshot" in lower_excerpt:
        tags.add("snapshot")
    if "reactivestatedomain" in lower_excerpt or "schedulingstatedomain" in lower_excerpt or "reactivewait" in lower_excerpt:
        tags.add("reactive_scheduling")
    if "inflighttask" in lower_excerpt or "onspawnbatchcomplete" in lower_excerpt or "entityregistry" in lower_excerpt:
        tags.add("async_chain")
    if "requirefullyinside" in lower_excerpt or "containspointxz" in lower_excerpt or "collider" in lower_excerpt:
        tags.add("area_logic")
    if "watchcondition" in lower_excerpt and "repeat" in lower_excerpt:
        tags.add("watch_repeat")
    if "compositecondition" in lower_excerpt:
        tags.add("composite_condition")
    if "blackboard.get" in lower_excerpt or "blackboardset" in lower_excerpt or "blackboard.set" in lower_excerpt or "blackboardget" in lower_excerpt:
        tags.add("blackboard")
    if "flow.join" in lower_excerpt or "joinstate" in lower_excerpt or "tryaccumulatejoinarrival" in lower_excerpt:
        tags.add("flow_join")
    if "flow.branch" in lower_excerpt or "flow.start" in lower_excerpt or "flow.end" in lower_excerpt or "flow.filter" in lower_excerpt:
        tags.add("flow_lightweight")
    if "spawnpreset" in lower_excerpt or "spawn.preset" in lower_excerpt:
        tags.add("spawn_preset")
    if "spawnwave" in lower_excerpt or "spawn.wave" in lower_excerpt:
        tags.add("spawn_wave")
    if "triggerenterarea" in lower_excerpt or "trigger.enterarea" in lower_excerpt or "trigger.enter-area" in lower_excerpt:
        tags.add("trigger_enter_area")
    if "showwarning" in lower_excerpt or "camerashake" in lower_excerpt or "screenflash" in lower_excerpt or "vfx" in lower_excerpt:
        tags.add("vfx")

    return tags


def build_report_payload(
    author: str,
    since: datetime,
    until: datetime,
    file_changes: list[FileChange],
    commit_facts: list[CommitFact],
) -> dict:
    projects: dict[str, dict] = {}

    for change in file_changes:
        project_bucket = projects.setdefault(
            change.project_id,
            {
                "project_name": change.project_name,
                "report_title": change.report_title,
                "modules": {},
            },
        )
        module_bucket = project_bucket["modules"].setdefault(
            change.module,
            {"changes": [], "commit_subjects": []},
        )
        module_bucket["changes"].append(change)

    for fact in commit_facts:
        project_bucket = projects.setdefault(
            fact.project_id,
            {
                "project_name": fact.project_name,
                "report_title": fact.report_title,
                "modules": {},
            },
        )
        module_bucket = project_bucket["modules"].setdefault(
            fact.module,
            {"changes": [], "commit_subjects": []},
        )
        module_bucket["commit_subjects"].append(fact.subject)

    ordered_projects = []
    for project_id, project_bucket in projects.items():
        modules = []
        for module_name, module_bucket in project_bucket["modules"].items():
            modules.append(
                {
                    "module": module_name,
                    "facts": build_module_facts(module_name, module_bucket["changes"], module_bucket["commit_subjects"]),
                    "file_count": len(module_bucket["changes"]),
                    "commit_subjects": dedupe_preserve(module_bucket["commit_subjects"])[:MAX_COMMIT_SUBJECTS_PER_MODULE],
                    "files": sorted({change.path for change in module_bucket["changes"]}),
                }
            )
        modules.sort(key=lambda item: item["module"])
        ordered_projects.append(
            {
                "project_id": project_id,
                "project_name": project_bucket["project_name"],
                "report_title": project_bucket["report_title"],
                "modules": modules,
            }
        )

    ordered_projects.sort(key=lambda item: item["project_name"])

    return {
        "author": author,
        "window": {
            "since": since.isoformat(sep=" "),
            "until": until.isoformat(sep=" "),
        },
        "projects": ordered_projects,
    }


def build_module_facts(module_name: str, changes: list[FileChange], commit_subjects: list[str]) -> list[str]:
    tags = {tag for change in changes for tag in change.tags}
    file_names = [Path(change.path).stem for change in changes]
    unique_files = dedupe_preserve(file_names)
    facts: list[str] = []

    if "文档" in module_name:
        doc_names = [Path(change.path).stem for change in changes if "docs" in change.tags]
        sample = "、".join(dedupe_preserve(doc_names)[:3])
        if sample:
            facts.append(f"整理并更新 {sample} 等文档，收敛当前实现口径")
        else:
            facts.append("整理并更新相关设计文档，收敛当前实现口径")
        for subject in dedupe_preserve(commit_subjects)[:MAX_COMMIT_SUBJECTS_PER_MODULE]:
            facts.append(f"提交记录：{subject}")
        return facts[:MAX_GROUP_FACTS]

    if "测试" in module_name:
        test_targets = []
        if "flow_join" in tags:
            test_targets.append("Flow.Join")
        if "spawn_wave" in tags:
            test_targets.append("Spawn.Wave")
        if "watch_repeat" in tags:
            test_targets.append("WatchCondition Repeat")
        if "reactive_scheduling" in tags:
            test_targets.append("Reactive / Scheduling")
        if "trigger_enter_area" in tags:
            test_targets.append("Trigger.EnterArea")
        if "spawn_preset" in tags:
            test_targets.append("Spawn.Preset")
        label = "、".join(dedupe_preserve(test_targets)) if test_targets else "相关功能"
        facts.append(f"补充 {label} 的回归测试，提升状态迁移后的稳定性")
        for subject in dedupe_preserve(commit_subjects)[:MAX_COMMIT_SUBJECTS_PER_MODULE]:
            facts.append(f"提交记录：{subject}")
        return facts[:MAX_GROUP_FACTS]

    if "编辑器" in module_name or "配置" in module_name:
        if "watch_repeat" in tags:
            facts.append("补回 WatchCondition Repeat 的定义、codegen 和配置链路")
        if "definition_chain" in tags and not facts:
            facts.append("更新定义、生成代码和编辑器配置链路，保持运行时与配置侧一致")
        for subject in dedupe_preserve(commit_subjects)[:MAX_COMMIT_SUBJECTS_PER_MODULE]:
            facts.append(f"提交记录：{subject}")
        if facts:
            return facts[:MAX_GROUP_FACTS]

    if "state_migration" in tags:
        segments: list[str] = []
        if "composite_condition" in tags:
            segments.append("CompositeCondition")
        if "blackboard" in tags:
            segments.append("Blackboard Get / Set")
        if "flow_lightweight" in tags or "flow_join" in tags:
            segments.append("Flow 轻量节点")
        if "watch_repeat" in tags or "reactive_scheduling" in tags:
            segments.append("WaitSignal / WatchCondition")
        if "spawn_preset" in tags:
            segments.append("Spawn.Preset")
        if "trigger_enter_area" in tags:
            segments.append("Trigger.EnterArea")
        if "vfx" in tags:
            segments.append("VFX 节点")
        label = "、".join(dedupe_preserve(segments)) if segments else "多个运行时节点"
        facts.append(f"完成 {label} 的状态迁移，统一接入 NodePrivateStateDomain")

    if "reactive_scheduling" in tags:
        facts.append("补齐 Reactive / Scheduling 相关监听、超时、释放链路")

    if "watch_repeat" in tags or ("definition_chain" in tags and any("watchcondition" in change.diff_excerpt.lower() for change in changes)):
        facts.append("补回 WatchCondition Repeat 的定义、codegen 和配置链路")

    if "async_chain" in tags:
        if "spawn_preset" in tags:
            facts.append("完善 Spawn.Preset 异步创建、主线程收口、实体注册与批次完成通知流程")
        elif "spawn_wave" in tags:
            facts.append("加固 Spawn.Wave 异步批次完成与实体注册链路")
        else:
            facts.append("加固异步执行与主线程收口链路")

    if "area_logic" in tags and "trigger_enter_area" in tags:
        facts.append("补齐 Trigger.EnterArea 的 RequireFullyInside 与多 Collider 完整进入判定")

    if "snapshot" in tags:
        snapshot_targets = []
        if "spawn_preset" in tags:
            snapshot_targets.append("Spawn.Preset")
        if "trigger_enter_area" in tags:
            snapshot_targets.append("Trigger.EnterArea")
        if "spawn_wave" in tags:
            snapshot_targets.append("Spawn.Wave")
        label = "、".join(dedupe_preserve(snapshot_targets)) if snapshot_targets else "相关节点"
        facts.append(f"为 {label} 补齐 Snapshot / Replay 导出与恢复能力")

    if "tests" in tags:
        test_targets = []
        if "flow_join" in tags:
            test_targets.append("Flow.Join")
        if "spawn_wave" in tags:
            test_targets.append("Spawn.Wave")
        if "watch_repeat" in tags:
            test_targets.append("WatchCondition Repeat")
        if "reactive_scheduling" in tags:
            test_targets.append("Reactive / Scheduling")
        label = "、".join(dedupe_preserve(test_targets)) if test_targets else "相关功能"
        facts.append(f"补充 {label} 的回归测试，提升状态迁移后的稳定性")

    if "docs" in tags:
        doc_names = [Path(change.path).stem for change in changes if "docs" in change.tags]
        sample = "、".join(dedupe_preserve(doc_names)[:3])
        if sample:
            facts.append(f"整理并更新 {sample} 等文档，收敛当前实现口径")
        else:
            facts.append("整理并更新相关设计文档，收敛当前实现口径")

    if "definition_chain" in tags and not any("Repeat" in fact or "codegen" in fact for fact in facts):
        facts.append("更新定义、生成代码和编辑器配置链路，保持运行时与配置侧一致")

    for subject in dedupe_preserve(commit_subjects)[:MAX_COMMIT_SUBJECTS_PER_MODULE]:
        normalized = subject.strip()
        if normalized and normalized not in facts:
            facts.append(f"提交记录：{normalized}")

    if not facts:
        if unique_files:
            sample = "、".join(unique_files[:3])
            facts.append(f"更新 {sample} 等文件，推进该模块实现")
        else:
            facts.append("推进该模块实现并整理相关改动")

    return facts[:MAX_GROUP_FACTS]


def dedupe_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def render_markdown(payload: dict, detail: str) -> str:
    author = payload["author"]
    projects = payload["projects"]

    blocks: list[str] = []
    if detail in {"detailed", "both"}:
        lines = [author, "", "详细日报", "昨日完成"]
        for project in projects:
            title = project["report_title"] or project["project_name"]
            lines.append(title)
            for module in project["modules"]:
                lines.append(f"- {module['module']}")
                for fact in module["facts"]:
                    lines.append(f"  - {fact}")
        blocks.append("\n".join(lines).strip())

    if detail in {"brief", "both"}:
        lines = [author, "", "简要日报", "昨日完成"]
        for project in projects:
            title = project["report_title"] or project["project_name"]
            lines.append(f"- {title}")
            compact_facts: list[str] = []
            for module in project["modules"]:
                compact_facts.extend(module["facts"])
            for fact in compact_facts[:4]:
                lines.append(f"  - {fact}")
        blocks.append("\n".join(lines).strip())

    return "\n\n".join(blocks).strip()


def main() -> int:
    args = parse_args()
    cwd = Path(args.cwd or os.getcwd()).resolve()
    user_config = load_user_config(args)
    requested_mode = args.mode or user_config.default_mode or "current-project"

    try:
        config = load_workspace_config(args, cwd, requested_mode, user_config)
        since, until = determine_window(args)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    author = args.author or config.default_author or ""
    all_file_changes: list[FileChange] = []
    all_commit_facts: list[CommitFact] = []

    for project in config.projects:
        file_changes, commit_facts = collect_project_data(project, config.builtin_ignore_globs, since, until)
        all_file_changes.extend(file_changes)
        all_commit_facts.extend(commit_facts)

    payload = build_report_payload(author, since, until, all_file_changes, all_commit_facts)
    payload["mode"] = requested_mode
    payload["project_count"] = len(config.projects)

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(render_markdown(payload, args.detail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

