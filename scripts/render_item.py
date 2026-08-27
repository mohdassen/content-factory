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
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(audio)
    ], check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f'{h:02}:{m:02}:{s:02},{milli:03}'


def chunks(text: str, max_chars: int = 56) -> list[str]:
    words = text.replace('\n', ' ').split()
    out, current = [], []
    length = 0
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
    cursor = 0.0
    rows = []
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
        scenes = [
            {'start': i * step, 'end': min(duration, (i + 1) * step), 'caption': title}
            for i in range(6)
        ]

    # Storyboards can be authored for an older narration duration. Scale timing
    # proportionally so the final scene still lands on the end of the voice track.
    authored_end = max(float(s.get('end', 0)) for s in scenes) or duration
    scale = duration / authored_end
    normalized = []
    for scene in scenes:
        start = max(0.0, float(scene.get('start', 0)) * scale)
        end = min(duration, float(scene.get('end', authored_end)) * scale)
        if end <= start:
            continue
        normalized.append({
            'start': start,
            'end': end,
            'caption': str(scene.get('caption') or title).strip(),
        })
    return title, normalized


def esc_path(path: Path) -> str:
    return str(path).replace('\\', '/').replace(':', r'\:').replace("'", r"\'")


def scene_filters(scenes: list[dict], work: Path) -> list[str]:
    filters: list[str] = []
    accents = ['0xd9262e', '0xf2a900', '0x4cc9f0', '0x7bd389', '0xb388ff', '0xff7a59']

    for idx, scene in enumerate(scenes):
        start = scene['start']
        end = scene['end']
        accent = accents[idx % len(accents)]
        text_file = work / f'scene-{idx:02}.txt'
        text_file.write_text(scene['caption'], encoding='utf-8')
        text_path = esc_path(text_file)
        enable = f"between(t,{start:.3f},{end:.3f})"

        # Full-height accent rail + glass card; each scene changes its composition.
        side = 72 if idx % 2 == 0 else 968
        card_y = 420 + (idx % 3) * 105
        filters.extend([
            f"drawbox=x={side}:y=300:w=16:h=780:color={accent}@0.92:t=fill:enable='{enable}'",
            f"drawbox=x=92:y={card_y}:w=896:h=430:color=0x171c24@0.90:t=fill:enable='{enable}'",
            f"drawbox=x=92:y={card_y}:w=896:h=8:color={accent}@1.0:t=fill:enable='{enable}'",
            (
                f"drawtext=fontfile={FONT_BOLD}:textfile='{text_path}':fontcolor=white:fontsize=58:"
                f"x=(w-text_w)/2:y={card_y + 120}+18*sin((t-{start:.3f})*2.4):"
                f"box=0:line_spacing=18:enable='{enable}'"
            ),
            (
                f"drawtext=fontfile={FONT_BOLD}:text='{idx + 1:02}':fontcolor={accent}:fontsize=150:"
                f"x={'120' if idx % 2 == 0 else '820'}:y=250+10*sin((t-{start:.3f})*3):"
                f"alpha='0.13+0.05*sin((t-{start:.3f})*4)':enable='{enable}'"
            ),
        ])
    return filters


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    args = parser.parse_args()

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
    title_file = output / f'{slug}-title.txt'
    title_file.write_text(title, encoding='utf-8')

    escaped_sub = esc_path(subtitle)
    escaped_title = esc_path(title_file)

    filters = [
        'scale=1080:1920',
        'drawbox=x=0:y=0:w=iw:h=ih:color=0x0b0e13:t=fill',
        # subtle frame and moving top marker create constant motion without distraction
        'drawbox=x=48:y=58:w=984:h=1804:color=0x202733@0.42:t=6',
        "drawbox=x='60+mod(t*145,840)':y=74:w=180:h=7:color=white@0.50:t=fill",
        'drawbox=x=72:y=118:w=936:h=120:color=0x151a22@0.88:t=fill',
        (
            f"drawtext=fontfile={FONT_BOLD}:textfile='{escaped_title}':fontcolor=white:fontsize=36:"
            "x=(w-text_w)/2:y=155"
        ),
        (
            f"drawtext=fontfile={FONT_BOLD}:text='{args.id}':fontcolor=white@0.35:fontsize=26:"
            "x=90:y=1810"
        ),
    ]

    filters.extend(scene_filters(scenes, output))

    # Narration captions remain readable but no longer dominate the entire canvas.
    filters.extend([
        'drawbox=x=58:y=1515:w=964:h=265:color=black@0.48:t=fill',
        (
            f"subtitles='{escaped_sub}':"
            "force_style='FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=165'"
        ),
        # Bottom progress bar: width grows with narration time.
        f"drawbox=x=58:y=1830:w='964*t/{duration:.6f}':h=8:color=white@0.70:t=fill",
    ])

    vf = ','.join(filters)
    out = output / f'{slug}-preview.mp4'

    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=0x0b0e13:s=1080x1920:d={duration}:r=30',
        '-i', str(voice), '-vf', vf,
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', '22', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(out)
    ], check=True)

    print(out)


if __name__ == '__main__':
    main()
