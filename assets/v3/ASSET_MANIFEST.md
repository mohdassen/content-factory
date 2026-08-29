# Content Factory V3 — 3D Asset Manifest

V3 replaces procedural primitive humans/props with reusable licensed 3D assets.

## Approved source policy

- Prefer **CC0** assets for the permanent library.
- Commercial use must be explicitly allowed.
- Never redistribute paid/restricted source assets in this repository.
- Keep source URL + license next to every imported asset.

## Initial character source

### Quaternius — Universal Base Characters
- Source: https://quaternius.com/packs/universalbasecharacters.html
- License: CC0
- Formats: FBX / OBJ / glTF; source edition also provides Blender files.
- Purpose: base male/female humanoids with animation-friendly humanoid rig.

### Quaternius — Universal Animation Library
- Source: https://quaternius.com/
- License: CC0
- Purpose: locomotion / idle / gesture animation pool for retargeting.

## Optional animation source

### Adobe Mixamo
- Source: https://www.mixamo.com/
- Commercial films are allowed under Adobe's Mixamo terms.
- Do not redistribute downloaded character/animation source files publicly.
- Use only when automated acquisition/credential handling is solved.

## V3 local asset contract

The Blender builder discovers files from:

```text
assets/v3/
  characters/
    *.fbx | *.glb | *.gltf
  animations/
    *.fbx | *.glb | *.gltf
  environment/
    *.fbx | *.glb | *.gltf | *.blend
  props/
    *.fbx | *.glb | *.gltf | *.blend
```

Each production asset must have a neighboring `.license.txt` file containing source URL and license.

## First V3 target

Five-second vertical cinematic shot in a year-2000 American video rental store:
- 3 rigged customers
- 1 employee
- browsing/walking/idle motion
- shelves, cases, counter and practical lighting
- 9:16 cinematic dolly camera
- no text, branding, narration or captions
