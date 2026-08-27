from pathlib import Path
import asyncio
import edge_tts

SCRIPT = Path('content/001-netflix-blockbuster/script_ar.txt')
OUTPUT = Path('output/001-netflix-blockbuster-voice.mp3')
VOICE = 'ar-SA-HamedNeural'

async def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = SCRIPT.read_text(encoding='utf-8').strip()
    communicate = edge_tts.Communicate(text=text, voice=VOICE, rate='+8%', pitch='-2Hz')
    await communicate.save(str(OUTPUT))

if __name__ == '__main__':
    asyncio.run(main())
