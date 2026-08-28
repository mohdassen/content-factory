from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


MOTION_PRESETS = [
    "z='min(1.035,1+on*0.00020)':x='(iw-iw/zoom)*0.48':y='(ih-ih/zoom)*0.56'",
    "z='min(1.030,1+on*0.00016)':x='(iw-iw/zoom)*(0.25+0.45*on/180)':y='(ih-ih/zoom)*0.48'",
    "z='if(eq(on,0),1.035,max(1.005,zoom-0.00016))':x='(iw-iw/zoom)*0.50':y='(ih-ih/zoom)*0.54'",
    "z='min(1.032,1+on*0.00017)':x='(iw-iw/zoom)*0.57':y='(ih-ih/zoom)*0.55'",
]


def find_story(content_id: str) -> Path:
    matches = sorted(Path('content').glob(f'{content_id}-*'))
    if not matches:
        raise SystemExit(f'No story directory found for id={content_id}')
    return matches[0]


def run_text(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60).stdout.strip()


def run_ffmpeg(cmd: list[str], timeout: int = 900) -> None:
    subprocess.run(cmd, check=True, timeout=timeout)


def probe_duration(media: Path) -> float:
    return float(run_text(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(media)]))


def probe_dimensions(image: Path) -> tuple[int, int]:
    raw = run_text(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', str(image)])
    w, h = raw.split('x')
    return int(w), int(h)


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, centi = divmod(rem, 100)
    return f'{h}:{m:02}:{s:02}.{centi:02}'


def load_timing(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        raise SystemExit('STRICT V3 requires narration timing metadata.')
    data = json.loads(path.read_text(encoding='utf-8'))
    words = data.get('words') or []
    if not words:
        raise SystemExit('STRICT V3 requires non-empty narration timing metadata.')
    return words, str(data.get('timing_source') or 'REAL_WORD_BOUNDARIES')


def scene_plan(story: Path, words: list[dict], duration: float) -> list[dict]:
    board = story / 'storyboard.json'
    if board.exists():
        scenes = json.loads(board.read_text(encoding='utf-8')).get('scenes') or []
        if scenes and all(int(s.get('narration_end_word', 0)) > 0 for s in scenes[:-1]):
            boundaries = [0.0]
            previous_word = 0
            for idx, scene in enumerate(scenes[:-1], 1):
                end_word = int(scene['narration_end_word'])
                if end_word <= previous_word or end_word > len(words):
                    raise SystemExit(f'Invalid narration_end_word in scene {idx:02}.')
                boundaries.append(float(words[end_word - 1]['end']))
                previous_word = end_word
            boundaries.append(duration)
            return [{'start': boundaries[i], 'end': boundaries[i + 1]} for i in range(len(boundaries) - 1)]

    paragraphs = [p.strip() for p in story.joinpath('script_ar.txt').read_text(encoding='utf-8').split('\n\n') if p.strip()]
    if len(paragraphs) < 2:
        raise SystemExit('STRICT V3 requires multiple narration paragraphs or an authored storyboard.')
    token_counts = [max(1, len(p.split())) for p in paragraphs]
    total_tokens = sum(token_counts)
    boundaries = [0.0]
    running = 0
    for count in token_counts[:-1]:
        running += count
        word_idx = min(len(words) - 1, max(0, round(running / total_tokens * len(words)) - 1))
        boundaries.append(float(words[word_idx]['end']))
    boundaries.append(duration)
    return [{'start': boundaries[i], 'end': boundaries[i + 1]} for i in range(len(boundaries) - 1)]


def chunks_from_words(words: list[dict], max_words: int = 7) -> list[dict]:
    rows = []
    for i in range(0, len(words), max_words):
        group = words[i:i + max_words]
        if group:
            rows.append({'start': float(group[0]['start']), 'end': float(group[-1]['end']), 'text': ' '.join(str(w['text']) for w in group)})
    return rows


def write_ass(words: list[dict], path: Path) -> None:
    header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Arabic,Noto Sans Arabic,54,&H00FFFFFF,&H00FFFFFF,&HCC000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,90,90,235,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    events = []
    for row in chunks_from_words(words):
        text = str(row['text']).replace('\n', r'\N')
        events.append(f"Dialogue: 0,{ass_time(row['start'])},{ass_time(row['end'])},Arabic,,0,0,0,,{{\\fad(70,90)}}{text}")
    path.write_text(header + '\n'.join(events) + '\n', encoding='utf-8')


def strict_master(slug: str, idx: int) -> Path:
    root = Path('assets') / 'stories' / slug / 'scenes'
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        candidate = root / f'{idx:02}.{ext}'
        if candidate.exists():
            return candidate
    raise SystemExit(f'BLOCKED: independent V3 master missing for scene {idx:02} in {root}.')


def validate_master(image: Path) -> tuple[int, int]:
    w, h = probe_dimensions(image)
    if w < 900 or h < 1400 or h <= w:
        raise SystemExit(f'BLOCKED: {image} is not a sufficiently large portrait master ({w}x{h}).')
    return w, h


def make_background(slug: str, scenes: list[dict], output: Path) -> tuple[Path, list[dict]]:
    seg_dir = output / f'{slug}-segments'
    seg_dir.mkdir(parents=True, exist_ok=True)
    files, visual_meta = [], []
    for idx, scene in enumerate(scenes, 1):
        length = max(0.35, scene['end'] - scene['start'])
        image = strict_master(slug, idx)
        w, h = validate_master(image)
        segment = seg_dir / f'{idx:02}.mp4'
        motion = MOTION_PRESETS[(idx - 1) % len(MOTION_PRESETS)]
        fade_in = 0.08 if idx > 1 else 0.15
        fade_out = 0.08 if idx < len(scenes) else 0.15
        fade_out_start = max(0.0, length - fade_out)
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"zoompan={motion}:d=1:s=1080x1920:fps=24,"
            "eq=contrast=1.02:saturation=1.015,"
            f"fade=t=in:st=0:d={fade_in:.3f},"
            f"fade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f},format=yuv420p"
        )
        run_ffmpeg([
            'ffmpeg', '-nostdin', '-y', '-hide_banner', '-loglevel', 'error', '-loop', '1', '-i', str(image),
            '-t', f'{length:.3f}', '-vf', vf, '-an', '-c:v', 'libx264',
            '-preset', 'ultrafast', '-crf', '20', '-r', '24', '-threads', '0', str(segment)
        ], timeout=300)
        files.append(segment)
        visual_meta.append({'scene': idx, 'master': str(image), 'source_width': w, 'source_height': h, 'fit': 'aspect_preserved_center_crop'})

    concat = seg_dir / 'concat.txt'
    concat.write_text('\n'.join(f"file '{p.resolve()}'" for p in files), encoding='utf-8')
    bg = output / f'{slug}-background.mp4'
    run_ffmpeg(['ffmpeg', '-nostdin', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', str(bg)], timeout=120)
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
    logo = Path('assets') / 'brand' / 'logo.webp'
    if not voice.exists():
        raise SystemExit('Missing narration audio.')
    if not logo.exists():
        raise SystemExit('STRICT V3 requires the approved brand logo asset.')
    duration = probe_duration(voice)
    words, timing_source = load_timing(timing)
    scenes = scene_plan(story, words, duration)
    subtitle = output / f'{slug}.ass'
    write_ass(words, subtitle)
    bg, masters = make_background(slug, scenes, output)
    sub = str(subtitle).replace(':', r'\:').replace("'", r"\'")
    filter_complex = (
        f"[0:v]subtitles='{sub}',drawbox=x=70:y=1830:w='940*t/{duration:.6f}':h=4:color=white@0.30:t=fill[base];"
        "[2:v]scale=150:-1,format=rgba,colorchannelmixer=aa=0.82[logo];"
        "[base][logo]overlay=W-w-38:42,format=yuv420p[v]"
    )
    out = output / f'{slug}-preview.mp4'
    run_ffmpeg([
        'ffmpeg', '-nostdin', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(bg), '-i', str(voice), '-loop', '1', '-i', str(logo),
        '-filter_complex', filter_complex, '-map', '[v]', '-map', '1:a:0',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
        '-shortest', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-threads', '0', str(out)
    ], timeout=420)
    metadata = output / f'{slug}-render.json'
    metadata.write_text(json.dumps({
        'slug': slug,
        'architecture': 'V3_GOLDEN_STRICT',
        'duration': round(duration, 3),
        'scene_count': len(scenes),
        'narration_timing': timing_source,
        'scene_timing': 'NARRATION_PARAGRAPH_ALIGNED',
        'all_visuals_are_approved_masters': True,
        'brand_name': 'خلف الشاشة',
        'brand_logo': str(logo),
        'brand_logo_position': 'top_right',
        'visuals': masters,
        'forbidden_fallbacks_enabled': False,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
