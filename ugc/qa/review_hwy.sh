#!/bin/bash
# review_hwy.sh <video.mp4> <outdir> : sheets vs approved v1c + reaction crops + talking strips + whisper transcript
set -e
V="$1"; O="$2"; REF=~/masonry-tools/insta/ig_in/highway_yui_v/v1c.mp4; mkdir -p "$O"
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of compact "$V"
ffmpeg -nostats -i "$V" -vn -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
ffmpeg -v error -y -i "$REF" -i "$V" -filter_complex "[0:v]fps=0.5,scale=200:-1[a];[1:v]fps=0.5,scale=200:-1[b];[a][b]hstack,pad=iw+8:ih+8:4:4:white,tile=7x2" "$O/pair_%02d.jpg"
ffmpeg -v error -y -i "$V" -vf "fps=1,crop=330:360:750:330,scale=165:-1,tile=14x4" -frames:v 1 "$O/pip.jpg"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
ffmpeg -v error -y -ss 56 -i "$V" -vf "fps=1,crop=1080:1350:0:300,scale=200:-1,tile=12x4" -frames:v 1 "$O/second_half.jpg"
ffmpeg -v error -y -i "$V" -vn -ac 1 -ar 16000 "$O/a.wav"
whisper "$O/a.wav" --model small --language ja --condition_on_previous_text False --output_format txt --output_dir "$O" >/dev/null 2>&1
cat "$O/a.txt"
