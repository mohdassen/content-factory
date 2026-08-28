from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

FPS = 24
WIDTH = 1080
HEIGHT = 1920


def find_story(content_id: str) -> Path:
    matches = sorted(Path('content').glob(f'{content_id}-*'))
    if not matches:
        raise SystemExit(f'No story directory found for id={content_id}')
    return matches[0]


def run_text(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60).stdout.strip()


def run_ffmpeg(cmd: list[str], stage: str, log_dir: Path, timeout: int = 300) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f'{stage}.log'
    with log_file.open('w', encoding='utf-8') as log:
        log.write('COMMAND:\n' + ' '.join(cmd) + '\n\n')
        log.flush()
        try:
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            log.write(f'\nTIMEOUT after {timeout}s\n')
            raise SystemExit(f'FFmpeg timeout in stage {stage}; see {log_file}')
    if proc.returncode != 0:
        raise SystemExit(f'FFmpeg failed in stage {stage} rc={proc.returncode}; see {log_file}')


def probe_duration(media: Path) -> float:
    return float(run_text(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(media)]))


def probe_dimensions(image: Path) -> tuple[int, int]:
    raw = run_text(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', str(image)])
    w, h = raw.split('x')
    return int(w), int(h)


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, centi = divmod(rem, 100)
    return f'{h}:{m:02}:{s:02}.{centi:02}'


def load_timing(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        raise SystemExit('STRICT V3 requires narration timing metadata.')
    data = json.loads(path.read_text(encoding='utf-8'))
    words = data.get('words') or []
    if not words:
        raise SystemExit('STRICT V3 requires non-empty narration timing metadata.')
    return words, str(data.get('timing_source') or 'REAL_WORD_BOUNDARIES')


def scene_plan(story: Path, words: list[dict], duration: float) -> list[dict]:
    board = story / 'storyboard.json'
    if board.exists():
        scenes = json.loads(board.read_text(encoding='utf-8')).get('scenes') or []
        if scenes and all(int(s.get('narration_end_word', 0)) > 0 for s in scenes[:-1]):
            boundaries = [0.0]
            previous_word = 0
            for idx, scene in enumerate(scenes[:-1], 1):
                end_word = int(scene['narration_end_word'])
                if end_word <= previous_word or end_word > len(words):
                    raise SystemExit(f'Invalid narration_end_word in scene {idx:02}.')
                boundaries.append(float(words[end_word - 1]['end']))
                previous_word = end_word
            boundaries.append(duration)
            return [{'start': boundaries[i], 'end': boundaries[i + 1]} for i in range(len(boundaries) - 1)]
    paragraphs = [p.strip() for p in story.joinpath('script_ar.txt').read_text(encoding='utf-8').split('\n\n') if p.strip()]
    if len(paragraphs) < 2:
        raise SystemExit('STRICT V3 requires multiple narration paragraphs or an authored storyboard.')
    token_counts = [max(1, len(p.split())) for p in paragraphs]
    total_tokens = sum(token_counts)
    boundaries = [0.0]
    running = 0
    for count in token_counts[:-1]:
        running += count
        word_idx = min(len(words) - 1, max(0, round(running / total_tokens * len(words)) - 1))
        boundaries.append(float(words[word_idx]['end']))
    boundaries.append(duration)
    return [{'start': boundaries[i], 'end': boundaries[i + 1]} for i in range(len(boundaries) - 1)]


def chunks_from_words(words: list[dict], max_words: int = 7) -> list[dict]:
    rows = []
    for i in range(0, len(words), max_words):
        group = words[i:i + max_words]
        if group:
            rows.append({'start': float(group[0]['start']), 'end': float(group[-1]['end']), 'text': ' '.join(str(w['text']) for w in group)})
    return rows


def write_ass(words: list[dict], path: Path) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Arabic,Noto Sans Arabic,54,&H00FFFFFF,&H00FFFFFF,&HCC000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,90,90,235,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for row in chunks_from_words(words):
        text = str(row['text']).replace('\n', r'\N').replace('{', r'\{').replace('}', r'\}')
        events.append(f"Dialogue: 0,{ass_time(row['start'])},{ass_time(row['end'])},Arabic,,0,0,0,,{text}")
    path.write_text(header + '\n'.join(events) + '\n', encoding='utf-8')


def strict_master(slug: str, idx: int) -> Path:
    root = Path('assets') / 'stories' / slug / 'scenes'
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        candidate = root / f'{idx:02}.{ext}'
        if candidate.exists():
            return candidate
    raise SystemExit(f'BLOCKED: independent V3 master missing for scene {idx:02} in {root}.')


def validate_master(image: Path) -> tuple[int, int]:
    w, h = probe_dimensions(image)
    if w < 900 or h < 1400 or h <= w:
        raise SystemExit(f'BLOCKED: {image} is not a sufficiently large portrait master ({w}x{h}).')
    return w, h


def make_background(slug: str, scenes: list[dict], output: Path, log_dir: Path) -> tuple[Path, list[dict]]:
    seg_dir = output / f'{slug}-segments'
    seg_dir.mkdir(parents=True, exist_ok=True)
    files, visual_meta = [], []
    for idx, scene in enumerate(scenes, 1):
        length = max(0.35, float(scene['end']) - float(scene['start']))
        image = strict_master(slug, idx)
        w, h = validate_master(image)
        segment = seg_dir / f'{idx:02}.mp4'
        vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},format=yuv420p"
        run_ffmpeg(['ffmpeg','-nostdin','-y','-hide_banner','-loglevel','warning','-loop','1','-framerate',str(FPS),'-i',str(image),'-t',f'{length:.3f}','-vf',vf,'-an','-c:v','libx264','-preset','ultrafast','-crf','21','-r',str(FPS),'-pix_fmt','yuv420p',str(segment)], f'segment-{idx:02}', log_dir, timeout=90)
        files.append(segment)
        visual_meta.append({'scene':idx,'master':str(image),'source_width':w,'source_height':h,'fit':'aspect_preserved_center_crop'})
    concat = seg_dir / 'concat.txt'
    concat.write_text('\n'.join(f"file '{p.resolve()}'" for p in files), encoding='utf-8')
    bg = output / f'{slug}-background.mp4'
    run_ffmpeg(['ffmpeg','-nostdin','-y','-hide_banner','-loglevel','warning','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(bg)], 'concat', log_dir, timeout=60)
    return bg, visual_meta


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument('--id',required=True); args=ap.parse_args()
    story=find_story(args.id); slug=story.name
    output=Path('output'); output.mkdir(exist_ok=True)
    log_dir=output/'diagnostics'/slug; log_dir.mkdir(parents=True,exist_ok=True)
    voice=output/f'{slug}-voice.mp3'; timing=output/f'{slug}-word-boundaries.json'; logo=Path('assets')/'brand'/'logo.png'
    if not voice.exists(): raise SystemExit('Missing narration audio.')
    if not logo.exists(): raise SystemExit('STRICT V3 requires the stable PNG brand logo asset.')
    probe_dimensions(logo)
    duration=probe_duration(voice); words,timing_source=load_timing(timing); scenes=scene_plan(story,words,duration)
    subtitle=output/f'{slug}.ass'; write_ass(words,subtitle)
    bg,masters=make_background(slug,scenes,output,log_dir)
    sub=str(subtitle).replace(':',r'\:').replace("'",r"\'")
    out=output/f'{slug}-preview.mp4'
    fc=f"[0:v]subtitles='{sub}'[base];[2:v]scale=150:-1,format=rgba,colorchannelmixer=aa=0.82[lg];[base][lg]overlay=W-w-38:42:shortest=1,format=yuv420p[v]"
    run_ffmpeg(['ffmpeg','-nostdin','-y','-hide_banner','-loglevel','warning','-i',str(bg),'-i',str(voice),'-loop','1','-framerate','1','-i',str(logo),'-filter_complex',fc,'-map','[v]','-map','1:a:0','-t',f'{duration:.3f}','-c:v','libx264','-preset','ultrafast','-crf','22','-threads','0','-c:a','aac','-b:a','128k','-pix_fmt','yuv420p','-movflags','+faststart',str(out)], 'final-compose', log_dir, timeout=420)
    final_duration=probe_duration(out)
    if final_duration < max(1.0,duration-0.75): raise SystemExit(f'Final video unexpectedly short: {final_duration:.3f}s vs narration {duration:.3f}s')
    (output/f'{slug}-render.json').write_text(json.dumps({'slug':slug,'architecture':'V3_GOLDEN_STRICT','renderer_mode':'ROBUST_STAGED_V1','duration':round(final_duration,3),'scene_count':len(scenes),'narration_timing':timing_source,'scene_timing':'NARRATION_PARAGRAPH_ALIGNED','all_visuals_are_approved_masters':True,'brand_name':'خلف الشاشة','brand_logo':str(logo),'brand_logo_position':'top_right','visuals':masters,'forbidden_fallbacks_enabled':False,'diagnostics_dir':str(log_dir)},ensure_ascii=False,indent=2),encoding='utf-8')
    print(out)

if __name__=='__main__': main()
