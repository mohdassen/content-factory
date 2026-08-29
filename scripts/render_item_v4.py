from __future__ import annotations

from pathlib import Path

import render_item as base

# V4 production defaults
base.FPS = 30
base.WIDTH = 1080
base.HEIGHT = 1920
base.OUTRO_DURATION = 1.6


def v4_cinematic_filter(idx: int, length: float) -> str:
    fps, width, height = base.FPS, base.WIDTH, base.HEIGHT
    frames = max(2, int(round(length * fps)))
    denom = max(1, frames - 1)

    # Purposeful motion: stronger hook, restrained documentary motion afterward.
    if idx == 1:
        z = f"min(1.02+0.10*on/{denom},1.12)"
        x = "iw/2-(iw/zoom/2)"
        y = f"ih/2-(ih/zoom/2)-40*on/{denom}"
    elif idx % 4 == 2:
        z = f"min(1.025+0.055*on/{denom},1.08)"
        x = f"iw/2-(iw/zoom/2)-45+90*on/{denom}"
        y = "ih/2-(ih/zoom/2)"
    elif idx % 4 == 3:
        z = f"max(1.025,1.075-0.045*on/{denom})"
        x = "iw/2-(iw/zoom/2)"
        y = f"ih/2-(ih/zoom/2)+32-64*on/{denom}"
    elif idx % 4 == 0:
        z = f"min(1.02+0.05*on/{denom},1.07)"
        x = f"iw/2-(iw/zoom/2)+50-100*on/{denom}"
        y = f"ih/2-(ih/zoom/2)+20-40*on/{denom}"
    else:
        z = f"min(1.02+0.045*on/{denom},1.065)"
        x = "iw/2-(iw/zoom/2)"
        y = f"ih/2-(ih/zoom/2)-30+60*on/{denom}"

    return (
        "scale=1240:2205:force_original_aspect_ratio=increase,"
        "crop=1240:2205,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps},"
        f"trim=duration={length:.3f},setpts=PTS-STARTPTS,"
        "eq=contrast=1.055:saturation=1.03:brightness=-0.018,"
        "vignette=PI/7,format=yuv420p"
    )


def v4_write_ass(words: list[dict], path: Path) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Arabic,Noto Sans Arabic,68,&H00FFFFFF,&H00FFFFFF,&HC8000000,&H60000000,-1,0,0,0,100,100,0,0,1,5,1,2,105,105,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    # Shorter chunks are easier to read on mobile and feel more kinetic.
    for row in base.chunks_from_words(words, max_words=5):
        text = str(row['text']).replace('\n', r'\N').replace('{', r'\{').replace('}', r'\}')
        events.append(f"Dialogue: 0,{base.ass_time(row['start'])},{base.ass_time(row['end'])},Arabic,,0,0,0,,{text}")
    path.write_text(header + '\n'.join(events) + '\n', encoding='utf-8')


base.cinematic_filter = v4_cinematic_filter
base.write_ass = v4_write_ass

if __name__ == '__main__':
    base.main()
