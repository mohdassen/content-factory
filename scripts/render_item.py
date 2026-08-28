from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


MOTION_PRESETS = [
    "z='min(1.045,1+on*0.00018)':x='(iw-iw/zoom)*0.48':y='(ih-ih/zoom)*0.56'",
    "z='min(1.035,1+on*0.00014)':x='(iw-iw/zoom)*(0.22+0.50*on/240)':y='(ih-ih/zoom)*0.48'",
    "z='if(eq(on,0),1.04,max(1.006,zoom-0.00014))':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.54'",
    "z='min(1.04,1+on*0.00015)':x='(iw-iw/zoom)*0.57':y='(ih-ih/zoom)*0.55'",
    "z='min(1.045,1+on*0.00018)':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.42'",
    "z='min(1.032,1+on*0.00011)':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*(0.68-0.24*on/180)'",
    "z='min(1.05,1+on*0.00020)':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.50'",
    "z='if(eq(on,0),1.045,max(1.008,zoom-0.00013))':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.44'",
    "z='min(1.045,1+on*0.00017)':x='(iw-iw/zoom)*(0.46+0.12*on/190)':y='(ih-ih/zoom)*(0.58-0.13*on/190)'",
]


def find_story(content_id: str) -> Path:
    matches = sorted(Path('content').glob(f'{content_id}-*'))
    if not matches:
        raise SystemExit(f'No story directory found for id={content_id}')
    return matches[0]


