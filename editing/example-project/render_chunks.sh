#!/bin/sh
# render every chunk with a fresh single-worker process, verify frame counts,
# stream-copy concat into renders/vid87-<take>.mp4 (video only; audio is muxed
# once by build_mix.py).  Refuses a chunk whose source stamp is stale.
set -e
cd "$(dirname "$0")"
TAKE=$(python3 -c "import json;print(json.load(open('chunks/manifest.json'))['take'])")
STAMP=$(python3 -c "import hashlib;print(hashlib.sha256(open('index.html','rb').read()).hexdigest()[:16])")
mkdir -p renders/chunks
: > renders/chunks/list.txt
for c in chunks/c*/; do
  n=$(basename "$c"); [ "$(cat $c/.source-hash)" = "$STAMP" ] || { echo "$n is STALE"; exit 1; }
  want=$(python3 -c "import json;print(json.load(open('$c/chunk.json'))['frames'])")
  out="$PWD/renders/chunks/$n.mp4"
  CH=$(python3 -c "import hashlib;print(hashlib.sha256(open('$c/index.html','rb').read()).hexdigest()[:16])")
  if [ -s "$out" ] && [ "$(cat $c/.rendered-hash 2>/dev/null)" = "$CH" ]; then echo "$n cached"; else
    rm -f "$out"; echo "── $n ($want frames) ──"
    ( cd "$c" && npx --yes hyperframes@0.7.87 render -q high -f 30 --video-bitrate 36M --no-low-memory-mode -w 1 -o "$out" > render.log 2>&1 ) || { echo "$n FAILED"; LC_ALL=C tail -c 1500 $c/render.log | LC_ALL=C tr '\r' '\n' | grep -aiE "stalled|error|fail" | tail -3; exit 1; }
    echo "$CH" > $c/.rendered-hash
  fi
  got=$(ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of csv=p=0 "$out")
  [ "$got" = "$want" ] || { echo "$n has $got frames, wanted $want"; exit 1; }
  echo "file '$out'" >> renders/chunks/list.txt
done
ffmpeg -y -v error -f concat -safe 0 -i renders/chunks/list.txt -c copy -an "renders/vid87-$TAKE.mp4"
ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames,width,height,bit_rate -of csv=p=0 "renders/vid87-$TAKE.mp4"
echo "CHUNKS_DONE $TAKE"
