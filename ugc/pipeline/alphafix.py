#!/usr/bin/env python3
"""Reaction cut-out alpha repair + QA (peer review 25 Nov: holes in v2 pen tip @45 s, misaki mouth/pen @8.3-9.0 s).
usage: alphafix.py <react_join.mp4> <react_cut.webm> <out.mov> [x0,y0,x1,y1 crop]   (run with the cvenv python: cv2 + numpy)
RGB comes from the source join (the matte zeroes RGB where alpha=0, so a filled hole would otherwise be black).
Alpha: (1) enclosed transparent regions (not connected to the frame border) -> opaque; (2) 7 px elliptical close, kept as max;
(3) temporal: a frame whose opaque area inside the subject box drops >3% below the median of its +-3 neighbours gets
max(alpha, neighbours' alpha). Prints per-run stats and every flagged frame; exits 2 if any frame still fails after repair."""
import subprocess, sys
import cv2, numpy as np

src, cut, out = sys.argv[1:4]
W, H = 360, 640


def frames(path, fmt, extra=()):
    p = subprocess.Popen(["ffmpeg", "-v", "error", *extra, "-i", path, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", fmt, "-"],
                         stdout=subprocess.PIPE)
    n = W * H * (4 if fmt == "rgba" else 3)
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, -1)


rgb = [f.copy() for f in frames(src, "rgb24")]
al = [f[:, :, 3].copy() for f in frames(cut, "rgba", ("-c:v", "libvpx-vp9"))]
assert abs(len(rgb) - len(al)) <= 1, (len(rgb), len(al))
n = min(len(rgb), len(al)); rgb, al = rgb[:n], al[:n]
K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))


def holes(a):
    inv = (a <= 127).astype(np.uint8)
    cnt, lab = cv2.connectedComponents(inv, connectivity=4)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) | {0}
    m = np.isin(lab, list(edge), invert=True)
    return m


def area(a, box):
    x0, y0, x1, y1 = box
    return int((a[y0:y1, x0:x1] > 127).sum())


filled = pen = flick = 0
KD = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
for i, a in enumerate(al):
    h = holes(a); filled += int(h.sum()); a[h] = 255
    c = rgb[i].astype(np.int16); r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    purple = (r - g > 15) & (b - g > 25) & (cv2.dilate((a > 127).astype(np.uint8), KD) > 0) & (a < 250)   # the highlighter, next to her
    pen += int(purple.sum()); a[purple] = 255
    al[i] = np.maximum(a, cv2.morphologyEx(a, cv2.MORPH_CLOSE, K))
orig = [a.copy() for a in al]
for i in range(n):   # momentary drop-outs: opaque in both neighbours (1 or 2 frames away) but not here
    for d in (1, 2):
        if i - d >= 0 and i + d < n:
            m = np.minimum(orig[i - d], orig[i + d]); flick += int(((m > 127) & (al[i] <= 127)).sum()); al[i] = np.maximum(al[i], m)
box = tuple(int(v) for v in sys.argv[4].split(",")) if len(sys.argv) > 4 else (0, 0, W, H)   # x0,y0,x1,y1 = the PiP crop


def flagged():
    ar = np.array([area(a, box) for a in al]); bad = []
    for i in range(n):
        nb = np.r_[ar[max(0, i - 3):i], ar[i + 1:i + 4]]
        if len(nb) and ar[i] < 0.97 * np.median(nb):
            bad.append((i, ar[i], int(np.median(nb))))
    return bad


bad = flagged()
for i, _, _ in bad:
    nb = [al[j] for j in (i - 1, i + 1) if 0 <= j < n]
    al[i] = np.maximum(al[i], np.max(np.stack(nb), axis=0))
for a in al:   # final pass: the pen/close/temporal fills can enclose new gaps (pen against her cheek)
    a[holes(a)] = 255
left = flagged(); still_holes = sum(int(holes(a).sum() > 0) for a in al)
print(f"frames {n}, box {box}, interior hole px filled {filled}, purple px {pen}, flicker px {flick}, area-drop frames {len(bad)} {[(round(i / 24, 2), a, m) for i, a, m in bad][:20]}")
print(f"after repair: area-drop frames {len(left)} {[(round(i / 24, 2), a, m) for i, a, m in left][:20]}, frames with enclosed holes {still_holes}")
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", "24", "-i", "-",
                      "-c:v", "png", "-pix_fmt", "rgba", out], stdin=subprocess.PIPE)
for c, a in zip(rgb, al):
    p.stdin.write(np.dstack([c, a]).tobytes())
p.stdin.close(); p.wait()
sys.exit(2 if left or still_holes else 0)
