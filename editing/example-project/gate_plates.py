#!/usr/bin/env python3
"""Every B-roll plate must MOVE, and must not be a black hole.

A <video> whose media clock is never driven paints its first frame for the
whole scene.  That is invisible to every structural gate: the plate is
present, in the right box, correctly framed — it is simply a still.  This
measures the mean absolute difference between two frames inside each plate's
own window, cropped to the plate's rect on the DELIVERED file, and fails a
plate that does not change.  It also fails one that is nearly black, which is
what an undecoded or off-window <video> looks like.
"""
import subprocess
import sys
import numpy as np

SRC = sys.argv[1] if len(sys.argv) > 1 else "renders/vid87-v1-mixed.mp4"
W, H = 2160, 3840          # the delivered frame; the plate rect is 1080-space
# scene, key, in, out, rect (1080-space) — must match PLATE_PLAN in build_index.py
PLATES = [("s01", "browse", 1.710, 2.760, (552, 356, 420, 272)),
          ("s02", "checkout", 2.760, 3.780, (72, 290, 600, 338)),
          ("s05", "aianswer", 5.860, 7.230, (72, 290, 600, 338))]
FLOOR = 0.8        # mean |delta|, 0-255
DARK = 18.0        # mean luma under this is a black rectangle, not footage


def frame(t):
    f = int(round(t * 30))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC,
                          "-vf", "select=eq(n\\,%d)" % f, "-vsync", "0",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W).astype(int)


bad = []
for name, key, a, b, (PX, PY, PW, PH) in PLATES:
    t1, t2 = a + (b - a) * 0.22, a + (b - a) * 0.86
    f1, f2 = frame(t1), frame(t2)
    X, Y, Wc, Hc = PX * 2, PY * 2, PW * 2, PH * 2
    c1 = f1[Y:Y + Hc, X:X + Wc]
    c2 = f2[Y:Y + Hc, X:X + Wc]
    d = np.abs(c1 - c2).mean()
    lum = (c1.mean() + c2.mean()) / 2
    flag = ""
    if d < FLOOR:
        flag, _ = "   <-- FROZEN", bad.append("%s/%s frozen" % (name, key))
    elif lum < DARK:
        flag, _ = "   <-- BLACK", bad.append("%s/%s black" % (name, key))
    print("  %-4s %-12s %5.3fs..%5.3fs  mean |delta| %6.2f  luma %5.1f%s"
          % (name, key, t1, t2, d, lum, flag))
if bad:
    sys.exit("gate_plates: %d plate(s) failed: %s" % (len(bad), ", ".join(bad)))
print("gate_plates: all %d plates are live" % len(PLATES))
