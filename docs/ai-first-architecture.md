# Content Factory — AI-first architecture

Status: ADOPTED

## Production principle
The visual source of truth is a curated set of AI-generated cinematic keyframes created specifically for each story. Stock imagery is fallback only and must never define the final look.

## Pipeline
1. Research and fact-check story.
2. Write Arabic short-form script and hook.
3. Build scene plan (6–10 scenes, 2–7 seconds each).
4. Generate high-quality 9:16 AI keyframes with a consistent art direction and recurring presenter/brand when appropriate.
5. Store approved scene assets under `assets/stories/<slug>/scenes/` using `01.png`, `02.png`, etc.
6. GitHub Actions renders motion from those assets: Ken Burns, pan/zoom, parallax-style layers where available, transitions, narration, subtitles, logo/brand treatment and progress treatment.
7. QC checks technical validity plus visual-asset coverage. A publish-ready video must not silently degrade into an empty/static fallback.
8. Telegram receives only QC-passed publish-ready output.

## Asset priority
1. Approved AI-generated story scene
2. Approved factual/archive visual when licensing permits
3. Curated stock visual
4. Motion-graphics fallback for short connective scenes only

## Visual rules
- 1080x1920 / 9:16.
- Main visual occupies the full frame.
- No large permanent black subtitle box.
- Captions: max ~5–7 Arabic words per beat, lower safe zone, maximum two lines.
- Do not burn storyboard/debug IDs into final output.
- Avoid repeating the same composition in consecutive scenes.
- First 1–2 seconds must contain a strong visual hook.
- Scene changes typically every 2–5 seconds.
- Brand/logo is subtle and consistent.
- Recurring presenter character must retain consistent appearance across episodes.

## QC policy
`PASS` is not only codec/duration. Final QC should also require:
- expected scene assets exist;
- no blank/near-black primary scenes;
- subtitle safe-zone compliance;
- no overlapping text layers;
- narration audio exists;
- 9:16 H.264/AAC output;
- platform duration target met.

## Automation boundary
AI image generation/approval is the creative stage. GitHub Actions is the deterministic production stage. The renderer must consume approved assets and must not replace missing primary assets with low-quality output while still calling the result publish-ready.
