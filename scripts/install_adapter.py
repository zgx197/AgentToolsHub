from __future__ import annotations

import argparse

from adapter_common import install_tree, print_paths, resolve_install_target, resolve_repo_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install a capability adapter from AgentToolsHub into a local agent skills directory."
    )
    parser.add_argument("capability", help="Capability id, e.g. workspace-daily-report")
    parser.add_argument("platform", choices=("codex", "claude"), help="Target agent platform")
    parser.add_argument("--target-root", help="Override install root directory")
    parser.add_argument("--force", action="store_true", help="Overwrite the existing installed adapter")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved source and target without copying")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root()
    _, source, target = resolve_install_target(repo_root, args.capability, args.platform, args.target_root)

    print_paths(source, target)
    if args.dry_run:
        return 0

    install_tree(source, target, force=args.force)
    print("Install complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
