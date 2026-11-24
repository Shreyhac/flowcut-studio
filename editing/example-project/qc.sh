#!/bin/sh
# structure, contrast, layout, cut frames, Instagram's chrome, the SFX bed,
# and whether every B-roll plate is actually moving in the DELIVERED file.
set -e
cd "$(dirname "$0")"
REN="${1:-renders/vid87-v1-mixed.mp4}"
echo "── lint ──";      npx --yes hyperframes@0.7.87 lint     2>&1 | tail -2
echo "── validate ──";  npx --yes hyperframes@0.7.87 validate 2>&1 | tail -1
echo "── inspect ──";   npx --yes hyperframes@0.7.87 inspect  2>&1 | tail -1
echo "── voids ──";     python3 gate_voids.py    | tail -1
echo "── safe zones (preview) ──"; python3 gate_safezone.py preview | tail -1
echo "── audio ──";     python3 gate_audio.py    2>&1 | tail -1
if [ -f "$REN" ]; then
  echo "── safe zones (delivered) ──"; python3 gate_safezone.py qa | tail -1
  echo "── plates live ──";            python3 gate_plates.py "$REN" | tail -1
fi
