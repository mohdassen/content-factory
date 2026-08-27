from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def find_story(content_id: str) -> Path:
    matches = sorted(Path('content').glob(f'{content_id}-*'))
    if not matches:
        raise SystemExit(f'No story directory found for id={content_id}')
    return matches[0]


def probe_duration(audio: Path) -> float:
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(audio)], check=True, capture_output=True, text=True)
    return float(r.stdout.strip())


def srt_time(seconds: float) -> str:
    ms=int(round(seconds*1000)); h,rem=divmod(ms,3600000); m,rem=divmod(rem,60000); s,milli=divmod(rem,1000)
    return f'{h:02}:{m:02}:{s:02},{milli:03}'


def chunks(text: str, max_words: int = 7) -> list[str]:
    words=text.replace('\n',' ').split(); return [' '.join(words[i:i+max_words]) for i in range(0,len(words),max_words)]


def write_srt(script: str, duration: float, path: Path) -> None:
    parts=chunks(script); weights=[max(1,len(p.split())) for p in parts]; total=sum(weights); cursor=0.0; rows=[]
    for i,(part,w) in enumerate(zip(parts,weights),1):
        seg=duration*w/total; end=min(duration,cursor+seg)
        rows.append(f'{i}\n{srt_time(cursor)} --> {srt_time(end)}\n{part}\n'); cursor=end
    path.write_text('\n'.join(rows),encoding='utf-8')


def load_storyboard(path: Path, duration: float) -> list[dict]:
    try: scenes=json.loads(path.read_text(encoding='utf-8')).get('scenes') or []
    except Exception: scenes=[]
    if not scenes:
        step=duration/6; return [{'start':i*step,'end':min(duration,(i+1)*step)} for i in range(6)]
    authored=max(float(s.get('end',0)) for s in scenes) or duration; scale=duration/authored
    return [{'start':max(0,float(s.get('start',0))*scale),'end':min(duration,float(s.get('end',authored))*scale)} for s in scenes]


def make_background(slug: str, scenes: list[dict], output: Path) -> Path:
    visual_dir=output/'visuals'/slug; seg_dir=output/f'{slug}-segments'; seg_dir.mkdir(parents=True,exist_ok=True); files=[]
    palette=['0x101318','0x151018','0x0d1620','0x151810','0x111221','0x181211']
    for idx,scene in enumerate(scenes,1):
        length=max(.25,scene['end']-scene['start']); image=visual_dir/f'{idx:02}.jpg'; segment=seg_dir/f'{idx:02}.mp4'
        if image.exists():
            zoom="min(zoom+0.0007,1.10)"
            vf=f"scale=1280:2276:force_original_aspect_ratio=increase,crop=1280:2276,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,eq=contrast=1.04:saturation=.9:brightness=-.04,drawbox=x=0:y=0:w=iw:h=ih:color=black@.24:t=fill,format=yuv420p"
            cmd=['ffmpeg','-y','-loop','1','-i',str(image),'-t',f'{length:.3f}','-vf',vf,'-an','-c:v','libx264','-preset','ultrafast','-crf','24','-r','30',str(segment)]
        else:
            vf="drawgrid=width=160:height=160:thickness=2:color=white@0.018,format=yuv420p"
            cmd=['ffmpeg','-y','-f','lavfi','-i',f'color=c={palette[(idx-1)%len(palette)]}:s=1080x1920:d={length:.3f}:r=30','-vf',vf,'-an','-c:v','libx264','-preset','ultrafast','-crf','25',str(segment)]
        subprocess.run(cmd,check=True); files.append(segment)
    concat=seg_dir/'concat.txt'; concat.write_text('\n'.join(f"file '{p.resolve()}'" for p in files),encoding='utf-8')
    bg=output/f'{slug}-background.mp4'; subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(bg)],check=True); return bg


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument('--id',required=True); args=ap.parse_args()
    story=find_story(args.id); slug=story.name; voice=Path('output')/f'{slug}-voice.mp3'; script=story/'script_ar.txt'
    if not voice.exists() or not script.exists(): raise SystemExit('Missing script or voice')
    output=Path('output'); output.mkdir(exist_ok=True); duration=probe_duration(voice)
    subtitle=output/f'{slug}.srt'; write_srt(script.read_text(encoding='utf-8').strip(),duration,subtitle)
    scenes=load_storyboard(story/'storyboard.json',duration); bg=make_background(slug,scenes,output)
    sub=str(subtitle).replace(':',r'\:').replace("'",r"\'")

    # One typography layer only. The previous renderer displayed storyboard captions
    # and narration subtitles simultaneously, producing the overlapping Arabic seen
    # in previews. Keep short narration captions in a dedicated safe zone.
    vf=(
      "scale=1080:1920,"
      "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.06:t=fill,"
      "drawbox=x=44:y=70:w=992:h=1780:color=white@0.07:t=3,"
      "drawbox=x=58:y=1450:w=964:h=330:color=black@0.62:t=fill,"
      f"subtitles='{sub}':force_style='FontName=DejaVu Sans,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginL=90,MarginR=90,MarginV=205',"
      f"drawbox=x=58:y=1815:w='964*t/{duration:.6f}':h=7:color=white@0.70:t=fill"
    )
    out=output/f'{slug}-preview.mp4'
    subprocess.run(['ffmpeg','-y','-i',str(bg),'-i',str(voice),'-vf',vf,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','160k','-shortest','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
    print(out)

if __name__=='__main__': main()
