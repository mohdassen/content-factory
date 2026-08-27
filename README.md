# Content Factory

AI-assisted short-form content production system focused on original Arabic-first stories about money, business, technology, AI, rise-and-fall stories, and Saudi/Gulf opportunities.

## V1 Goal

One command should turn an approved idea into a production package:

`Idea -> Research -> Score -> Script -> Storyboard -> Voice plan -> Visual plan -> Captions -> Render manifest -> QC`

The initial version deliberately separates factual research and creative writing so that unsupported claims do not flow directly into production.

## Project principles

- Original, non-repetitive content.
- Source-backed factual claims.
- Strong hook in the first 1-2 seconds.
- Vertical 9:16 output planning.
- Arabic-first, reusable for multilingual expansion.
- Analytics-driven iteration instead of template spam.

## Local quick start

```bash
python -m src.main --demo
```

No paid API is required for the deterministic demo pipeline. AI providers and rendering integrations are added as adapters.
