from pathlib import Path
import argparse
import asyncio
import edge_tts

VOICE = 'ar-SA-HamedNeural'

async def generate(content_id: str) -> None:
    matches = sorted(Path('content').glob(f'{content_id}-*/script_ar.txt'))
    if not matches:
        raise SystemExit(f'No Arabic script found for content id {content_id}')
    script = matches[0]
    slug = script.parent.name
    output = Path('output') / f'{slug}-voice.mp3'
    output.parent.mkdir(parents=True, exist_ok=True)
    text = script.read_text(encoding='utf-8').strip()
    await edge_tts.Communicate(text=text, voice=VOICE, rate='+8%', pitch='-2Hz').save(str(output))
    print(output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    asyncio.run(generate(args.id))
