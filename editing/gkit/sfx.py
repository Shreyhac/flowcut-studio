#!/usr/bin/env python3
r"""gkit SFX bed for any cut:  python3 gkit/sfx.py hf95a   (from vid91/vid94 sfx91/sfx94)

Reads <proj>/cues.py (CUES = [(id, time | "#elementId[+s]", file, class, dur)]),
and carries hf89's three rules:
  1. gains reference his speech RMS (+2.2 dB = VO_PEAK, the vid88 relationship he
     passed), never the median;
  2. every file is trimmed to its own transient (relative threshold) as WAV;
  3. anchored cues resolve off the real timeline, so a cue cannot drift from the
     tween it belongs to.
Then it reports PILE-UPS: cues whose summed class level inside 90 ms would sit
more than 1 dB over VO_PEAK (vid79 round 3: six stacked cues read +8.6 dB).
"""
import importlib.util, json, os, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from reel import anchors  # noqa: E402

SR = 48000
PRE = 0.008


def samples(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def onset(x, rel=0.12):
    pk = float(np.abs(x).max())
    return 0.0 if pk <= 0 else int(np.argmax(np.abs(x) > pk * rel)) / float(SR)


def speech_rms(path):
    x = samples(path)
    n = len(x) // 480
    fr = x[:n * 480].reshape(n, 480)
    db = 20 * np.log10(np.maximum(np.sqrt((fr ** 2).mean(1)), 1e-9))
    act = db > db.max() - 30
    return float(20 * np.log10(np.sqrt((fr[act] ** 2).mean())))


def main(proj):
    proj = os.path.abspath(proj)
    DUR = json.load(open(os.path.join(proj, "plan.json")))["dur"]
    spec = importlib.util.spec_from_file_location("cues", os.path.join(proj, "cues.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sfx = os.path.join(proj, "assets", "sfx")
    rms = speech_rms(os.path.join(proj, "assets", "aroll.mp4"))
    vo_peak = round(rms + 2.2 + getattr(mod, "KIT_OFFSET", 0.0), 1)
    cls_db = {"impact": -4.0, "rocket": -4.5, "thud": -5.5, "pop": -7.0, "shine": -8.0, "trans": -9.0,
              "marker": -10.0, "click": -11.0, "bed": -12.0, "soft": -13.0}
    cls_db = {k: vo_peak + v for k, v in cls_db.items()}
    cues = anchors.resolve(mod.CUES, os.path.join(proj, "index.html"))
    made = {}
    for _, _, fn, _, _ in cues:
        if fn in made:
            continue
        x = samples(os.path.join(sfx, fn))
        off = max(0.0, onset(x) - PRE)
        gain = -1.0 - 20 * np.log10(max(float(np.abs(x).max()), 1e-9))
        out = os.path.join(sfx, "t_" + fn.replace(".mp3", ".wav"))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(sfx, fn), "-af",
                        "atrim=start=%.5f,asetpts=N/SR/TB,volume=%.3fdB" % (off, gain),
                        "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", out], check=True)
        y = samples(out)
        assert onset(y) < 0.012, fn
        made[fn] = dict(peak=20 * np.log10(max(float(np.abs(y).max()), 1e-9)), dur=len(y) / float(SR))
    rows, block = [], []
    for i, (cid, t, fn, cls, d) in enumerate(cues):
        m = made[fn]
        d = round(min(d, m["dur"] - 0.005, DUR - t - 0.01), 3)
        vol = round(min(10 ** ((cls_db[cls] - m["peak"]) / 20.0), 1.0), 3)
        rows.append(dict(id=cid, t=round(t, 3), file=fn, cls=cls, dur=d, vol=vol, target=round(cls_db[cls], 1)))
        block.append('<audio id="sfx_%s" src="assets/sfx/t_%s" data-start="%.3f" data-duration="%.2f" '
                     'data-track-index="%d" data-volume="%.3f"></audio>'
                     % (cid, fn.replace(".mp3", ".wav"), t, d, 300 + i, vol))
    open(os.path.join(proj, "sfx_block.html"), "w").write("\n".join(block))
    json.dump(rows, open(os.path.join(proj, "sfx_cues.json"), "w"), indent=1)
    json.dump({"speech_rms": round(rms, 2), "vo_peak": vo_peak}, open(os.path.join(proj, "audio.json"), "w"))
    # pile-ups: power-sum of class targets for cues within 90 ms
    bad = []
    rs = sorted(rows, key=lambda r: r["t"])
    for i, r in enumerate(rs):
        grp = [q for q in rs if 0 <= q["t"] - r["t"] < 0.09]
        if len(grp) > 1:
            tot = 10 * np.log10(sum(10 ** (q["target"] / 10) for q in grp))
            if tot > vo_peak + 1.0:
                bad.append((r["t"], [q["id"] for q in grp], round(tot - vo_peak, 1)))
    print("%d cues · speech RMS %.1f · VO_PEAK %.1f" % (len(rows), rms, vo_peak))
    for b in bad:
        print("  PILE-UP at %.2f: %s  (+%.1f dB over VO_PEAK)" % b)
    return rows, bad


if __name__ == "__main__":
    main(sys.argv[1])
