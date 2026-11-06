#!/usr/bin/env python3
"""Generate viewer/poses_index.json from poses/*.json without touching poses/.

Run from the repository root:
    python3 viewer/tools/build_index.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSES_DIR = ROOT / "poses"
OUT_PATH = ROOT / "viewer" / "poses_index.json"


def build_index() -> dict:
    entries = []
    for path in sorted(POSES_DIR.glob("*.json")):
        if path.name == "schema.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "meta" not in data or "bones" not in data:
            continue
        meta = data.get("meta", {})
        pose_id = meta.get("id") or path.stem
        source_image = meta.get("sourceImage")
        entries.append(
            {
                "id": pose_id,
                "name": meta.get("name", pose_id),
                "description": meta.get("description", ""),
                "file": f"poses/{path.name}",
                "targetModels": meta.get("targetModels", ["female", "male"]),
                "sourceImage": source_image.get("path") if isinstance(source_image, dict) else None,
            }
        )
    return {
        "formatVersion": 1,
        "skeleton": "pose-library-humanoid-v1",
        "poses": entries,
    }


def main() -> None:
    index_data = build_index()
    OUT_PATH.write_text(json.dumps(index_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} ({len(index_data['poses'])} pose(s))")


if __name__ == "__main__":
    main()
