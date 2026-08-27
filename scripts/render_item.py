from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path


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


def chunks(text: str, max_chars: int = 62) -> list[str]:
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

    Path('output').mkdir(exist_ok=True)
    duration = probe_duration(voice)
    subtitle = Path('output') / f'{slug}.srt'
    write_srt(script_path.read_text(encoding='utf-8').strip(), duration, subtitle)

    storyboard = story / 'storyboard.json'
    title = slug.replace('-', ' ').upper()
    if storyboard.exists():
        try:
            data = json.loads(storyboard.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                title = str(data.get('title') or data.get('topic') or title)
        except Exception:
            pass

    out = Path('output') / f'{slug}-preview.mp4'
    escaped_sub = str(subtitle).replace(':', r'\:')
    vf = (
        "scale=1080:1920,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=0x101318:t=fill,"
        "drawbox=x=54:y=80:w=972:h=155:color=0x1b2029@0.96:t=fill,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{args.id}  CONTENT FACTORY':fontcolor=white:fontsize=48:x=72:y=125,"
        "drawbox=x=54:y=1520:w=972:h=260:color=black@0.38:t=fill,"
        f"subtitles='{escaped_sub}':force_style='FontName=DejaVu Sans,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=165'"
    )

    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=0x101318:s=1080x1920:d={duration}:r=30',
        '-i', str(voice), '-vf', vf,
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', '24', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(out)
    ], check=True)

    print(out)


if __name__ == '__main__':
    main()
