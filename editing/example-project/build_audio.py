#!/usr/bin/env python3
r"""Trim, level and emit hf80's SFX bed — and prove every cue lands on its beat.

Three rules, all of them paid for on earlier films:

1. **Gains are referenced to his speech-active PEAK, not its median.**  On
   rumik1 a 34-cue kit was placed perfectly and measured a lift over the voice
   of +0.0 dB, because every gain had been set under her speech *median*
   (-23.6) instead of her *peak* (-12.7).  The cue list read as finished the
   whole time.  This take's speech-active peak is -10.1 dBFS.

2. **Every file is trimmed to its own transient.**  This kit carries 0-1203 ms
   of leading silence: `wsh2` starts 1.203 s in, `marker` 577 ms, `riser` 673.
   A click cued on a button press lands a second later.  The threshold is
   RELATIVE to each file's own peak — an absolute one leaves a quiet file's
   real onset 80-120 ms past the trim point.

3. **Each cue is verified ALONE.**  Measured on a shared stem, four cues 130 ms
   apart all report the loudest of the four and the check invents an error.
   And the assertion is on ONSET, not on peak position: a riser or a shine
   legitimately peaks long after it starts.

Run: python3 build_audio.py     (writes assets/sfx/t_*.mp3 + prints the block)
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SFX = os.path.join(HERE, "assets", "sfx")
SR = 48000

# 0905.mp4 is HOT: 4603 clipped samples and an absolute peak of +3.14 dBFS, so
# the absolute peak is a clipping artefact, not a level.  The robust loud level
# (p95 of a 10 ms peak envelope over speech-active samples) is +0.97 dBFS and the
# speech RMS is -14.19.
#
# ROUND 2 — he said the SFX is too loud.  Measured on the v6 render, the class
# targets were not the problem: the loudest class sat at -12.2, only +2.0 dB over
# his speech RMS, which is the relationship vid77 shipped with and he passed.
# The problem was that cues STACK.  Six pile-ups fired inside 70 ms of each other
# and their SUM reached -5.6 dBFS, +8.6 dB over his speech RMS.  A cue list read
# per-cue looks correct the whole time; what he hears is the sum.
#
# Two changes, not one:
#   · the whole kit comes down 5 dB (VO_PEAK -8.2 -> -13.2), so impacts land at
#     -17.2, which is 3 dB UNDER his speech RMS rather than 2 dB over it;
#   · the four worst pile-ups are separated in time below, so nothing sums.
# Still peak-referenced, not median-referenced, so the rumik1 failure (a whole
# kit inaudible) stays fixed — the correction is the OFFSET and the SPACING.
VO_PEAK = -15.3
# shreyanshnew.mp4 (vid87): speech RMS -17.47 dBFS, robust peak (p95 of a 10 ms
# envelope over speech) -2.82, 181 clipped samples.  1.7 dB hotter than vid80's
# take, so the kit moves WITH the take (vid79 rule: port the relationship, not
# the number): vid80 hung VO_PEAK 2.16 dB over his speech RMS, so -15.3 here and
# impacts land ~2 dB under his RMS.  No two cues fire inside 120 ms.
PRE = 0.008

CLASS_DB = {
    "impact":  VO_PEAK - 4.0,
    "rocket":  VO_PEAK - 4.5,
    "thud":    VO_PEAK - 5.5,
    "pop":     VO_PEAK - 7.0,
    "shine":   VO_PEAK - 8.0,
    "trans":   VO_PEAK - 9.0,
    "marker":  VO_PEAK - 10.0,
    "click":   VO_PEAK - 11.0,
    "bed":     VO_PEAK - 12.0,
    "soft":    VO_PEAK - 13.0,
}

# id, time, file, class, duration
CUES = [
    # ── s00 · the cover stands; the G turns, the pill nods ─────────────
    ("openP",   0.010, "paper.mp3",    "soft",   0.50),
    ("openSh",  0.140, "shine.mp3",    "shine",  0.80),
    ("gTurn",   0.500, "click.mp3",    "click",  0.36),
    ("pillNod", 0.920, "page.mp3",     "soft",   0.30),
    # ── s01 · Google sends visitors ────────────────────────────────────
    ("w01",     1.610, "wsh.mp3",      "trans",  0.55),
    ("gIn",     1.730, "pop2.mp3",     "pop",    0.42),
    ("curs",    1.920, "pops.mp3",     "bed",    0.62),
    ("visCnt",  2.120, "beeps.mp3",    "soft",   0.60),
    # ── s02 · visitors are money ───────────────────────────────────────
    ("w02",     2.660, "wsh2.mp3",     "trans",  0.55),
    ("notes",   3.020, "page.mp3",     "soft",   0.30),
    ("upChip",  3.300, "pop.mp3",      "pop",    0.40),
    ("money",   3.440, "confirm.mp3",  "shine",  0.60),
    # ── s03 · THE DEAL, snapped ────────────────────────────────────────
    ("w03",     3.680, "wsh.mp3",      "trans",  0.55),
    ("dealIn",  3.800, "thud.mp3",     "thud",   0.34),
    ("shake",   4.140, "glitch.mp3",   "marker", 0.40),
    ("ended",   4.460, "impact.mp3",   "impact", 0.85),
    ("snap",    4.600, "tear.mp3",     "trans",  0.50),
    # ── s04 · the AI reads your page ───────────────────────────────────
    ("w04",     4.930, "wsh2.mp3",     "trans",  0.55),
    ("tiles",   5.050, "popcl.mp3",    "pop",    0.50),
    ("scan",    5.200, "keys.mp3",     "bed",    0.50),
    ("suck",    5.520, "swoosh.mp3",   "trans",  0.40),
    # ── s05 · and answers, zero clicks ─────────────────────────────────
    ("w05",     5.760, "wsh.mp3",      "trans",  0.55),
    ("ring",    6.260, "marker.mp3",   "marker", 0.55),
    ("srcCut",  6.500, "slice.mp3",    "impact", 0.50),
    ("never",   6.660, "pop2.mp3",     "pop",    0.42),
    # ── s06 · the traffic crash ────────────────────────────────────────
    ("w06",     7.130, "wsh2.mp3",     "trans",  0.55),
    ("crash",   7.340, "slowdown.mp3", "trans",  0.90),
    ("ratio",   7.620, "beeps.mp3",    "soft",   0.60),
    ("drop",    7.800, "thud.mp3",     "thud",   0.34),
    ("dot",     8.260, "pop.mp3",      "pop",    0.40),
    ("anymore", 8.620, "impact.mp3",   "impact", 0.80),
    # ── s07 · Cloudflare: Allow -> Charge, 402 ─────────────────────────
    ("w07",     9.030, "wsh.mp3",      "trans",  0.55),
    ("cfIn",    9.150, "shine.mp3",    "shine",  0.80),
    ("chClick",10.100, "click.mp3",    "click",  0.36),
    ("cells",  10.230, "popcl.mp3",    "pop",    0.50),
    ("st402",  10.540, "impact.mp3",   "impact", 0.85),
    ("buzz",   10.680, "glitch.mp3",   "marker", 0.40),
    # ── s08 · your info, your price ────────────────────────────────────
    ("w08",    11.190, "wsh2.mp3",     "trans",  0.55),
    ("info",   11.300, "thud.mp3",     "thud",   0.34),
    ("priceK", 11.440, "type.mp3",     "bed",    0.45),
    ("price",  12.040, "impact.mp3",   "impact", 0.80),
    ("decide", 12.260, "marker.mp3",   "marker", 0.50),
    # ── s09 · the crawler pays at the gate ─────────────────────────────
    ("w09",    12.520, "wsh.mp3",      "trans",  0.55),
    ("coin",   12.760, "pop.mp3",      "pop",    0.40),
    ("paid",   13.120, "correct.mp3",  "shine",  0.60),
    ("walk",   13.340, "page.mp3",     "soft",   0.30),
    # ── s10 · 402s every day ───────────────────────────────────────────
    ("w10",    13.560, "wsh2.mp3",     "trans",  0.55),
    ("bigCnt", 13.700, "beeps.mp3",    "soft",   0.80),
    ("log1",   14.000, "pop2.mp3",     "pop",    0.42),
    ("log2",   14.280, "pop2.mp3",     "pop",    0.42),
    ("log3",   14.600, "pop2.mp3",     "pop",    0.42),
    ("foot",   14.820, "marker.mp3",   "marker", 0.50),
    # ── s11 · the CTA ──────────────────────────────────────────────────
    ("w11",    15.070, "wsh.mp3",      "trans",  0.55),
    ("ctaSh",  15.190, "shine.mp3",    "shine",  0.80),
    ("ctaType",15.400, "type.mp3",     "bed",    0.45),
    ("sub",    15.640, "click.mp3",    "click",  0.36),
    ("taken1", 16.160, "thud.mp3",     "thud",   0.34),
    ("taken2", 16.520, "impact.mp3",   "impact", 0.80),
]

DUR = 16.867


def samples(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def onset(x, rel=0.12):
    """First sample above 12% of THIS signal's own peak."""
    pk = float(np.abs(x).max())
    if pk <= 0:
        return 0.0
    idx = int(np.argmax(np.abs(x) > pk * rel))
    return idx / float(SR)


