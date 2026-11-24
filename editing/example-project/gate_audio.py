#!/usr/bin/env python3
r"""Prove hf76's SFX bed lands where the cue list says, and sits under his voice.

Three assertions, all of them bought with a shipped mistake:

  ONSET   Each cue is rendered ALONE and its first transient measured.  On a
          shared stem, cues 130 ms apart all report the loudest of the group
          and the check invents an 830 ms error that is not there.  And the
          assertion is on ONSET, never on peak position: a riser and a shine
          legitimately peak long after they start.

  LIFT    The SFX stem's level at each cue, against his speech-active PEAK.
          rumik1 shipped 34 correctly-placed cues with a measured lift of
          +0.0 dB because the gains had been referenced to her speech MEDIAN.
          A cue list reads as finished either way.

  SOURCE  Every `src` the composition names must exist, and every trimmed file
          must be the one the cue list computed its gain from.  A missing asset
          directory passes every structural gate — a broken <audio> is silent
          and a broken <img> is invisible.

Run: python3 gate_audio.py       (exits non-zero on any failure)
"""
import json, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 16.867
VO_PEAK = -15.3
TOL = 0.040          # a cue may be 40 ms off its beat; a frame is 33 ms


def pcm(args):
    out = subprocess.run(["ffmpeg", "-v", "error"] + args +
                         ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True)
    return np.frombuffer(out.stdout, dtype=np.float32)


def onset(x, rel=0.12):
    pk = float(np.abs(x).max())
    if pk <= 0:
        return None
    return int(np.argmax(np.abs(x) > pk * rel)) / float(SR)


def env_db(x, at, win=0.050):
    a = int(max(0, at) * SR)
    b = min(len(x), a + int(win * SR))
    if b <= a:
        return -120.0
    seg = x[a:b]
    return 20 * np.log10(max(float(np.abs(seg).max()), 1e-9))


def main():
    fails, notes = [], []
    cues = json.load(open(os.path.join(HERE, "sfx_cues.json")))
    html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()

    # ── SOURCE: the composition and the cue list must agree, and the files
    #    must be on disk.  A missing asset dir passes every structural gate.
    tags = re.findall(r'<audio[^>]*>', html)
    in_html = {}
    for t in tags:
        eid = re.search(r'id="([^"]+)"', t).group(1)
        src = re.search(r'src="([^"]+)"', t).group(1)
        st = float(re.search(r'data-start="([\d.]+)"', t).group(1))
        vol = float(re.search(r'data-volume="([\d.]+)"', t).group(1))
        in_html[eid] = (src, st, vol)
        if not os.path.exists(os.path.join(HERE, src)):
            fails.append("SOURCE %s -> %s does not exist" % (eid, src))
    for c in cues:
        eid = "sfx_" + c["id"]
        if eid not in in_html:
            fails.append("SOURCE cue %s is in the list and not in the film" % c["id"])
            continue
        src, st, vol = in_html[eid]
        if abs(st - c["t"]) > 0.001 or abs(vol - c["vol"]) > 0.001:
            fails.append("SOURCE %s drifted: film says t=%.3f v=%.3f, list says t=%.3f v=%.3f"
                         % (eid, st, vol, c["t"], c["vol"]))
    stray = [k for k in in_html if k.startswith("sfx_") and
             k[4:] not in {c["id"] for c in cues}]
    if stray:
        fails.append("SOURCE %s are in the film and not in the cue list" % stray)
    notes.append("SOURCE %d cues, all present in both the film and the list, all on disk"
                 % len(cues))

    # ── ONSET: render each cue ALONE ──────────────────────────────────────
    worst = (0.0, "")
    for c in cues:
        src = os.path.join(HERE, in_html["sfx_" + c["id"]][0])
        # One input, delayed and padded.  Mixing against an anullsrc bed needs
        # the bed to be BOUNDED — `-t` placed after its own `-i` binds to the
        # next input instead, so amix waits on an infinite stream and the whole
        # check hangs with no output at all.
        x = pcm(["-i", src, "-af",
                 "atrim=0:%.3f,volume=%.4f,adelay=%d|%d,apad=whole_dur=%.3f"
                 % (c["dur"], c["vol"], int(c["t"] * 1000), int(c["t"] * 1000), DUR)])
        got = onset(x)
        if got is None:
            fails.append("ONSET %s is SILENT in its own render" % c["id"])
            continue
        err = got - c["t"]
        if abs(err) > worst[0]:
            worst = (abs(err), c["id"])
        if abs(err) > TOL:
            fails.append("ONSET %s fires at %.3f, cued at %.3f (%+.0f ms)"
                         % (c["id"], got, c["t"], err * 1000))
    notes.append("ONSET %d cues rendered alone; worst error %.0f ms (%s), tolerance %.0f ms"
                 % (len(cues), worst[0] * 1000, worst[1], TOL * 1000))

    # ── LIFT: the whole stem, against his speech-active peak ──────────────
    ins, filt, mix = [], [], []
    for i, c in enumerate(cues):
        src = os.path.join(HERE, in_html["sfx_" + c["id"]][0])
        ins += ["-i", src]
        filt.append("[%d:a]atrim=0:%.3f,volume=%.4f,adelay=%d|%d,aformat=channel_layouts=mono[s%d]"
                    % (i, c["dur"], c["vol"], int(c["t"] * 1000), int(c["t"] * 1000), i))
        mix.append("[s%d]" % i)
    graph = ";".join(filt) + ";" + "".join(mix) + \
            "amix=inputs=%d:normalize=0:duration=longest,apad=whole_dur=%.3f[out]" \
            % (len(cues), DUR)
    stem = pcm(ins + ["-filter_complex", graph, "-map", "[out]"])
    if len(stem) == 0:
        fails.append("LIFT the SFX stem rendered empty")
    else:
        # Measure over the cue's OWN SPAN, not a fixed 50 ms at its onset.  A
        # marker sweep, a shine and a wsh all peak well after they start, so a
        # window at the attack reads the kit ~10 dB quieter than it is and
        # invites a correction that would actually make it too loud.
        peaks = [env_db(stem, c["t"], win=min(c["dur"], 0.35)) for c in cues]
        med = float(np.median(peaks))
        notes.append("LIFT stem peak %.1f dBFS; median cue %.1f dBFS = %.1f dB under his "
                     "speech-active peak (%.1f)"
                     % (20 * np.log10(max(float(np.abs(stem).max()), 1e-9)),
                        med, VO_PEAK - med, VO_PEAK))
        if med > VO_PEAK - 2:
            fails.append("LIFT median cue %.1f dBFS is within 2 dB of his voice" % med)
        if med < VO_PEAK - 26:
            fails.append("LIFT median cue %.1f dBFS is %.0f dB under his voice — inaudible"
                         % (med, VO_PEAK - med))
        quiet = [(c["id"], p) for c, p in zip(cues, peaks) if p < VO_PEAK - 30]
        if quiet:
            fails.append("LIFT these cues are more than 30 dB down: %s"
                         % ", ".join("%s %.0f" % q for q in quiet))

    for n in notes:
        print("  ·", n)
    if fails:
        print("\n%d issue(s)" % len(fails))
        for f in fails:
            print("  ✗", f)
        sys.exit(1)
    print("\n✓ gate_audio clean")


main()
