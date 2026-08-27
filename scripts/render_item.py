from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def find_story(content_id: str) -> Path:
    matches = sorted(Path('content').glob(f'{content_id}-*'))
    if not matches:
        raise SystemExit(f'No story directory found for id={content_id}')
    return matches[0]


def probe_duration(audio: Path) -> float:
    r = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(audio)
    ], check=True, capture_output=True, text=True)
    return float(r.stdout.strip())


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f'{h:02}:{m:02}:{s:02},{milli:03}'


def chunks(text: str, max_chars: int = 56) -> list[str]:
    words = text.replace('\n', ' ').split()
    out, current, length = [], [], 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and length + extra > max_chars:
            out.append(' '.join(current))
            current, length = [word], len(word)
        else:
            current.append(word)
            length += extra
    if current:
        out.append(' '.join(current))
    return out


def write_srt(script: str, duration: float, path: Path) -> None:
    parts = chunks(script)
    weights = [max(1, len(p.split())) for p in parts]
    total = sum(weights)
    cursor, rows = 0.0, []
    for i, (part, weight) in enumerate(zip(parts, weights), 1):
        seg = duration * weight / total
        start, end = cursor, min(duration, cursor + seg)
        rows.append(f'{i}\n{srt_time(start)} --> {srt_time(end)}\n{part}\n')
        cursor = end
    path.write_text('\n'.join(rows), encoding='utf-8')


def load_storyboard(path: Path, duration: float) -> tuple[str, list[dict]]:
    title = path.parent.name.replace('-', ' ').upper()
    scenes: list[dict] = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            title = str(data.get('title') or data.get('topic') or title)
            scenes = data.get('scenes') or []
        except Exception:
            scenes = []
    if not scenes:
        step = duration / 6
        scenes = [{'start': i * step, 'end': min(duration, (i + 1) * step), 'caption': title} for i in range(6)]
    authored_end = max(float(s.get('end', 0)) for s in scenes) or duration
    scale = duration / authored_end
    normalized = []
    for scene in scenes:
        start = max(0.0, float(scene.get('start', 0)) * scale)
        end = min(duration, float(scene.get('end', authored_end)) * scale)
        if end > start:
            normalized.append({'start': start, 'end': end, 'caption': str(scene.get('caption') or title).strip()})
    return title, normalized


def esc_path(path: Path) -> str:
    return str(path).replace('\\', '/').replace(':', r'\:').replace("'", r"\'")


def make_background(slug: str, scenes: list[dict], output: Path) -> Path:
    visual_dir = output / 'visuals' / slug
    seg_dir = output / f'{slug}-segments'
    seg_dir.mkdir(parents=True, exist_ok=True)
    segment_files: list[Path] = []

    for idx, scene in enumerate(scenes, 1):
        seg_len = max(0.25, scene['end'] - scene['start'])
        image = visual_dir / f'{idx:02}.jpg'
        segment = seg_dir / f'{idx:02}.mp4'
        if image.exists():
            # Cinematic Ken Burns motion. Alternate zoom direction and horizontal framing.
            zoom = "min(zoom+0.0008,1.12)" if idx % 2 else "if(lte(zoom,1.0),1.12,max(1.0,zoom-0.0008))"
            xexpr = "iw/2-(iw/zoom/2)+12*sin(on/18)" if idx % 2 else "iw/2-(iw/zoom/2)-12*sin(on/20)"
            vf = (
                "scale=1280:2276:force_original_aspect_ratio=increase,crop=1280:2276,"
                f"zoompan=z='{zoom}':x='{xexpr}':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
                "eq=contrast=1.05:saturation=0.92:brightness=-0.035,"
                "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.20:t=fill,format=yuv420p"
            )
            cmd = ['ffmpeg', '-y', '-loop', '1', '-i', str(image), '-t', f'{seg_len:.3f}', '-vf', vf,
                   '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '24', '-r', '30', str(segment)]
        else:
            # Deterministic fallback still has visual motion and scene-specific tone.
            palette = ['0x101318', '0x151018', '0x0d1620', '0x151810', '0x111221', '0x181211']
            color = palette[(idx - 1) % len(palette)]
            vf = (
                "drawgrid=width=120:height=120:thickness=2:color=white@0.025,"
                f"drawbox=x='-300+mod(t*85+{idx*70},1380)':y=0:w=420:h=1920:color=white@0.025:t=fill,"
                "format=yuv420p"
            )
            cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c={color}:s=1080x1920:d={seg_len:.3f}:r=30',
                   '-vf', vf, '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25', str(segment)]
        subprocess.run(cmd, check=True)
        segment_files.append(segment)

    concat_file = seg_dir / 'concat.txt'
    concat_file.write_text('\n'.join(f"file '{p.resolve()}'" for p in segment_files), encoding='utf-8')
    background = output / f'{slug}-background.mp4'
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file), '-c', 'copy', str(background)], check=True)
    return background


