#!/usr/bin/env python3
import argparse, json, os, pathlib, re, time
from huggingface_hub import InferenceClient
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]

def find_story(content_id):
    m=sorted((ROOT/'content').glob(f'{content_id}-*'))
    if not m: raise SystemExit(f'Unknown content id: {content_id}')
    return m[0]

def clean_paragraphs(text):
    return [re.sub(r'\s+',' ',p).strip() for p in re.split(r'\n\s*\n',text) if p.strip()]

def normalize_for_renderer(image):
    w,h=image.size
    if h <= w:
        raise RuntimeError(f'FLUX returned non-portrait image: {w}x{h}')
    min_w,min_h=900,1400
    if w>=min_w and h>=min_h:
        return image
    scale=max(min_w/w,min_h/h)
    nw=max(min_w,round(w*scale)); nh=max(min_h,round(h*scale))
    return image.resize((nw,nh),Image.Resampling.LANCZOS)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--id',required=True); a=ap.parse_args()
    token=os.getenv('HF_TOKEN','').strip()
    if not token: raise SystemExit('HF_TOKEN is required')
    story=find_story(a.id); slug=story.name
    paragraphs=clean_paragraphs((story/'script_ar.txt').read_text(encoding='utf-8'))
    if len(paragraphs)<6: raise SystemExit('Need at least 6 narration paragraphs')
    out=ROOT/'assets'/'stories'/slug/'scenes'; out.mkdir(parents=True,exist_ok=True)
    model=os.getenv('IMAGE_MODEL','black-forest-labs/FLUX.1-schnell')
    client=InferenceClient(provider='auto',api_key=token)
    for i,narration in enumerate(paragraphs,1):
        dest=out/f'{i:02d}.png'
        if dest.exists(): print('KEEP',dest); continue
        prompt=(f'ONE independent vertical 9:16 cinematic master frame for a premium technology documentary. Story: {slug}. Scene {i}. '
                f'Narration context: {narration}. Create a literal historically believable visual using recognizable real-world objects, people, period-correct environments and technology. '
                'Photorealistic premium documentary cinematography, dramatic practical lighting, shallow depth of field, natural skin and materials, subtle film grain, rich dynamic range, strong foreground/background separation, centered portrait-safe composition. '
                'For this Apple Newton story use authentic early-to-late 1990s atmosphere and pen-computing context where appropriate. '
                'ABSOLUTELY NO visible text, letters, numbers, captions, subtitles, UI labels, timestamps, added logos, watermarks, collage, grid, storyboard panels, presentation slides or decorative typography.')
        print(f'FLUX GENERATE {i}/{len(paragraphs)}')
        image=client.text_to_image(prompt,model=model,width=768,height=1360,num_inference_steps=4)
        original=image.size
        image=normalize_for_renderer(image)
        image.save(dest,'PNG',optimize=True)
        print(f'SAVED {dest} original={original[0]}x{original[1]} normalized={image.size[0]}x{image.size[1]}')
        time.sleep(1)
    manifest={'architecture':'V3_GOLDEN_STRICT','story':slug,'source':'independent_flux_generation','model':model,'scene_count':len(list(out.glob('*.png'))),'image_text_allowed':False,'target_frame':'1080x1920_9x16','renderer_normalization':'portrait_upscale_only_no_stretch'}
    (out.parent/'masters-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__': main()
