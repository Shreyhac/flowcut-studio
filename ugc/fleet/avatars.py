#!/usr/bin/env python3
"""Generate one realistic beach walking-selfie start frame per account (fleet/avatars/<key>.png).
Idempotent: skips accounts whose frame exists. Runs up to 4 Masonry jobs at once."""
import json, os, re, subprocess, sys, concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "avatars"); os.makedirs(OUT, exist_ok=True)
acc = json.load(open(os.path.join(HERE, "accounts.json")))["accounts"]
only = set(sys.argv[1:])

BASE = ("Genuine unedited iPhone front-camera selfie video frame of {who}, wearing {outfit}, walking along the shoreline "
        "of {scene}. Phone held at arm's length a little above eye level, so her head sits in the MIDDLE of the vertical frame "
        "with open sky and the ocean horizon in the upper third above her head, her shoulders and upper body in the lower part, "
        "her outstretched arm entering from one side. Real waves with white foam behind her, wet sand. Natural real daylight, "
        "relaxed happy expression, slight smile, mouth a little open mid-word. Real skin texture with pores, a few loose "
        "hairs moving in the wind, visible sensor noise and mild compression, horizon tilted a couple of degrees, no beauty "
        "filter, no bokeh, no retouching. A nice casual summer top with a relaxed beach vibe, not swimwear.")


def ref_jpg(path, key):
    p = os.path.expanduser(path if os.path.isabs(os.path.expanduser(path)) else os.path.join(HERE, path))
    j = os.path.join(OUT, f"_ref_{key}.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", "scale=576:-2", "-q:v", "4", j], check=True)
    return j


def one(a):
    key = a["key"]; dst = os.path.join(OUT, key + ".png")
    if os.path.exists(dst):
        return key, "exists"
    if a.get("frame"):
        subprocess.run(["cp", os.path.join(HERE, a["frame"]), dst], check=True); return key, "copied approved frame"
    cmd = ["masonry", "image", BASE.format(**a), "-m", "gpt-image-2.6-sunburst", "-a", "9:16", "--title", f"avatar_{key}"]
    if a.get("ref"):
        cmd += ["--ref", ref_jpg(a["ref"], key)]
    for attempt in range(3):
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        m = re.search(r'"job_id":\s*"([^"]+)"', out)
        if not m:
            continue
        w = subprocess.run(["masonry", "job", "wait", m.group(1), "--timeout", "12m", "--download", "-o", dst, "--overwrite"],
                           capture_output=True, text=True)
        if os.path.exists(dst):
            return key, f"ok job {m.group(1)}"
        err = re.findall(r'"message":\s*"([^"]{0,160})', w.stdout + w.stderr)
        if err and "safety" in err[-1]:   # soften the outfit wording and retry
            cmd[2] = cmd[2].replace(a["outfit"], "a loose cotton beach cover-up dress")
    return key, "FAILED"


todo = [a for a in acc if not only or a["key"] in only]
with cf.ThreadPoolExecutor(int(os.environ.get("PAR", "1"))) as ex:
    for k, r in ex.map(one, todo):
        print(f"{k:7s} {r}", flush=True)
