#!/usr/bin/env python3
"""Pull a frame at every beat (+2 frames after each) out of the DELIVERED file in
one decode pass, named <t>_<beat>.png at 1080x1920, into qa/.  Then scan every
frame's mean luma for single-frame spikes (the vid80 blank-frame-before-a-cut
signature) and report them."""
import json, os, re, subprocess, sys, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1]
src = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
T = json.loads(re.search(r"var T = (\{.*?\}), CAM", src, re.S).group(1))
FPS, N = 30, int(round(T["end"] * 30))
want = {}
for k, v in T.items():
    for dk, dv in ((k, 0), (k + "+2f", 2)):
        f = min(N - 1, int(round(v * FPS)) + dv)
        want.setdefault(f, dk)
want.setdefault(0, "frame0")
want.setdefault(N - 1, "last")
out = os.path.join(HERE, "qa")
os.makedirs(out, exist_ok=True)
for f in glob.glob(os.path.join(out, "*.png")):
    os.remove(f)
frames = sorted(want)
expr = "+".join("eq(n\\,%d)" % f for f in frames)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-vf", "select='%s',scale=1080:1920" % expr,
                "-vsync", "0", os.path.join(out, "tmp_%04d.png")], check=True)
tmp = sorted(glob.glob(os.path.join(out, "tmp_*.png")))
assert len(tmp) == len(frames), "%d extracted, %d wanted" % (len(tmp), len(frames))
for p, f in zip(tmp, frames):
    os.rename(p, os.path.join(out, "%06.3f_%s.png" % (f / FPS, re.sub(r"[^A-Za-z0-9+_-]", "", want[f]))))
print("qa: %d beat frames" % len(frames))

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-vf", "scale=108:192,format=gray",
                      "-f", "rawvideo", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(float)
art = fr[:, 24:88, :].mean(axis=(1, 2))           # the art band, y240..880
spikes = [i for i in range(1, len(art) - 1)
          if art[i] - max(art[i - 1], art[i + 1]) > 6 or min(art[i - 1], art[i + 1]) - art[i] > 6]
print("luma scan: %d frames, %d single-frame spike(s)%s" % (len(art), len(spikes),
      (": " + ", ".join("f%d (%.3fs)" % (i, i / FPS) for i in spikes)) if spikes else ""))
