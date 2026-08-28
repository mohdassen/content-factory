from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def find_story(content_id: str) -> Path:
    matches = sorted(Path('content').glob(f'{content_id}-*'))
    if not matches:
        raise SystemExit(f'No story directory found for id={content_id}')
    return matches[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    args = ap.parse_args()

    story = find_story(args.id)
    query_path = story / 'library_query.json'
    manifest_path = Path('assets/library/manifest.json')
    if not query_path.exists():
        raise SystemExit(f'Missing library query: {query_path}')
    if not manifest_path.exists():
        raise SystemExit('Missing permanent asset library manifest')

    query = json.loads(query_path.read_text(encoding='utf-8'))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    items = manifest.get('items') or []

    topic = query.get('topic')
    labels = query.get('labels') or []
    count = int(query.get('scene_count') or len(labels) or 8)

    pool = [x for x in items if x.get('topic') == topic and x.get('text_free') is True and x.get('logo_free') is True]
    if labels:
        by_label = {x.get('label'): x for x in pool}
        selected = []
        for label in labels:
            item = by_label.get(label)
            if not item:
                raise SystemExit(f'Library asset missing for label={label!r}, topic={topic!r}')
            selected.append(item)
    else:
        selected = pool[:count]

    if len(selected) < count:
        raise SystemExit(f'Not enough library assets for topic={topic!r}: need {count}, found {len(selected)}')
    selected = selected[:count]

    dst = Path('assets/stories') / story.name / 'scenes'
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    staged = []
    for idx, item in enumerate(selected, start=1):
        src = Path(item['path'])
        if not src.exists():
            raise SystemExit(f'Library file missing: {src}')
        out = dst / f'{idx:02d}{src.suffix.lower()}'
        shutil.copy2(src, out)
        staged.append({'scene': idx, 'asset_id': item['id'], 'source': item['path'], 'staged': out.as_posix()})

    result = {
        'source': 'PERMANENT_GITHUB_ASSET_LIBRARY',
        'story': story.name,
        'topic': topic,
        'scene_count': len(staged),
        'assets': staged,
    }
    out_manifest = dst.parent / 'library-selection.json'
    out_manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
