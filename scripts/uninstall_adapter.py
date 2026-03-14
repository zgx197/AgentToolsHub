from __future__ import annotations

import argparse

from adapter_common import print_paths, resolve_install_target, resolve_repo_root, uninstall_tree


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove an installed capability adapter from a local agent skills directory."
    )
    parser.add_argument("capability", help="Capability id, e.g. workspace-daily-report")
    parser.add_argument("platform", choices=("codex", "claude"), help="Target agent platform")
    parser.add_argument("--target-root", help="Override install root directory")
    parser.add_argument("--missing-ok", action="store_true", help="Exit successfully if the target is not installed")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved source and target without deleting")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root()
    _, source, target = resolve_install_target(repo_root, args.capability, args.platform, args.target_root)

    print_paths(source, target)
    if args.dry_run:
        return 0

    removed = uninstall_tree(target, missing_ok=args.missing_ok)
    if removed:
        print("Uninstall complete.")
    else:
        print("Target not installed; nothing to remove.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
