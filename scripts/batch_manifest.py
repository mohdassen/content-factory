from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"


def discover() -> list[dict]:
    jobs = []
    for folder in sorted(CONTENT.iterdir()):
        if not folder.is_dir() or not folder.name[:3].isdigit():
            continue
        script = folder / "script_ar.txt"
        if not script.exists():
            continue
        jobs.append({
            "id": folder.name[:3],
            "slug": folder.name,
            "script": str(script.relative_to(ROOT)),
            "storyboard": str((folder / "storyboard.json").relative_to(ROOT)) if (folder / "storyboard.json").exists() else None,
            "visual_plan": str((folder / "visual_plan.json").relative_to(ROOT)) if (folder / "visual_plan.json").exists() else None,
            "research": str((folder / "research.md").relative_to(ROOT)) if (folder / "research.md").exists() else None,
            "ready_for_voice": True,
            "ready_for_visual_render": (folder / "storyboard.json").exists() and (folder / "visual_plan.json").exists(),
        })
    return jobs


if __name__ == "__main__":
    output = {"count": 0, "jobs": discover()}
    output["count"] = len(output["jobs"])
    out = ROOT / "output" / "batch-manifest.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {output['count']} content jobs -> {out}")
