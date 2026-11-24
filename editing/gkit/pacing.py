#!/usr/bin/env python3
r"""Pacing check: the monotony our DOM / QA / cut-frame gates cannot see (HANDOFF-100x-style-gaurav.md).

    python3 gkit/pacing.py cut.mp4 [t0 t1] [--ref ref.mp4 [r0 r1]]

Per frame: mean |luma diff| against the previous frame on a 108x192 grey thumbnail (0-255).
  hard cut     diff > 28 (a page change, a flipbook flick, a meme cut)
  static       diff < 0.5
  near-static  diff < 1.5
Measure the reference with the SAME call on the same span length: absolute numbers differ between
methods (gb9 LEARNINGS quoted Prompt Motion at 45% near-static, the breakdown at 20%), the delta is what counts.
"""
import subprocess
import sys

import numpy as np

W, H, CUT, STATIC, NEAR = 108, 192, 28.0, 0.5, 1.5


def frames(path, t0=None, t1=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(t0)] if t0 is not None else []) + ["-i", path]
    if t1 is not None:
        cmd += ["-t", str(t1 - (t0 or 0))]
    cmd += ["-vf", "scale=%d:%d,format=gray" % (W, H), "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def measure(path, t0=None, t1=None):
    f = frames(path, t0, t1)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    n = len(d)
    cuts = int((d > CUT).sum())
    dur = len(f) / 30.0
    return dict(frames=len(f), dur=round(dur, 2), cuts=cuts, s_per_cut=round(dur / max(cuts, 1), 2),
                static=round(100.0 * (d < STATIC).sum() / n, 1), near=round(100.0 * (d < NEAR).sum() / n, 1),
                mean=round(float(d.mean()), 2), longest_hold=round(longest(d) / 30.0, 2))


def longest(d):
    """the longest run of near-static frames: one 2 s freeze is worse than ten scattered still frames"""
    best = cur = 0
    for v in d:
        cur = cur + 1 if v < NEAR else 0
        best = max(best, cur)
    return best


def fmt(tag, m):
    return ("%-5s %5.2fs  cuts %2d (1 per %.2fs)  static %4.1f%%  near-static %4.1f%%  mean %5.2f  longest still %.2fs"
            % (tag, m["dur"], m["cuts"], m["s_per_cut"], m["static"], m["near"], m["mean"], m["longest_hold"]))


if __name__ == "__main__":
    a = sys.argv[1:]
    ref = None
    if "--ref" in a:
        k = a.index("--ref")
        ref, a = a[k + 1:], a[:k]
    nums = lambda xs: [float(x) for x in xs[1:3]] if len(xs) >= 3 else [None, None]
    print(fmt("cut", measure(a[0], *nums(a))))
    if ref:
        print(fmt("ref", measure(ref[0], *nums(ref))))
