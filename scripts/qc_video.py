from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return p.stdout.strip()


def probe(path: Path) -> dict:
    raw = run([
        'ffprobe','-v','error','-print_format','json','-show_format','-show_streams',str(path)
    ])
    return json.loads(raw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    ap.add_argument('--min-duration', type=float, default=35.0)
    ap.add_argument('--max-duration', type=float, default=60.0)
    args = ap.parse_args()

    matches = sorted(Path('output').glob(f'{args.id}-*-preview.mp4'))
    if not matches:
        raise SystemExit(f'No preview found for id={args.id}')
    video = matches[0]
    data = probe(video)
    streams = data.get('streams', [])
    fmt = data.get('format', {})

    v = next((s for s in streams if s.get('codec_type') == 'video'), None)
    a = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    duration = float(fmt.get('duration') or 0)

    checks = {
        'has_video': bool(v),
        'has_audio': bool(a),
        'vertical_1080x1920': bool(v and v.get('width') == 1080 and v.get('height') == 1920),
        'video_codec_h264': bool(v and v.get('codec_name') == 'h264'),
        'audio_codec_aac': bool(a and a.get('codec_name') == 'aac'),
        'duration_min_ok': duration >= args.min_duration,
        'duration_max_ok': duration <= args.max_duration,
    }

    hard_fail_keys = ['has_video','has_audio','vertical_1080x1920','video_codec_h264','audio_codec_aac','duration_min_ok']
    hard_pass = all(checks[k] for k in hard_fail_keys)
    publish_profile_pass = hard_pass and checks['duration_max_ok']

    report = {
        'id': args.id,
        'file': str(video),
        'duration_seconds': round(duration, 3),
        'checks': checks,
        'technical_pass': hard_pass,
        'short_publish_profile_pass': publish_profile_pass,
        'decision': 'PASS' if publish_profile_pass else ('REWORK_DURATION' if hard_pass else 'FAIL')
    }

    out = Path('output') / f'{args.id}-qc.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))

    if not hard_pass:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