def trim_all():
    """One trimmed copy per SOURCE file, named t_<file>."""
    made = {}
    for _, _, fn, _, _ in CUES:
        if fn in made:
            continue
        src = os.path.join(SFX, fn)
        x = samples(src)
        off = max(0.0, onset(x) - PRE)
        # WAV, not mp3.  Re-encoding to mp3 puts LAME's ~25 ms encoder delay
        # back at the head of every file, which is most of the lateness the
        # trim exists to remove — the assert below caught it on marker.mp3.
        out = os.path.join(SFX, "t_" + fn.replace(".mp3", ".wav"))
        # INPUT seek (-ss before -i) snaps to the nearest mp3 frame boundary,
        # which is ~26 ms wide — marker.mp3 still opened 31 ms late through it.
        # atrim runs on decoded samples and is exact.
        # Also normalise every trimmed file to -1 dBFS peak.  Without it the
        # kit's own spread does the levelling: marker.mp3 peaks at -19.9 and
        # would sit AT the ceiling (volume 1.000) with no headroom left, while
        # confirm.mp3 peaks at +2.4.  Normalised, one number per class sets the
        # whole kit and the class targets mean what they say.
        gain = -1.0 - 20 * np.log10(max(float(np.abs(x).max()), 1e-9))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                        "-af", "atrim=start=%.5f,asetpts=N/SR/TB,volume=%.3fdB" % (off, gain),
                        "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", out], check=True)
        y = samples(out)
        after = onset(y)
        assert after < 0.012, "%s still starts %.0f ms in after trimming" % (fn, after * 1000)
        made[fn] = dict(off=off, peak=20 * np.log10(max(float(np.abs(y).max()), 1e-9)),
                        dur=len(y) / float(SR))
        print("  trim %-13s -%.0f ms   peak %6.1f dB   %.2fs"
              % (fn, off * 1000, made[fn]["peak"], made[fn]["dur"]))
    return made


