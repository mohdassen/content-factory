from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


def find_story(content_id: str) -> Path:
    matches = sorted(Path('content').glob(f'{content_id}-*'))
    if not matches:
        raise SystemExit(f'No story directory for {content_id}')
    return matches[0]


def download(url: str, target: Path) -> None:
    req = urllib.request.Request(url, headers={'User-Agent': 'ContentFactory/1.0'})
    with urllib.request.urlopen(req, timeout=45) as r:
        target.write_bytes(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    args = ap.parse_args()
    story = find_story(args.id)
    board = json.loads((story / 'storyboard.json').read_text(encoding='utf-8'))
    out = Path('output') / 'visuals' / story.name
    out.mkdir(parents=True, exist_ok=True)

    # Optional free provider. If PEXELS_API_KEY is absent the renderer keeps its
    # deterministic motion-graphics fallback, so CI never depends on the service.
    key = os.getenv('PEXELS_API_KEY', '').strip()
    if not key:
        print('PEXELS_API_KEY unavailable: using motion-graphics fallback')
        return

    for idx, scene in enumerate(board.get('scenes', []), 1):
        query = str(scene.get('visual') or scene.get('caption') or '').strip()
        if not query:
            continue
        endpoint = 'https://api.pexels.com/v1/search?' + urllib.parse.urlencode({
            'query': query, 'orientation': 'portrait', 'per_page': 1
        })
        req = urllib.request.Request(endpoint, headers={'Authorization': key})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode('utf-8'))
            photos = data.get('photos') or []
            if not photos:
                continue
            src = photos[0].get('src', {})
            url = src.get('portrait') or src.get('large2x') or src.get('large')
            if url:
                download(url, out / f'{idx:02}.jpg')
                print(f'downloaded scene {idx}')
        except Exception as exc:
            print(f'scene {idx} visual skipped: {exc}')


if __name__ == '__main__':
    main()