def scene_filters(scenes: list[dict], work: Path) -> list[str]:
    filters: list[str] = []
    accents = ['0xd9262e', '0xf2a900', '0x4cc9f0', '0x7bd389', '0xb388ff', '0xff7a59']
    for idx, scene in enumerate(scenes):
        start, end = scene['start'], scene['end']
        accent = accents[idx % len(accents)]
        text_file = work / f'scene-{idx:02}.txt'
        text_file.write_text(scene['caption'], encoding='utf-8')
        text_path = esc_path(text_file)
        enable = f"between(t,{start:.3f},{end:.3f})"
        card_y = 420 + (idx % 3) * 95
        filters.extend([
            f"drawbox=x=64:y={card_y}:w=952:h=395:color=black@0.42:t=fill:enable='{enable}'",
            f"drawbox=x=64:y={card_y}:w=14:h=395:color={accent}@0.95:t=fill:enable='{enable}'",
            f"drawtext=fontfile={FONT_BOLD}:textfile='{text_path}':fontcolor=white:fontsize=56:x=(w-text_w)/2:y={card_y+120}+12*sin((t-{start:.3f})*2.5):line_spacing=18:enable='{enable}'",
            f"drawtext=fontfile={FONT_BOLD}:text='{idx+1:02}':fontcolor={accent}:fontsize=132:x={120 if idx%2==0 else 835}:y=280:alpha='0.16+0.04*sin((t-{start:.3f})*4)':enable='{enable}'",
        ])
    return filters


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    args = ap.parse_args()

    story = find_story(args.id)
    slug = story.name
    script_path = story / 'script_ar.txt'
    voice = Path('output') / f'{slug}-voice.mp3'
    if not script_path.exists() or not voice.exists():
        raise SystemExit('Missing script or generated voice')

    output = Path('output')
    output.mkdir(exist_ok=True)
    duration = probe_duration(voice)
    subtitle = output / f'{slug}.srt'
    write_srt(script_path.read_text(encoding='utf-8').strip(), duration, subtitle)
    title, scenes = load_storyboard(story / 'storyboard.json', duration)
    background = make_background(slug, scenes, output)

    title_file = output / f'{slug}-title.txt'
    title_file.write_text(title, encoding='utf-8')
    escaped_sub, escaped_title = esc_path(subtitle), esc_path(title_file)

    filters = [
        'scale=1080:1920',
        'drawbox=x=0:y=0:w=iw:h=ih:color=black@0.08:t=fill',
        'drawbox=x=48:y=58:w=984:h=1804:color=white@0.10:t=4',
        "drawbox=x='60+mod(t*145,840)':y=74:w=180:h=7:color=white@0.55:t=fill",
        'drawbox=x=72:y=118:w=936:h=120:color=black@0.42:t=fill',
        f"drawtext=fontfile={FONT_BOLD}:textfile='{escaped_title}':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=155",
        f"drawtext=fontfile={FONT_BOLD}:text='{args.id}':fontcolor=white@0.42:fontsize=26:x=90:y=1810",
    ]
    filters.extend(scene_filters(scenes, output))
    filters.extend([
        'drawbox=x=58:y=1515:w=964:h=265:color=black@0.48:t=fill',
        f"subtitles='{escaped_sub}':force_style='FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=165'",
        f"drawbox=x=58:y=1830:w='964*t/{duration:.6f}':h=8:color=white@0.75:t=fill",
    ])

    out = output / f'{slug}-preview.mp4'
    subprocess.run([
        'ffmpeg', '-y', '-i', str(background), '-i', str(voice), '-vf', ','.join(filters),
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
        '-c:a', 'aac', '-b:a', '160k', '-shortest', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)
    ], check=True)
    print(out)


if __name__ == '__main__':
    main()
