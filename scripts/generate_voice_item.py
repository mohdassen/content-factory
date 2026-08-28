from pathlib import Path
import argparse
import asyncio
import json
import edge_tts

VOICE = 'ar-SA-HamedNeural'


def ticks_to_seconds(value: int | float) -> float:
    # Edge TTS timing values are 100-nanosecond ticks.
    return float(value) / 10_000_000.0


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

    timing_path.write_text(
        json.dumps(
            {
                'slug': slug,
                'voice': VOICE,
                'words': boundaries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    print(audio_path)
    print(timing_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    asyncio.run(generate(args.id))
