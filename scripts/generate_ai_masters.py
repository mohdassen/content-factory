#!/usr/bin/env python3
import argparse, base64, json, os, pathlib, re, time, urllib.request, urllib.error

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


def read_optional_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def clean_paragraphs(text):
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def build_scene_inputs(story):
    """Prefer explicit storyboard/visual plan, but never require them.

    The repository's original content pack only guarantees script_ar.txt and research.md.
    Strict V3 therefore derives independent visual scenes from narration when richer planning
    files are not present.
    """
    storyboard = read_optional_json(story / "storyboard.json") or {}
    visual_plan = read_optional_json(story / "visual_plan.json") or {}
    scenes = storyboard.get("scenes") or []
    shots = visual_plan.get("shots") or []

    if scenes and shots:
        count = min(len(scenes), len(shots))
        return [
            {
                "narration": str(scenes[i].get("caption") or scenes[i].get("narration") or "").strip(),
                "visual": str(shots[i].get("prompt") or scenes[i].get("visual") or "").strip(),
            }
            for i in range(count)
        ], visual_plan.get("style", "premium cinematic documentary realism")

    script_path = story / "script_ar.txt"
    if not script_path.exists():
        raise SystemExit(f"Missing required narration source: {script_path}")

    paragraphs = clean_paragraphs(script_path.read_text(encoding="utf-8"))
    if len(paragraphs) < 6:
        raise SystemExit("Need at least 6 narration paragraphs to derive V3 scenes")

    # One independently generated master per narration paragraph. The Arabic narration is
    # context only; the prompt explicitly forbids rendering any text inside the image.
    derived = [
        {
            "narration": p,
            "visual": (
                "Create a literal but cinematic visual interpretation of this narration idea, "
                "using recognizable real-world objects, environments, people, product context, "
                "and emotional storytelling rather than abstract graphics."
            ),
        }
        for p in paragraphs
    ]
    return derived, "premium cinematic technology documentary, photorealistic, editorial, dramatic but credible"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    args = ap.parse_args()

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise SystemExit("OPENAI_API_KEY secret is required to generate strict AI masters")

    story = find_story(args.id)
    slug = story.name
    scene_inputs, base_style = build_scene_inputs(story)
    if len(scene_inputs) < 6:
        raise SystemExit("Need at least 6 independent V3 scene inputs")

    out = ROOT / "assets" / "stories" / slug / "scenes"
    out.mkdir(parents=True, exist_ok=True)

    model = os.getenv("IMAGE_MODEL", "gpt-image-1")
    size = os.getenv("IMAGE_SIZE", "1024x1536")
    quality = os.getenv("IMAGE_QUALITY", "high")
    force = os.getenv("FORCE_REGENERATE_MASTERS", "false").lower() == "true"

    for i, scene in enumerate(scene_inputs, start=1):
        dest = out / f"{i:02d}.png"
        if dest.exists() and not force:
            print(f"KEEP {dest}")
            continue

        narration = scene["narration"]
        visual = scene["visual"]
        prompt = (
            f"Create ONE independent vertical cinematic master image for an Arabic short-form technology documentary. "
            f"Story: {slug}. Scene {i}. Narration meaning/context: {narration}. Visual direction: {visual}. "
            f"Style: {base_style}. Compose specifically for a final 9:16 frame with the important subject centered inside "
            f"a narrow portrait-safe area so conversion to 1080x1920 requires no stretching and only minimal edge crop. "
            f"Premium HDR lighting, documentary realism, depth, foreground/background separation, natural textures, "
            f"strong focal subject, visually distinct from the other scenes. "
            f"ABSOLUTELY NO visible text, letters, numbers, captions, subtitles, UI labels, timestamps, logos added as graphics, "
            f"watermarks, collage, grid, storyboard panels, presentation slides, or decorative typography. "
            f"Any unavoidable product branding should be subtle and naturally part of a photographed physical object only."
        )
        payload = {"model": model, "prompt": prompt, "size": size, "quality": quality, "n": 1}
        print(f"GENERATE {slug} scene {i}/{len(scene_inputs)}")
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
        "image_text_allowed": False,
        "target_frame": "1080x1920_9x16",
    }
    (out.parent / "masters-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
