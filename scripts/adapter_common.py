from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


DEFAULT_TARGETS = {
    "codex": Path.home() / ".codex" / "skills",
}

ENV_TARGETS = {
    "claude": "CLAUDE_CODE_SKILLS_DIR",
}


def resolve_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_manifest(repo_root: Path, capability: str) -> dict:
    manifest_path = repo_root / "capabilities" / capability / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Capability manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def resolve_source(repo_root: Path, manifest: dict, platform: str) -> Path:
    entrypoints = manifest.get("entrypoints", {})
    relative = entrypoints.get(platform)
    if not relative:
        raise ValueError(f"Capability does not expose a {platform} adapter")

    source = repo_root / relative
    if not source.exists():
        raise FileNotFoundError(f"Adapter source not found: {source}")
    if not source.is_dir():
        raise ValueError(f"Adapter source is not a directory and cannot be installed: {source}")
    return source


def resolve_target_root(platform: str, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()

    if platform in DEFAULT_TARGETS:
        return DEFAULT_TARGETS[platform]

    env_name = ENV_TARGETS.get(platform)
    if env_name and os.environ.get(env_name):
        return Path(os.environ[env_name]).expanduser().resolve()

    raise ValueError(
        f"No default install root for {platform}. "
        "Pass --target-root or set the expected environment variable."
    )


def resolve_install_target(repo_root: Path, capability: str, platform: str, target_root_override: str | None) -> tuple[dict, Path, Path]:
    manifest = load_manifest(repo_root, capability)
    source = resolve_source(repo_root, manifest, platform)
    target_root = resolve_target_root(platform, target_root_override)
    target = target_root / source.name
    return manifest, source, target


def print_paths(source: Path, target: Path) -> None:
    print(f"Source: {source}")
    print(f"Target: {target}")


def install_tree(source: Path, target: Path, force: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not force:
            raise FileExistsError(f"Target already exists: {target}. Use --force to overwrite.")
        shutil.rmtree(target)

    shutil.copytree(source, target)


def uninstall_tree(target: Path, missing_ok: bool) -> bool:
    if not target.exists():
        if missing_ok:
            return False
        raise FileNotFoundError(f"Target does not exist: {target}")

    shutil.rmtree(target)
    return True
