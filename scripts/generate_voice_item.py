from pathlib import Path
import argparse
import asyncio
import json
import re
import subprocess
import edge_tts

VOICE = 'ar-SA-HamedNeural'


def ticks_to_seconds(value: int | float) -> float:
    return float(value) / 10_000_000.0


def probe_duration(media: Path) -> float:
    raw = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(media)
    ], check=True, capture_output=True, text=True).stdout.strip()
    return float(raw)


def audio_aligned_words(text: str, duration: float) -> list[dict]:
    tokens = re.findall(r'\S+', text)
    if not tokens:
        return []
    # Allocate the measured narration duration proportionally to token length.
    # This fallback preserves sentence/scene sync even when Edge TTS omits WordBoundary events.
    weights = [max(1, len(re.sub(r'[^\w\u0600-\u06FF]', '', t))) for t in tokens]
    total = float(sum(weights))
    cursor = 0.0
    rows = []
    for i, (token, weight) in enumerate(zip(tokens, weights)):
        start = cursor
        end = duration if i == len(tokens) - 1 else cursor + duration * (weight / total)
        rows.append({
            'text': token,
            'start': round(start, 6),
            'end': round(end, 6),
            'duration': round(end - start, 6),
        })
        cursor = end
    return rows


async def generate(content_id: str) -> None:
    matches = sorted(Path('content').glob(f'{content_id}-*/script_ar.txt'))
    if not matches:
        raise SystemExit(f'No Arabic script found for content id {content_id}')

    script = matches[0]
    slug = script.parent.name
    output_dir = Path('output')
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path = output_dir / f'{slug}-voice.mp3'
    timing_path = output_dir / f'{slug}-word-boundaries.json'
    text = script.read_text(encoding='utf-8').strip()

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate='+8%',
        pitch='-2Hz',
    )

    boundaries: list[dict] = []
    with audio_path.open('wb') as audio:
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio.write(chunk['data'])
            elif chunk['type'] == 'WordBoundary':
                start = ticks_to_seconds(chunk['offset'])
                duration = ticks_to_seconds(chunk['duration'])
                boundaries.append({
                    'text': chunk['text'],
                    'start': round(start, 6),
                    'end': round(start + duration, 6),
                    'duration': round(duration, 6),
                })

    duration = probe_duration(audio_path)
    timing_source = 'REAL_WORD_BOUNDARIES'
    if not boundaries:
        boundaries = audio_aligned_words(text, duration)
        timing_source = 'AUDIO_ALIGNED_WORD_TIMING'

    if not boundaries:
        raise SystemExit('Unable to generate narration timing metadata.')

    timing_path.write_text(
        json.dumps(
            {
                'slug': slug,
                'voice': VOICE,
                'timing_source': timing_source,
                'audio_duration': round(duration, 6),
                'words': boundaries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    print(audio_path)
    print(timing_path)
    print(f'timing_source={timing_source}; words={len(boundaries)}; duration={duration:.3f}s')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    asyncio.run(generate(args.id))
