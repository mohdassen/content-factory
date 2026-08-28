from __future__ import annotations

import render_item as base


def stronger_cinematic_filter(idx: int, length: float) -> str:
    fps = base.FPS
    width = base.WIDTH
    height = base.HEIGHT
    frames = max(2, int(round(length * fps)))
    denom = max(1, frames - 1)

    # V3.2: deliberately visible motion for mobile viewing.
    # Use a literal frame denominator because FFmpeg zoompan does not expose `d`
    # as an expression variable inside z/x/y on all supported runner builds.
    if idx == 1:
        z = f"min(1.0+0.20*on/{denom},1.20)"
        x = "iw/2-(iw/zoom/2)"
        y = f"ih/2-(ih/zoom/2)-55*on/{denom}"
    elif idx % 4 == 2:
        z = f"min(1.03+0.13*on/{denom},1.16)"
        x = f"iw/2-(iw/zoom/2)-85+170*on/{denom}"
        y = "ih/2-(ih/zoom/2)"
    elif idx % 4 == 3:
        z = f"max(1.02,1.17-0.15*on/{denom})"
        x = "iw/2-(iw/zoom/2)"
        y = f"ih/2-(ih/zoom/2)+55-110*on/{denom}"
    elif idx % 4 == 0:
        z = f"min(1.04+0.11*on/{denom},1.15)"
        x = f"iw/2-(iw/zoom/2)+90-180*on/{denom}"
        y = f"ih/2-(ih/zoom/2)+45-90*on/{denom}"
    else:
        z = f"min(1.02+0.14*on/{denom},1.16)"
        x = "iw/2-(iw/zoom/2)"
        y = f"ih/2-(ih/zoom/2)-60+120*on/{denom}"

    return (
        "scale=1380:2450:force_original_aspect_ratio=increase,"
        "crop=1380:2450,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps},"
        f"trim=duration={length:.3f},setpts=PTS-STARTPTS,"
        "eq=contrast=1.025:saturation=1.035,format=yuv420p"
    )


base.cinematic_filter = stronger_cinematic_filter

if __name__ == '__main__':
    base.main()
