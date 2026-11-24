#!/usr/bin/env python3
r"""Delivery QA for any gkit build (handoff item 7), reading the DELIVERED file, never the preview:

  python3 gkit/qa.py sheets  hf95a out/vid95a-final.mp4      # every cut, +2f, mid-scene -> qa/cuts_N.jpg
  python3 gkit/qa.py lag     hf95a out/vid95a-final.mp4      # engine frame-repeat check on full-frame A-roll beats
  python3 gkit/qa.py ink     hf95a out/vid95a-final.mp4      # cut frame + next 3: never near-blank (item 4)
  python3 gkit/qa.py cues    hf95a out/vid95a-final.mp4      # no SFX cue lifts his voice's peak > 1.5 dB
  python3 gkit/qa.py peak    out/vid95a-final.mp4            # true peak <= -1 dBTP
  python3 gkit/qa.py all     hf95a out/vid95a-final.mp4
"""
import json, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

FPS = 30


def plan(proj):
    return json.load(open(os.path.join(proj, "plan.json")))


def gray(path, w, h, crop=None):
    vf = (crop + "," if crop else "") + "scale=%d:%d,format=gray" % (w, h)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(r, np.uint8).reshape(-1, h, w).astype(np.float32)


def sheets(proj, src):
    P = plan(proj)
    want = []
    for n, a, b, _ in P["scenes"]:
        fa = int(round(a * FPS))
        want += [(fa, n), (fa + 2, n + "+2"), (int(round((a + b) / 2 * FPS)), n + " mid")]
    want.append((int(round(P["dur"] * FPS)) - 1, "last"))
    frames = sorted(set(f for f, _ in want))
    lab = {}
    for f, l in want:
        lab.setdefault(f, l)
    qd = os.path.join(proj, "qa")
    os.makedirs(qd, exist_ok=True)
    tmp = os.path.join(qd, "c_%04d.png")
    expr = "+".join("eq(n\\,%d)" % f for f in frames)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "select='%s',scale=270:480" % expr, "-vsync", "0", tmp], check=True)
    tw, th, cols = 270, 480, 9
    rows = (len(frames) + cols - 1) // cols
    im = Image.new("RGB", (cols * tw, rows * (th + 22)), "#222")
    d = ImageDraw.Draw(im)
    for i, f in enumerate(frames):
        p = tmp % (i + 1)
        x, y = (i % cols) * tw, (i // cols) * (th + 22)
        im.paste(Image.open(p).convert("RGB"), (x, y + 22))
        d.text((x + 4, y + 4), "%s f%d %.2f" % (lab[f], f, f / FPS), fill="#fff")
        os.remove(p)
    per = 3 * (th + 22)
    outs = []
    for k in range(0, im.height, per):
        out = os.path.join(qd, "cuts_%d.jpg" % (k // per))
        im.crop((0, k, im.width, min(im.height, k + per))).save(out, quality=82)
        outs.append(out)
    print("\n".join(outs))


def lag(proj, src):
    """on full-frame beats the render must show source frame n at frame n (HyperFrames floor() bug)"""
    P = plan(proj)
    master = os.path.join(proj, "assets", "aroll.mp4")
    full = [(a, b) for n, a, b, r in P["scenes"] if r in ("FULL", "AR")]
    W, H = 90, 120
    # compare the FACE only (measured box, 4K space): overlays on the chest made the old fixed crop read noise
    # FULL/AR beats only: a SPLIT rung's box is in scaled stage space and its union with the full boxes cropped the
    # film above the seam, so every frame differed by ~40 levels and 8 noise frames read "off-index" (vid98 v1)
    fullset = {n for n, a, b, r in P["scenes"] if r in ("FULL", "AR")}
    fb = [v for k, v in P.get("full_face", {}).items() if k in fullset]
    if fb:
        t, bt = min(f["top"] for f in fb), max(f["bot"] for f in fb)
        l, r = min(f["left"] for f in fb), max(f["right"] for f in fb)
        crop = "crop=%d:%d:%d:%d" % (int((r - l) * 2) // 2 * 2, int((bt - t) * 2) // 2 * 2, int(l * 2), int(t * 2))
    else:
        crop = "crop=1400:1400:380:600"
    R = gray(src, W, H, crop)
    S = gray(master, W, H, crop)
    bad, tot = [], 0
    for a, b in full:
        for f in range(int(round(a * FPS)) + 1, int(round(b * FPS)) - 1):
            if f + 1 >= len(S) or f >= len(R):
                continue
            d = [np.abs(R[f] - S[f + k]).mean() for k in (-1, 0, 1)]
            tot += 1
            if int(np.argmin(d)) != 1 and min(d) < d[1] - 0.3:
                bad.append((f, ["-1", "0", "+1"][int(np.argmin(d))]))
    print("lag: %d full-frame frames checked, %d off-index %s" % (tot, len(bad), bad[:12]))
    return not bad


def ink(proj, src, thr=1.0):
    """the cut frame and the next 3 must carry content.  'ink' = share of pixels that differ from the frame's
    dominant ground by > 40 levels (a standing line of type on black is ~2-4%; a header-only white card on
    paper ~0.5%).  Fails under thr %."""
    P = plan(proj)
    G = gray(src, 216, 384)
    bad, rows = [], []
    for n, a, b, r in P["scenes"]:
        f0 = int(round(a * FPS))
        vals = []
        for f in range(f0, min(f0 + 4, len(G))):
            g = G[f]
            ground = float(np.median(g))
            pct = 100.0 * float((np.abs(g - ground) > 40).mean())
            vals.append(pct)
            if pct < thr:
                bad.append((n, f, round(pct, 2)))
        rows.append("%s %.1f" % (n, min(vals)))
    print("ink: min %% per cut: " + ", ".join(rows))
    print("ink: %d cut frames checked, %d under %.1f%% %s" % (4 * len(P["scenes"]), len(bad), thr, bad[:12]))
    return not bad


def cues(proj, src):
    SR = 48000

    def pcm(p):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
        return np.frombuffer(r, np.float32)
    cf = os.path.join(proj, "sfx_cues.json")
    if not os.path.exists(cf):
        print("cues: no bed")
        return True
    v, m = pcm(os.path.join(proj, "assets", "aroll.mp4")), pcm(src)
    n = min(len(v), len(m))
    v, m = v[:n], m[:n]
    db = lambda x: 20 * np.log10(max(float(np.abs(x).max()), 1e-9))
    over = []
    C = json.load(open(cf))
    for c in C:
        a = int(c["t"] * SR)
        b = a + int(0.25 * SR)
        if b > n:
            continue
        dv, dm = db(v[a:b]), db(m[a:b])
        if dm - dv > 1.5:
            over.append((c["id"], round(c["t"], 2), round(dv, 1), round(dm, 1)))
    print("cues: %d cues, %d lift the window peak > 1.5 dB %s" % (len(C), len(over), over))
    return not over


def true_peak(src):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", r)
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    return (float(m[-1]) if m else 99.0), (I[-1] if I else "?")


def peak(src, ref=None):
    """true peak <= -1 dBTP, or (his master already peaks above that and is never processed) no higher
    than his master's own true peak + 0.2 dB"""
    tp, lufs = true_peak(src)
    print("peak: delivered true peak %.2f dBTP, integrated %s LUFS" % (tp, lufs))
    if ref:
        rt, _ = true_peak(ref)
        lim = max(-1.0, rt + 0.2)
        print("peak: his master %.2f dBTP (untouched) -> limit %.2f" % (rt, lim))
        return tp <= lim
    return tp <= -1.0


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "peak":
        sys.exit(0 if peak(sys.argv[2]) else 1)
    proj, src = os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
    if cmd == "sheets":
        sheets(proj, src)
    elif cmd == "all":
        ok = [lag(proj, src), ink(proj, src), cues(proj, src), peak(src, os.path.join(proj, "assets", "aroll.mp4"))]
        sheets(proj, src)
        print("QA %s" % ("PASS" if all(ok) else "FAIL"))
    else:
        sys.exit(0 if globals()[cmd](proj, src) else 1)
