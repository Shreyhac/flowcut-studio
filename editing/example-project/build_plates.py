#!/usr/bin/env python3
r"""vid87 — pre-composite every B-roll plate to the exact rect it occupies.

One plate per scene: his A-roll plus at most ONE B-roll decoder at any
instant on an 8 GB machine, no CSS transform over media, and the crop that
matters decided here with ffmpeg rather than by object-fit.  Each plate is
conformed at 2x its on-stage rect (the composition renders #stage at 2x).

Provenance: vid87/stock/stock-manifest.json (Pexels, real uploads) and
vid87/firstparty/SOURCES.md (first-party product films).
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "assets", "plates")

# key, source, in-point, crop (w,h,x,y as fractions of the source) or None, stage rect w,h, dur, speed
PLATES = [
    ("browse",   "vid87/stock/browse_7872722.mp4",     2.40, (1.00, 0.345, 0.00, 0.300), (420, 272), 1.40, 1.0),
    ("checkout", "vid87/stock/checkout_10224109.mp4",  0.60, None,                        (600, 338), 1.40, 1.0),
    # Google's own AI Mode film (search.google/ways-to-search/ai-mode/, HEVC 1080x1350).
    # 5.55s = the answer already fading in on the cut frame (5.0 is a dark crossfade);
    # 1.6x so the 1.37s scene carries answer-in, the 12-site answer holding, and the
    # scroll that starts at source 7.3.  Crop = the query + answer band, 16:9.
    ("aianswer", "vid87/firstparty/raw/g_aim-migrating-birds_en-US.mov",
                                                        5.55, (1.00, 0.4496, 0.00, 0.160), (600, 338), 1.70, 1.6),
]


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg failed:\n%s" % r.stderr[-900:])


def probe(p):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                           "-show_entries", "stream=width,height", "-show_entries", "format=duration",
                           "-of", "default=noprint_wrappers=1:nokey=1", p],
                          capture_output=True, text=True).stdout.split()


def main():
    os.makedirs(OUT, exist_ok=True)
    made = json.load(open(os.path.join(HERE, "plates.json"))) \
        if os.path.exists(os.path.join(HERE, "plates.json")) else {}
    for key, rel, ss, crop, (sw_, sh_), dur, speed in PLATES:
        if len(sys.argv) > 1 and key not in sys.argv[1:]:
            continue
        src = os.path.join(ROOT, rel)
        w0, h0 = [int(v) for v in probe(src)[:2]]
        OW, OH = sw_ * 2, sh_ * 2
        dst = os.path.join(OUT, "%s.mp4" % key)
        vf = ["setpts=(PTS-STARTPTS)/%.3f" % speed] if speed != 1.0 else []
        if crop:
            cw, ch, cx, cy = crop
            vf.append("crop=%d:%d:%d:%d" % (int(w0 * cw), int(h0 * ch), int(w0 * cx), int(h0 * cy)))
        vf += ["scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos" % (OW, OH),
               "crop=%d:%d" % (OW, OH), "fps=30,setsar=1"]
        run(["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % ss, "-i", src, "-t", "%.2f" % dur,
             "-an", "-vf", ",".join(vf), "-c:v", "libx264", "-crf", "17", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-g", "15", "-keyint_min", "15", dst])
        p = probe(dst)
        assert float(p[-1]) >= dur - 0.05, "%s conformed to %.2fs" % (key, float(p[-1]))
        made[key] = dict(path="assets/plates/%s.mp4" % key, w=int(p[0]), h=int(p[1]),
                         dur=float(p[-1]), src=rel, src_wh="%dx%d" % (w0, h0), ss=ss, speed=speed)
        print("  %-10s %sx%s %.2fs <- %s @ %.2fs" % (key, p[0], p[1], float(p[-1]), rel, ss))
    json.dump(made, open(os.path.join(HERE, "plates.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
