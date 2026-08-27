#!/usr/bin/env bash
set -euo pipefail

mkdir -p output

ffmpeg -y \
  -f lavfi -i "color=c=0x111111:s=1080x1920:d=55:r=30" \
  -vf "subtitles=content/001-netflix-blockbuster/captions.srt:force_style='FontName=DejaVu Sans,FontSize=56,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=220'" \
  -c:v libx264 -preset veryfast -pix_fmt yuv420p \
  -movflags +faststart \
  output/001-netflix-blockbuster-tech-preview.mp4

ffprobe -v error -show_entries format=duration:stream=width,height,codec_name -of default=noprint_wrappers=1 output/001-netflix-blockbuster-tech-preview.mp4
