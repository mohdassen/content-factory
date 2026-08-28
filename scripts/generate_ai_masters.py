#!/usr/bin/env python3
import argparse, base64, json, os, pathlib, time, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]


def find_story(content_id: str):
    matches = sorted((ROOT / "content").glob(f"{content_id}-*"))
    if not matches:
        raise SystemExit(f"Unknown content id: {content_id}")
    return matches[0]


def api_post(url, payload, api_key):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"OpenAI image API HTTP {e.code}: {body}") from e


def download(url):
    with urllib.request.urlopen(url, timeout=180) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    args = ap.parse_args()

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise SystemExit("OPENAI_API_KEY secret is required to generate strict AI masters")

    story = find_story(args.id)
    slug = story.name
    storyboard = json.loads((story / "storyboard.json").read_text(encoding="utf-8"))
    visual_plan = json.loads((story / "visual_plan.json").read_text(encoding="utf-8"))
    scenes = storyboard.get("scenes", [])
    shots = visual_plan.get("shots", [])
    if len(scenes) < 6 or len(shots) < 6:
        raise SystemExit("Need at least 6 storyboard scenes and visual prompts")

    out = ROOT / "assets" / "stories" / slug / "scenes"
    out.mkdir(parents=True, exist_ok=True)

    model = os.getenv("IMAGE_MODEL", "gpt-image-1")
    size = os.getenv("IMAGE_SIZE", "1024x1536")
    quality = os.getenv("IMAGE_QUALITY", "high")
    force = os.getenv("FORCE_REGENERATE_MASTERS", "false").lower() == "true"

    base_style = visual_plan.get("style", "premium cinematic documentary")
    for i, (scene, shot) in enumerate(zip(scenes, shots), start=1):
        dest = out / f"{i:02d}.png"
        if dest.exists() and not force:
            print(f"KEEP {dest}")
            continue
        caption = str(scene.get("caption", "")).strip()
        visual = str(shot.get("prompt") or scene.get("visual") or "").strip()
        prompt = (
            f"Create ONE independent vertical cinematic master image for an Arabic social-media documentary. "
            f"Story: {slug}. Scene {i}. Visual: {visual}. Style: {base_style}. "
            f"Portrait composition, premium HDR lighting, documentary realism, strong focal subject, safe margins, "
            f"no collage, no grid, no storyboard, no subtitle box, no watermark. "
            f"Integrate only this short on-image caption as tasteful designed Arabic typography if non-empty: «{caption}». "
            f"Keep brand names in their normal Latin spelling when naturally visible."
        )
        payload = {"model": model, "prompt": prompt, "size": size, "quality": quality, "n": 1}
        print(f"GENERATE {slug} scene {i}/{min(len(scenes), len(shots))}")
        result = api_post("https://api.openai.com/v1/images/generations", payload, key)
        item = result["data"][0]
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            raw = download(item["url"])
        else:
            raise RuntimeError(f"No image bytes returned for scene {i}: {item.keys()}")
        dest.write_bytes(raw)
        time.sleep(1)

    manifest = {
        "architecture": "V3_GOLDEN_STRICT",
        "story": slug,
        "source": "independent_ai_generation",
        "model": model,
        "scene_count": len(list(out.glob("*.png"))),
        "storyboard_as_source": False,
        "stock_fallback": False,
    }
    (out.parent / "masters-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))

if __name__ == "__main__":
    main()
