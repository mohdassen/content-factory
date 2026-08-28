# Content Factory — AI-first architecture

Status: ADOPTED — V3 GOLDEN TEMPLATE

## Production principle
The visual source of truth is a curated set of AI-generated cinematic keyframes created specifically for each story. Stock imagery is fallback only and must never define the final look.

V3 is the approved baseline: **every scene is generated as its own independent vertical master image**. Composite storyboards/contact sheets are planning/QC artifacts only and are never used as video source material.

## Golden pipeline
1. Research and fact-check story.
2. Write Arabic short-form script and hook.
3. Split narration into semantic sentences/beats and build a scene plan.
4. Generate one independent cinematic AI master for every scene:
   - vertical 9:16;
   - no captions, scene numbers, timestamps, storyboard borders or debug text baked into the image;
   - consistent art direction and recurring presenter/brand when appropriate;
   - preferred source resolution >= 1080x1920; never stretch a lower-resolution source.
5. Store approved masters under `assets/stories/<slug>/scenes/` using `01.png`, `02.png`, etc.
6. Generate narration and capture real word/sentence timing metadata.
7. Bind each scene change to the matching narration sentence/beat rather than fixed arbitrary durations.
8. Render at 1080x1920 without stretching. Use aspect-preserving scale/crop only.
9. Add captions after render as a separate ASS/subtitle layer. Captions are never part of the generated image.
10. Apply cinematic motion/transition/color treatment.
11. Run technical QC and visual QC/contact-sheet review.
12. Telegram receives only QC-passed publish-ready output.

## Asset priority
1. Approved AI-generated independent story scene
2. Approved factual/archive visual when licensing permits
3. Curated stock visual
4. Motion-graphics fallback for short connective scenes only

## Cinematic treatment
- Use varied camera motion per scene rather than one repeated zoom: slow push-in, pull-out, lateral drift, reveal and restrained parallax-style movement.
- Transitions are normally 250–450 ms. Prefer subtle cross-dissolve/film-fade; use hard cuts only for deliberate dramatic beats.
- Apply restrained contrast, saturation and local sharpness; avoid crushing shadows or oversaturation.
- Add subtle vignette/film grain only when it improves the scene; never degrade image detail.
- The first 1–2 seconds need the strongest visual hook and the fastest visual commitment.
- Scene changes typically follow narration phrase boundaries, usually every 3–7 seconds.
- Brand/logo remains small and consistent; it must not compete with the story.
- Final narration is leveled consistently and remains dominant over any ambience/music.

## Caption rules
- Captions are a separate ASS layer rendered after scene composition.
- Arabic font: Noto Sans Arabic (or approved brand Arabic font).
- Maximum two lines in the lower safe zone.
- Usually 5–9 Arabic words per beat depending on sentence rhythm.
- Important words may receive restrained emphasis, but never giant kinetic text that covers the subject.
- No permanent large black subtitle panel.

## Visual rules
- Final output: 1080x1920 / 9:16.
- Main visual occupies the full frame.
- No stretch, no distorted aspect ratio and no zoom large enough to expose source softness.
- Do not burn storyboard/debug IDs, timestamps or scene numbering into final output.
- Avoid repeated compositions in consecutive scenes.
- Recurring presenter character must retain consistent appearance across episodes.

## QC policy
`PASS` is not only codec/duration. Publish-ready QC requires:
- expected independent scene assets exist;
- no composite storyboard is being used as a primary visual;
- no blank/near-black primary scenes;
- source aspect ratio and final framing are valid;
- no visible stretch/distortion or excessive upscaling;
- subtitle safe-zone compliance;
- no overlapping/baked-in debug text layers;
- narration audio exists and scene changes align to narration beats;
- 9:16 H.264/AAC output;
- platform duration target met;
- a visual contact sheet is produced and reviewed before delivery.

## Automation boundary
AI image generation/approval is the creative stage. GitHub Actions is the deterministic production stage. The renderer must consume approved independent masters and must never replace missing primary assets with a low-quality fallback while still calling the result publish-ready.
