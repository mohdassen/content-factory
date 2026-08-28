from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


MOTION_PRESETS = [
    "z='min(1.055,1+on*0.00018)':x='(iw-iw/zoom)*0.44':y='(ih-ih/zoom)*0.56'",
    "z='min(1.045,1+on*0.00014)':x='(iw-iw/zoom)*(0.20+0.55*on/220)':y='(ih-ih/zoom)*0.46'",
    "z='if(eq(on,0),1.05,max(1.006,zoom-0.00016))':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.54'",
    "z='min(1.055,1+on*0.00016)':x='(iw-iw/zoom)*0.56':y='(ih-ih/zoom)*0.58'",
    "z='min(1.05,1+on*0.00022)':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.40'",
    "z='min(1.038,1+on*0.00012)':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*(0.70-0.28*on/150)'",
    "z='min(1.07,1+on*0.00028)':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.50'",
    "z='if(eq(on,0),1.055,max(1.01,zoom-0.00015))':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.45'",
    "z='min(1.06,1+on*0.00022)':x='(iw-iw/zoom)*(0.47+0.15*on/160)':y='(ih-ih/zoom)*(0.60-0.16*on/160)'",
]


def find_story(content_id: str) -> Path:
    matches = sorted(Path('content').glob(f'{content_id}-*'))
    if not matches:
        raise SystemExit(f'No story directory found for id={content_id}')
    return matches[0]


def probe_duration(media: Path) -> float:
    r = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(media)
    ], check=True, capture_output=True, text=True)
    return float(r.stdout.strip())


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, centi = divmod(rem, 100)
    return f'{h}:{m:02}:{s:02}.{centi:02}'


def load_words(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('words') or []
    except Exception:
        return []


def split_sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?؟؛…])\s+|\n+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def sentence_end_times(script: str, words: list[dict]) -> list[float]:
    if not words:
        return []
    sentences = split_sentences(script)
    ends: list[float] = []
    cursor = 0
    for sentence in sentences:
        count = max(1, len(sentence.split()))
        cursor = min(len(words), cursor + count)
        if cursor:
            ends.append(float(words[cursor - 1]['end']))
        if cursor >= len(words):
            break
    if ends and ends[-1] < float(words[-1]['end']):
        ends[-1] = float(words[-1]['end'])
    return ends


def chunks_from_words(words: list[dict], max_words: int = 7) -> list[dict]:
    rows: list[dict] = []
    for i in range(0, len(words), max_words):
        group = words[i:i + max_words]
        if not group:
            continue
        rows.append({
            'start': float(group[0]['start']),
            'end': float(group[-1]['end']),
            'text': ' '.join(str(w['text']) for w in group),
        })
    return rows


def fallback_caption_rows(script: str, duration: float, max_words: int = 7) -> list[dict]:
    tokens = script.replace('\n', ' ').split()
    groups = [' '.join(tokens[i:i + max_words]) for i in range(0, len(tokens), max_words)]
    weights = [max(1, len(x.split())) for x in groups]
    total = sum(weights) or 1
    cursor = 0.0
    rows = []
    for text, weight in zip(groups, weights):
        seg = duration * weight / total
        rows.append({'start': cursor, 'end': min(duration, cursor + seg), 'text': text})
        cursor += seg
    return rows


def write_ass(script: str, duration: float, words: list[dict], path: Path) -> None:
    rows = chunks_from_words(words) if words else fallback_caption_rows(script, duration)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Arabic,Noto Sans Arabic,54,&H00FFFFFF,&H00FFFFFF,&HCC000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,90,90,235,1
Style: Brand,Noto Sans Arabic,30,&H88FFFFFF,&H88FFFFFF,&H66000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,9,50,50,65,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for row in rows:
        text = str(row['text']).replace('\n', r'\N')
        events.append(
            f"Dialogue: 0,{ass_time(row['start'])},{ass_time(row['end'])},Arabic,,0,0,0,,{{\\fad(80,100)}}{text}"
        )
    events.append(f"Dialogue: 1,0:00:00.00,{ass_time(duration)},Brand,,0,0,0,,خلف الشاشة")
    path.write_text(header + '\n'.join(events) + '\n', encoding='utf-8')