def run_text(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def probe_duration(media: Path) -> float:
    return float(run_text([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(media)
    ]))


def probe_dimensions(image: Path) -> tuple[int, int]:
    raw = run_text([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', str(image)
    ])
    w, h = raw.split('x')
    return int(w), int(h)


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, centi = divmod(rem, 100)
    return f'{h}:{m:02}:{s:02}.{centi:02}'


def load_words(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit('STRICT V3 requires real word-boundary timing metadata.')
    data = json.loads(path.read_text(encoding='utf-8'))
    words = data.get('words') or []
    if not words:
        raise SystemExit('STRICT V3 requires non-empty word-boundary timing metadata.')
    return words


def load_storyboard(path: Path) -> list[dict]:
    scenes = json.loads(path.read_text(encoding='utf-8')).get('scenes') or []
    if not scenes:
        raise SystemExit('STRICT V3 requires an authored scene plan.')
    return scenes


def timed_scenes(storyboard: list[dict], words: list[dict], duration: float) -> list[dict]:
    boundaries = [0.0]
    previous_word = 0
    for idx, scene in enumerate(storyboard[:-1], 1):
        end_word = int(scene.get('narration_end_word', 0))
        if end_word <= previous_word or end_word > len(words):
            raise SystemExit(
                f'STRICT V3 scene {idx:02} has invalid narration_end_word={end_word}; '
                f'word count={len(words)}.'
            )
        boundaries.append(float(words[end_word - 1]['end']))
        previous_word = end_word
    boundaries.append(duration)
    return [
        {'start': boundaries[i], 'end': boundaries[i + 1]}
        for i in range(len(boundaries) - 1)
    ]


def chunks_from_words(words: list[dict], max_words: int = 7) -> list[dict]:
    rows = []
    for i in range(0, len(words), max_words):
        group = words[i:i + max_words]
        if group:
            rows.append({
                'start': float(group[0]['start']),
                'end': float(group[-1]['end']),
                'text': ' '.join(str(w['text']) for w in group),
            })
    return rows


def write_ass(words: list[dict], duration: float, path: Path) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Arabic,Noto Sans Arabic,54,&H00FFFFFF,&H00FFFFFF,&HCC000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,90,90,235,1
Style: Brand,Noto Sans Arabic,28,&H80FFFFFF,&H80FFFFFF,&H66000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,9,45,45,58,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for row in chunks_from_words(words):
        text = str(row['text']).replace('\n', r'\N')
        events.append(
            f"Dialogue: 0,{ass_time(row['start'])},{ass_time(row['end'])},Arabic,,0,0,0,,{{\\fad(70,90)}}{text}"
        )
    events.append(f"Dialogue: 1,0:00:00.00,{ass_time(duration)},Brand,,0,0,0,,خلف الشاشة")
    path.write_text(header + '\n'.join(events) + '\n', encoding='utf-8')


def strict_master(slug: str, idx: int) -> Path:
    root = Path('assets') / 'stories' / slug / 'scenes'
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        candidate = root / f'{idx:02}.{ext}'
        if candidate.exists():
            return candidate
    raise SystemExit(
        f'BLOCKED: approved independent V3 master missing for scene {idx:02} in {root}. '
        'Stock, storyboard crops and motion-graphics fallbacks are forbidden.'
    )


def validate_master(image: Path) -> tuple[int, int]:
    w, h = probe_dimensions(image)
    ratio = w / h
    if abs(ratio - (9 / 16)) > 0.025:
        raise SystemExit(f'BLOCKED: {image} is not a valid 9:16 master ({w}x{h}).')
    if w < 900 or h < 1600:
        raise SystemExit(f'BLOCKED: {image} is too small for V3 quality ({w}x{h}).')
    return w, h


def make_background(slug: str, scenes: list[dict], output: Path) -> tuple[Path, list[dict]]:
    seg_dir = output / f'{slug}-segments'
    seg_dir.mkdir(parents=True, exist_ok=True)
    files = []
    visual_meta = []

    for idx, scene in enumerate(scenes, 1):
        length = max(0.35, scene['end'] - scene['start'])
        image = strict_master(slug, idx)
        w, h = validate_master(image)
        segment = seg_dir / f'{idx:02}.mp4'
        motion = MOTION_PRESETS[(idx - 1) % len(MOTION_PRESETS)]

        # Tiny cinematic fades; source remains full-frame and aspect-preserved.
        fade_in = 0.10 if idx > 1 else 0.18
        fade_out = 0.10 if idx < len(scenes) else 0.20
        fade_out_start = max(0.0, length - fade_out)
        vf = (
            "scale=1100:1956:force_original_aspect_ratio=increase,"
            "crop=1100:1956,"
            f"zoompan={motion}:d=1:s=1080x1920:fps=30,"
            "eq=contrast=1.025:saturation=1.018:brightness=-0.002:gamma=1.008,"
            "unsharp=5:5:0.12:5:5:0.0,"
            "vignette=PI/11:eval=frame,"
            f"fade=t=in:st=0:d={fade_in:.3f},"
            f"fade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f},"
            "format=yuv420p"
        )
        subprocess.run([
            'ffmpeg', '-y', '-framerate', '30', '-loop', '1', '-i', str(image),
            '-t', f'{length:.3f}', '-vf', vf, '-an', '-c:v', 'libx264',
            '-preset', 'medium', '-crf', '18', '-r', '30', str(segment)
        ], check=True)
        files.append(segment)
        visual_meta.append({'scene': idx, 'master': str(image), 'source_width': w, 'source_height': h})

    concat = seg_dir / 'concat.txt'
    concat.write_text('\n'.join(f"file '{p.resolve()}'" for p in files), encoding='utf-8')
    bg = output / f'{slug}-background.mp4'
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', str(bg)], check=True)
    return bg, visual_meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    args = ap.parse_args()

    story = find_story(args.id)
    slug = story.name
    output = Path('output')
    output.mkdir(exist_ok=True)

    voice = output / f'{slug}-voice.mp3'
    timing = output / f'{slug}-word-boundaries.json'
    if not voice.exists():
        raise SystemExit('Missing narration audio.')

    duration = probe_duration(voice)
    words = load_words(timing)
    storyboard = load_storyboard(story / 'storyboard.json')
    scenes = timed_scenes(storyboard, words, duration)

    subtitle = output / f'{slug}.ass'
    write_ass(words, duration, subtitle)
    bg, masters = make_background(slug, scenes, output)

    sub = str(subtitle).replace(':', r'\:').replace("'", r"\'")
    vf = (
        f"subtitles='{sub}',"
        f"drawbox=x=70:y=1830:w='940*t/{duration:.6f}':h=4:color=white@0.30:t=fill,"
        "format=yuv420p"
    )
    out = output / f'{slug}-preview.mp4'
    subprocess.run([
        'ffmpeg', '-y', '-i', str(bg), '-i', str(voice),
        '-vf', vf, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7',
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264',
        '-preset', 'medium', '-crf', '18', '-c:a', 'aac', '-b:a', '192k',
        '-shortest', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)
    ], check=True)

    metadata = output / f'{slug}-render.json'
    metadata.write_text(json.dumps({
        'slug': slug,
        'architecture': 'V3_GOLDEN_STRICT',
        'duration': round(duration, 3),
        'scene_count': len(scenes),
        'narration_timing': 'REAL_WORD_BOUNDARIES',
        'all_visuals_are_approved_masters': True,
        'visuals': masters,
        'forbidden_fallbacks_enabled': False,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
