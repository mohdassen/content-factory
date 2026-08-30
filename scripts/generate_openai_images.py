#!/usr/bin/env python3
import base64
import io
import json
import os
import pathlib
import time

from openai import OpenAI
from PIL import Image

EPISODE = os.environ["EPISODE"]
ROOT = pathlib.Path("episodes") / EPISODE
OUT = pathlib.Path("build/images")
OUT.mkdir(parents=True, exist_ok=True)

api_key = os.environ.get("OPENAI_API_KEY", "").strip()
if not api_key:
    raise RuntimeError("OPENAI_API_KEY GitHub secret is required for Saher History image generation")

request = json.loads((ROOT / "request.json").read_text(encoding="utf-8"))
chapters = sorted((ROOT / "chapters").glob("*.txt"))
prompts = request.get("visual_prompts", [])
style = request.get(
    "visual_style",
    "warm cinematic Abbasid Baghdad, historically plausible medieval daily life, quiet sleep-history documentary atmosphere",
)

client = OpenAI(api_key=api_key)
manifest = []


def prepare_image(raw: bytes, out_path: pathlib.Path) -> None:
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = image.size
    target_ratio = 16 / 9
    ratio = w / h
    if ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        image = image.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        image = image.crop((0, top, w, top + new_h))
    image = image.resize((1280, 720), Image.Resampling.LANCZOS)
    image.save(out_path, format="JPEG", quality=95, optimize=True)


for i, _chapter in enumerate(chapters, 1):
    out_path = OUT / f"{i:02d}.jpg"

    # Prefer a deliberately curated local image if one has been committed.
    local_candidates = [
        ROOT / "images" / f"{i:02d}.jpg",
        ROOT / "images" / f"{i:02d}.jpeg",
        ROOT / "images" / f"{i:02d}.png",
        ROOT / "images" / f"{i:02d}.webp",
    ]
    local = next((p for p in local_candidates if p.exists()), None)
    if local:
        with Image.open(local) as img:
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="PNG")
        prepare_image(buf.getvalue(), out_path)
        manifest.append({"chapter": i, "source": "repository", "file": str(out_path)})
        print(f"chapter {i:02d}: using repository image {local}")
        continue

    base = prompts[i - 1] if i - 1 < len(prompts) else style
    prompt = (
        f"{base}. {style}. "
        "Create one single horizontal cinematic historical documentary frame for an Arabic sleep-history film. "
        "Abbasid Baghdad around the 10th century, historically plausible materials, clothing, architecture and daily life; "
        "warm natural light, atmospheric depth, refined painterly photorealism, subtle filmic texture, calm composition, "
        "no modern objects. Absolutely no text, letters, numerals, captions, signs, logos, borders, collage, watermark or UI."
    )

    last_error = None
    for attempt in range(1, 4):
        try:
            result = client.images.generate(
                model="gpt-image-2",
                prompt=prompt,
                size="1536x1024",
                quality="medium",
                n=1,
            )
            item = result.data[0]
            if not item.b64_json:
                raise RuntimeError("OpenAI image response did not contain b64_json")
            raw = base64.b64decode(item.b64_json)
            prepare_image(raw, out_path)
            manifest.append(
                {
                    "chapter": i,
                    "source": "openai",
                    "model": "gpt-image-2",
                    "file": str(out_path),
                }
            )
            print(f"chapter {i:02d}: generated with OpenAI gpt-image-2")
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            print(f"chapter {i:02d}: attempt {attempt}/3 failed: {exc}")
            if attempt < 3:
                time.sleep(5 * attempt)

    if last_error is not None:
        raise RuntimeError(f"OpenAI image generation failed for chapter {i:02d}: {last_error}")

(pathlib.Path("build") / "image_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"Generated/validated {len(manifest)} chapter images using OpenAI or curated repository images only.")