def load_storyboard(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('scenes') or []
    except Exception:
        return []


def aligned_scenes(storyboard: list[dict], duration: float, sentence_ends: list[float]) -> list[dict]:
    if not storyboard:
        step = duration / 6
        return [{'start': i * step, 'end': min(duration, (i + 1) * step)} for i in range(6)]

    authored_end = max(float(s.get('end', 0)) for s in storyboard) or duration
    desired = [float(s.get('end', authored_end)) / authored_end * duration for s in storyboard[:-1]]
    cuts: list[float] = []
    previous = 0.0

    for target in desired:
        candidates = [x for x in sentence_ends if x > previous + 0.8]
        if candidates:
            chosen = min(candidates, key=lambda x: abs(x - target))
            if abs(chosen - target) <= 2.2:
                cut = chosen
            else:
                cut = target
        else:
            cut = target
        cut = min(duration - 0.8, max(previous + 0.8, cut))
        cuts.append(cut)
        previous = cut

    boundaries = [0.0, *cuts, duration]
    return [
        {'start': boundaries[i], 'end': boundaries[i + 1]}
        for i in range(len(boundaries) - 1)
    ]


def find_visual(slug: str, idx: int, output: Path) -> tuple[Path | None, bool]:
    approved_dir = Path('assets') / 'stories' / slug / 'scenes'
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        p = approved_dir / f'{idx:02}.{ext}'
        if p.exists():
            return p, True

    fallback_dir = output / 'visuals' / slug
    for ext in ('jpg', 'jpeg', 'png', 'webp'):
        p = fallback_dir / f'{idx:02}.{ext}'
        if p.exists():
            return p, False
    return None, False


def make_background(slug: str, scenes: list[dict], output: Path) -> tuple[Path, bool]:
    seg_dir = output / f'{slug}-segments'
    seg_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    approved_used = False

    for idx, scene in enumerate(scenes, 1):
        length = max(.25, scene['end'] - scene['start'])
        image, approved = find_visual(slug, idx, output)
        approved_used = approved_used or approved
        segment = seg_dir / f'{idx:02}.mp4'

        if image is None:
            raise SystemExit(
                f'Missing primary visual for scene {idx:02}. '
                'Publish-ready rendering may not silently use an empty background.'
            )

        motion = MOTION_PRESETS[(idx - 1) % len(MOTION_PRESETS)]
        fade_in = 0.20 if idx == 1 else 0.08
        fade_out = 0.08 if idx < len(scenes) else 0.18
        fade_out_start = max(0.0, length - fade_out)

        vf = (
            "scale=1110:1973:force_original_aspect_ratio=increase,"
            "crop=1110:1973,"
            f"zoompan={motion}:d=1:s=1080x1920:fps=30,"
            "eq=contrast=1.035:saturation=1.025:brightness=-0.004:gamma=1.01,"
            "unsharp=5:5:0.18:5:5:0.0,"
            "vignette=PI/9:eval=frame,"
            f"fade=t=in:st=0:d={fade_in:.3f},"
            f"fade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f},"
            "format=yuv420p"
        )

        subprocess.run([
            'ffmpeg', '-y', '-framerate', '30', '-loop', '1', '-i', str(image),
            '-t', f'{length:.3f}', '-vf', vf, '-an', '-c:v', 'libx264',
            '-preset', 'ultrafast', '-crf', '21', '-r', '30', str(segment)
        ], check=True)
        files.append(segment)

    concat = seg_dir / 'concat.txt'
    concat.write_text('\n'.join(f"file '{p.resolve()}'" for p in files), encoding='utf-8')
    bg = output / f'{slug}-background.mp4'
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat),
        '-c', 'copy', str(bg)
    ], check=True)
    return bg, approved_used


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    args = ap.parse_args()

    story = find_story(args.id)
    slug = story.name
    output = Path('output')
    output.mkdir(exist_ok=True)

    voice = output / f'{slug}-voice.mp3'
    script_path = story / 'script_ar.txt'
    timing_path = output / f'{slug}-word-boundaries.json'
    if not voice.exists() or not script_path.exists():
        raise SystemExit('Missing script or voice')

    duration = probe_duration(voice)
    script = script_path.read_text(encoding='utf-8').strip()
    words = load_words(timing_path)
    sentence_ends = sentence_end_times(script, words)
    storyboard = load_storyboard(story / 'storyboard.json')
    scenes = aligned_scenes(storyboard, duration, sentence_ends)

    subtitle = output / f'{slug}.ass'
    write_ass(script, duration, words, subtitle)
    bg, approved_used = make_background(slug, scenes, output)

    sub = str(subtitle).replace(':', r'\:').replace("'", r"\'")
    vf = (
        f"subtitles='{sub}',"
        f"drawbox=x=70:y=1830:w='940*t/{duration:.6f}':h=4:color=white@0.34:t=fill,"
        "format=yuv420p"
    )

    out = output / f'{slug}-preview.mp4'
    subprocess.run([
        'ffmpeg', '-y', '-i', str(bg), '-i', str(voice),
        '-vf', vf, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7',
        '-map', '0:v:0', '-map', '1:a:0',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(out)
    ], check=True)

    metadata = output / f'{slug}-render.json'
    metadata.write_text(json.dumps({
        'slug': slug,
        'duration': round(duration, 3),
        'scene_count': len(scenes),
        'narration_timing': bool(words),
        'approved_ai_master_used': approved_used,
        'architecture': 'V3_GOLDEN',
    }, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
