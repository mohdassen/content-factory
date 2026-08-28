from __future__ import annotations

import render_item as base


def stronger_cinematic_filter(idx: int, length: float) -> str:
    fps = base.FPS
    width = base.WIDTH
    height = base.HEIGHT
    frames = max(2, int(round(length * fps)))

    # V3.2: deliberately visible motion for mobile viewing.
    # Motion remains smooth and image-based; narration, subtitles, outro and QC are untouched.
    if idx == 1:
        # Strong hook push-in with a mild upward drift.
        z = "min(1.0+0.20*on/max(1,d-1),1.20)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)-55*on/max(1,d-1)"
    elif idx % 4 == 2:
        # Left-to-right cinematic pan while pushing in.
        z = "min(1.03+0.13*on/max(1,d-1),1.16)"
        x = "iw/2-(iw/zoom/2)-85+170*on/max(1,d-1)"
        y = "ih/2-(ih/zoom/2)"
    elif idx % 4 == 3:
        # Pull-back for rhythm change.
        z = "max(1.02,1.17-0.15*on/max(1,d-1))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)+55-110*on/max(1,d-1)"
    elif idx % 4 == 0:
        # Right-to-left diagonal movement.
        z = "min(1.04+0.11*on/max(1,d-1),1.15)"
        x = "iw/2-(iw/zoom/2)+90-180*on/max(1,d-1)"
        y = "ih/2-(ih/zoom/2)+45-90*on/max(1,d-1)"
    else:
        # Slow dramatic push with vertical drift.
        z = "min(1.02+0.14*on/max(1,d-1),1.16)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)-60+120*on/max(1,d-1)"

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
