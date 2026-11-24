#!/usr/bin/env python3
"""Every scene's FIRST frame must already carry ink in the art band.

A cut that lands on blank paper is a void, and it is invisible to lint,
validate and inspect because every element in the scene is individually
correct — it just has not entered yet.  vid79 shipped five of them in one
pass, all from `opacity:0` entrances on the scene's own furniture.

Run after preview_frames.py.
"""
import glob, os, re, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CUTS = [("s00", 0.000), ("s01", 1.710), ("s02", 2.760), ("s03", 3.780), ("s04", 5.030),
        ("s05", 5.860), ("s06", 7.230), ("s07", 9.130), ("s08", 11.290), ("s09", 12.620),
        ("s10", 13.660), ("s11", 15.170)]
FLOOR = 1.5      # per cent of the art band that must be ink

frames = sorted(glob.glob(os.path.join(HERE, "preview", "*.png")))
if not frames:
    sys.exit("gate_voids: no preview frames — run preview_frames.py first")
times = [(float(re.search(r"/(\d+\.\d+)_", f).group(1)), f) for f in frames]

bad = []
for name, t in CUTS:
    f = min(times, key=lambda tf: abs(tf[0] - t))[1]
    im = np.array(Image.open(f).convert("L")).astype(int)
    # s00a is his face at full frame: its "art" is the cover card, lower down
    band = im[1180:1460, 40:1040] if name == "s00" else im[240:880, 40:1040]
    frac = (band < 200).sum() / band.size * 100.0
    print("  %-4s %6.3fs  ink %5.2f%%%s" % (name, t, frac, "   <-- VOID" if frac <= FLOOR else ""))
    if frac <= FLOOR:
        bad.append(name)
if bad:
    sys.exit("gate_voids: %d scene(s) cut onto blank paper: %s" % (len(bad), ", ".join(bad)))
print("gate_voids: all %d cut frames carry their scene" % len(CUTS))
