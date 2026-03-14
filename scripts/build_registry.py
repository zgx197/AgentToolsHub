from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES_DIR = REPO_ROOT / "capabilities"
MCP_DIR = REPO_ROOT / "mcp-servers"
OUTPUT_PATH = REPO_ROOT / "registry" / "generated" / "index.json"


def collect_manifests(base_dir: Path) -> list[dict]:
    if not base_dir.exists():
        return []

    items: list[dict] = []
    for manifest_path in sorted(base_dir.rglob("manifest.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["_manifest_path"] = str(manifest_path.relative_to(REPO_ROOT)).replace("\\", "/")
        items.append(data)
    return items


def main() -> int:
    capabilities = collect_manifests(CAPABILITIES_DIR)
    mcps = collect_manifests(MCP_DIR)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "capability_count": len(capabilities),
        "mcp_count": len(mcps),
        "capabilities": capabilities,
        "mcps": mcps,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Registry written: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
