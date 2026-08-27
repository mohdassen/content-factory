#!/usr/bin/env bash
set -euo pipefail

mkdir -p output
VOICE="output/001-netflix-blockbuster-voice.mp3"
OUT="output/001-netflix-blockbuster-preview.mp4"

DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VOICE")

ffmpeg -y \
  -f lavfi -i "color=c=0x0b0d12:s=1080x1920:d=${DURATION}:r=30" \
  -i "$VOICE" \
  -filter_complex "[0:v]
    drawbox=x='mod(t*90\,1080)-220':y=180:w=420:h=10:color=white@0.18:t=fill,
    drawbox=x='1080-mod(t*70\,1250)':y=1510:w=520:h=12:color=white@0.12:t=fill,
    drawbox=x=90:y=120:w=900:h=1480:color=black@0.12:t=fill,
    subtitles=content/001-netflix-blockbuster/captions.srt:force_style='FontName=DejaVu Sans,FontSize=54,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H55000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=230'[v]" \
  -map "[v]" -map 1:a \
  -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -shortest -movflags +faststart "$OUT"

ffprobe -v error -show_entries format=duration:stream=width,height,codec_name -of default=noprint_wrappers=1 "$OUT"
