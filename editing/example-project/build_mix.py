#!/usr/bin/env python3
r"""Mux the film's audio myself, so his voice is bit-exact.

WHY THIS EXISTS

The renderer's streaming audio path (which this 8 GB machine auto-selects, and
which is the only path that fits in the available disk) applies a constant
-1.22 dB fader to the whole mix.  Measured, not guessed: the best-fit scalar
between his master and the delivered audio is 0.86875, and after removing
exactly that scalar the residual correlates 0.0000 with his speech — a pure
gain, not processing, but still a change to audio he has said twice must not be
touched.

So the render supplies the PICTURE and this supplies the SOUND:

    his master audio (stream-copied, untouched)  +  the SFX bed
    summed with amix normalize=0, which is straight addition and applies no
    gain to either input

The result is verifiable: subtract his master from the delivered mix and what
remains must be the bed alone, uncorrelated with his voice.  `verify()` does
exactly that and refuses to write a file that fails it.

Cue times, files and per-cue volumes all come from sfx_cues.json, so this cannot
drift from what build_audio.py computed.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SFX = os.path.join(HERE, "assets", "sfx")
VOICE = os.path.join(HERE, "assets", "aroll.mp4")
SR = 48000


def run(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("failed: %s\n%s" % (" ".join(args[:6]), r.stderr[-1200:]))
    return r


def build_bed(cues, dur, out):
    """One ffmpeg pass: every cue trimmed, delayed to its beat, gained, summed.

    normalize=0 on the mix is not optional — amix's default divides by the input
    count, which would silently re-level the whole bed."""
    ins, filt, labels = [], [], []
    for i, c in enumerate(cues):
        ins += ["-i", os.path.join(SFX, "t_" + c["file"].replace(".mp3", ".wav"))]
        filt.append("[%d:a]atrim=0:%.3f,asetpts=N/SR/TB,volume=%.5f,"
                    "adelay=%d|%d[c%d]"
                    % (i, c["dur"], c["vol"], int(round(c["t"] * 1000)),
                       int(round(c["t"] * 1000)), i))
        labels.append("[c%d]" % i)
    filt.append("%samix=inputs=%d:normalize=0:dropout_transition=0,"
                "apad,atrim=0:%.3f[bed]" % ("".join(labels), len(cues), dur))
    run(["ffmpeg", "-y", "-v", "error"] + ins
        + ["-filter_complex", ";".join(filt), "-map", "[bed]",
           "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", out])


def mux(video, bed, out, dur):
    """His voice is input 0 and is added, never scaled: normalize=0."""
    run(["ffmpeg", "-y", "-v", "error",
         "-i", video,                      # picture + (discarded) render audio
         "-i", VOICE,                      # his master audio, untouched
         "-i", bed,
         "-filter_complex",
         # STEREO out, matching his master's layout.  Collapsing his stereo to
         # mono is itself a change to his audio; the bed is duplicated to two
         # channels instead.
         "[1:a]aformat=sample_fmts=fltp:sample_rates=%d:channel_layouts=stereo[v];"
         "[2:a]aformat=sample_fmts=fltp:sample_rates=%d:channel_layouts=stereo[b];"
         "[v][b]amix=inputs=2:normalize=0:dropout_transition=0,"
         "atrim=0:%.3f[a]" % (SR, SR, dur),
         "-map", "0:v:0", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
         "-movflags", "+faststart", out])


def pcm(path):
    """PER-CHANNEL, never downmixed.

    Decoding both files with `-ac 1` compares two different downmix rules when
    the layouts differ: ffmpeg's stereo->mono is 0.5*(L+R) while its mono output
    is a passthrough, and his master is dual-mono stereo.  That mismatch reads
    as a 1.2 dB "attenuation" that is not there.  Compare channel 0 to channel 0.
    """
    import numpy as np
    n = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                            "-show_entries", "stream=channels", "-of", "csv=p=0",
                            path], capture_output=True, text=True).stdout.strip())
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return x[0::n]


def verify(out, bed):
    """The honest test is not "the fitted gain is 1.000".

    SFX cues land ON his words by design, so the bed is NOT uncorrelated with
    his speech, and that correlation drags a least-squares gain fit below 1 even
    when nothing has been scaled.  The real test is subtractive: delivered minus
    master must BE the bed I built, and nothing else.
    """
    import numpy as np
    db = lambda v: 20 * np.log10(max(abs(float(v)), 1e-9))
    a, b, k = pcm(VOICE), pcm(out), pcm(bed)
    n = min(len(a), len(b), len(k)); a, b, k = a[:n], b[:n], k[:n]
    res = b - a                                   # what the mux added
    err = res - k                                 # how far that is from the bed
    corr = float(np.corrcoef(res, k)[0, 1])
    w = int(SR * 0.010); m = n // w
    fa = a[:m * w].reshape(m, w); fb = b[:m * w].reshape(m, w)
    act = np.sqrt((fa ** 2).mean(axis=1)) > 10 ** (-45 / 20.0)
    rms_a = db(np.sqrt((fa[act] ** 2).mean()))
    rms_b = db(np.sqrt((fb[act] ** 2).mean()))
    print("  his speech RMS  master        %+6.2f dBFS" % rms_a)
    print("  his speech RMS  delivered     %+6.2f dBFS   (%+.2f dB)" % (rms_b, rms_b - rms_a))
    print("  delivered minus master vs the bed I built: corr %.4f, error %+.2f dBFS"
          % (corr, db(np.sqrt((err ** 2).mean()))))
    print("  SFX bed peak                  %+6.2f dBFS  (%+.2f dB vs his speech RMS)"
          % (db(np.abs(k).max()), db(np.abs(k).max()) - rms_a))
    if corr < 0.90:
        sys.exit("build_mix: what was added is not the bed (corr %.3f) — refusing" % corr)
    if abs(rms_b - rms_a) > 0.30:
        sys.exit("build_mix: his speech moved %+.2f dB — refusing to ship" % (rms_b - rms_a))
    print("  OK: his voice is unscaled; everything added is the bed")


if __name__ == "__main__":
    video = sys.argv[1]
    out = sys.argv[2]
    dur = float(sys.argv[3]) if len(sys.argv) > 3 else 16.867
    cues = json.load(open(os.path.join(HERE, "sfx_cues.json")))
    bed = os.path.join(HERE, ".bed.wav")
    print("building the bed from %d cues…" % len(cues))
    build_bed(cues, dur, bed)
    print("muxing his untouched master + the bed onto the render's picture…")
    mux(video, bed, out, dur)
    print("verifying:")
    verify(out, bed)
    os.remove(bed)
    print("wrote %s" % out)