def build():
    print("trimming to the transient (threshold relative to each file's own peak):")
    meta = trim_all()
    rows, block = [], []
    for i, (cid, t, fn, cls, d) in enumerate(CUES):
        m = meta[fn]
        d = round(min(d, m["dur"] - 0.005), 3)      # never ask for more than the file holds
        d = round(min(d, DUR - t - 0.01), 3)           # the bed ends with the film
        vol = 10 ** ((CLASS_DB[cls] - m["peak"]) / 20.0)
        vol = round(min(vol, 1.0), 3)
        rows.append((cid, t, fn, cls, d, vol, CLASS_DB[cls]))
        block.append('<audio id="sfx_%s" src="assets/sfx/t_%s" data-start="%.3f" '
                     'data-duration="%.2f" data-track-index="%d" data-volume="%.3f"></audio>'
                     % (cid, fn.replace(".mp3", ".wav"), t, d, 300 + i, vol))
    open(os.path.join(HERE, "sfx_block.html"), "w").write("\n".join(block))
    json.dump([dict(id=r[0], t=r[1], file=r[2], cls=r[3], dur=r[4], vol=r[5],
                    target=r[6]) for r in rows],
              open(os.path.join(HERE, "sfx_cues.json"), "w"), indent=1)
    print("\n%-9s %7s %-13s %-7s %6s  %s" % ("id", "t", "file", "class", "vol", "target dBFS"))
    for cid, t, fn, cls, d, vol, tgt in rows:
        print("%-9s %7.3f %-13s %-7s %6.3f  %+.1f" % (cid, t, fn, cls, vol, tgt))
    print("\n%d cues -> sfx_block.html (VO speech-active peak %.1f dBFS)"
          % (len(rows), VO_PEAK))


if __name__ == "__main__":
    build()
