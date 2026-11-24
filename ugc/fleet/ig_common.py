"""Instagram (non-English) copies: shared helpers on top of common.py.

- whisper in the account's language (common.whisper_words hard-codes --language en)
- char-level alignment: script text carries the words, whisper carries the timing; works for languages
  without spaces (Japanese) because it matches characters, not words
- talking face in two parts (opening + CTA) from ONE lip-sync job over two cached, already-paid silent walk
  clips of the persona (no new walk generation)
"""
import difflib, json, os, re, subprocess, unicodedata
from common import *

IG = os.path.join(HERE, "ig")
IG_ACC = json.load(open(os.path.join(IG, "ig_accounts.json")))["accounts"]
IG_OUT = os.path.expanduser(os.environ.get("IG_OUT", "~/masonry-tools/insta/ig_in"))


def whisper_lang(wav16, outdir, lang, model="small"):
    js = os.path.join(outdir, os.path.splitext(os.path.basename(wav16))[0] + f".{model}.json")
    if not os.path.exists(js):
        with local_lock():
            run("nice", "-n", "19", "whisper", wav16, "--model", model, "--language", lang, "--word_timestamps", "True",
                "--output_format", "json", "--output_dir", outdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(os.path.join(outdir, os.path.splitext(os.path.basename(wav16))[0] + ".json"), js)
    d = json.load(open(js))
    return [dict(t=w["word"], s=w["start"], e=w["end"]) for s in d["segments"] for w in s["words"]], \
        "".join(s["text"] for s in d["segments"])


def nchars(s):
    """Comparable characters: NFKC (full-width -> ascii), accents stripped, lower case, letters/digits only."""
    s = unicodedata.normalize("NFKC", s).lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return [c for c in s if c.isalnum()]


def script_units(segments, lang, say=None):
    """-> units [{text, seg}] (a word for space languages, a '|' phrase for ja) and the TTS text.
    say: {caption text: spoken text} - e.g. '3.500' is captioned as digits but voiced 'tres mil quinientos'."""
    units, tts_parts = [], []
    for si, (beat, seg) in enumerate(segments):
        parts = [p for p in seg.split("|")] if lang == "ja" else seg.split()
        for p in parts:
            if p.strip():
                units.append(dict(text=p.strip(), seg=si, beat=beat))
        spoken = seg.replace("|", "")
        for k, v in (say or {}).items():
            spoken = spoken.replace(k, v)
        tts_parts.append(spoken)
    return units, (" " if lang != "ja" else "").join(tts_parts)


def align_units(units, wwords):
    """Give every unit (start, end) by matching its characters against whisper's characters."""
    sc, su = [], []
    for i, u in enumerate(units):
        for c in nchars(u["text"]):
            sc.append(c); su.append(i)
    wc, wt = [], []
    for w in wwords:
        cs = nchars(w["t"])
        for k, c in enumerate(cs):   # spread a word's time over its characters
            a = w["s"] + (w["e"] - w["s"]) * k / len(cs); b = w["s"] + (w["e"] - w["s"]) * (k + 1) / len(cs)
            wc.append(c); wt.append((a, b))
    t = [None] * len(sc)
    sm = difflib.SequenceMatcher(None, sc, wc, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                t[i1 + k] = wt[j1 + k]
        elif tag == "replace":       # different spellings ('GTA seis' vs 'GTA 6'): spread the span evenly
            s, e = wt[j1][0], wt[j2 - 1][1]; n = i2 - i1
            for k in range(n):
                t[i1 + k] = (s + (e - s) * k / n, s + (e - s) * (k + 1) / n)
    out = []
    for i, u in enumerate(units):
        ts = [t[k] for k in range(len(sc)) if su[k] == i and t[k]]
        out.append(dict(u, start=ts[0][0] if ts else None, end=ts[-1][1] if ts else None,
                        matched=len(ts), chars=sum(1 for k in su if k == i)))
    for i, u in enumerate(out):      # units whisper missed entirely: interpolate between neighbours
        if u["start"] is None:
            prev = next((out[j]["end"] for j in range(i - 1, -1, -1) if out[j]["end"] is not None), 0.0)
            nxt = next((out[j]["start"] for j in range(i + 1, len(out)) if out[j]["start"] is not None), prev + 0.3)
            u["start"], u["end"] = prev, max(prev + 0.05, (prev + nxt) / 2)
    for i in range(1, len(out)):     # monotonic
        out[i]["start"] = max(out[i]["start"], out[i - 1]["start"] + 0.02)
        out[i]["end"] = max(out[i]["end"], out[i]["start"] + 0.05)
    return [dict(u, start=round(u["start"], 3), end=round(u["end"], 3)) for u in out]


def seg_starts(aligned):
    st = {}
    for u in aligned:
        st.setdefault(u["beat"], u["start"])
    return st


def two_part_face(key, workdir, walk_a, walk_b, b_off, speech_a, speech_b, out_a, out_b):
    """One Sync Lipsync 3 job: [walk_a cut to speech_a] + [walk_b from b_off cut to speech_b] lip-synced to
    speech_a+speech_b, then split back at the joint. Walk clips are silent, cached, already paid for."""
    if os.path.exists(out_a) and os.path.exists(out_b):
        return
    la, lb = dur(speech_a), dur(speech_b)
    assert la <= dur(walk_a) - 0.05, f"{key}: opening speech {la:.2f}s longer than walk {dur(walk_a):.2f}s"
    assert b_off + lb <= dur(walk_b) - 0.05, f"{key}: CTA speech {lb:.2f}s does not fit walk B from {b_off}s"
    speech = os.path.join(workdir, "face_speech.mp3")
    if not os.path.exists(speech):
      with local_lock():
        run("ffmpeg", "-v", "error", "-y", "-i", speech_a, "-i", speech_b, "-filter_complex",
            "[0:a][1:a]concat=n=2:v=0:a=1[o]", "-map", "[o]", "-c:a", "libmp3lame", "-b:a", "192k", speech)
    joined = os.path.join(workdir, "walk_joined.mp4")
    if not os.path.exists(joined):
      with local_lock():
        tot = dur(speech)
        run("ffmpeg", "-v", "error", "-y", "-i", walk_a, "-ss", f"{b_off:.3f}", "-i", walk_b, "-filter_complex",
            f"[0:v]trim=0:{la:.4f},setpts=PTS-STARTPTS,fps=24,scale=768:1344[a];"
            f"[1:v]trim=0:{lb + 0.2:.4f},setpts=PTS-STARTPTS,fps=24,scale=768:1344[b];"
            f"[a][b]concat=n=2:v=1:a=0,trim=0:{tot:.4f},setpts=PTS-STARTPTS[v]", "-map", "[v]",
            "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", joined)
    log(key, f"walk joined {dur(joined):.2f}s for {la:.2f}+{lb:.2f}s speech -> lip-sync")
    ls = os.path.join(workdir, "face_lipsync.mp4")
    cached_job(os.path.join(workdir, "jobs.json"), "ig_lipsync",
               ["video", "lip-sync her mouth to the speech", "-m", "sync-lipsync-v3", "--source-video", joined,
                "--speech", speech, "--set", '{"lipsync_mode":"cut_off"}'], ls, timeout="60m")
    with local_lock():
      run("ffmpeg", "-v", "error", "-y", "-i", ls, "-t", f"{la:.4f}", "-an", "-c:v", "libx264", "-crf", "14",
        "-pix_fmt", "yuv420p", out_a)
      run("ffmpeg", "-v", "error", "-y", "-ss", f"{la:.4f}", "-i", ls, "-an", "-c:v", "libx264", "-crf", "14",
        "-pix_fmt", "yuv420p", out_b)


def multi_part_face(key, workdir, parts, outs):
    """ONE Sync Lipsync 3 job for several face beats. parts = [(speech_mp3, walk_clip, offset_s)], each beat's speech
    laid over its own stretch of an already-paid silent walk clip; the lip-synced result is split back into outs."""
    if all(os.path.exists(o) for o in outs):
        return
    lens = [dur(s) for s, _, _ in parts]
    for (s, clip, off), L in zip(parts, lens):
        assert off + L <= dur(clip) - 0.05, f"{key}: {L:.2f}s beat does not fit {os.path.basename(clip)} from {off:.2f}s"
    speech = os.path.join(workdir, "face_speech.mp3")
    joined = os.path.join(workdir, "walk_joined.mp4")
    with local_lock():
        if not os.path.exists(speech):
            ins = sum([["-i", s] for s, _, _ in parts], [])
            run("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex",
                "".join(f"[{i}:a]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[o]", "-map", "[o]",
                "-c:a", "libmp3lame", "-b:a", "192k", speech)
        if not os.path.exists(joined):
            ins = sum([["-ss", f"{off:.3f}", "-i", clip] for _, clip, off in parts], [])
            fc = ";".join(f"[{i}:v]trim=0:{L + (0.2 if i == len(parts) - 1 else 0):.4f},setpts=PTS-STARTPTS,fps=24,scale=768:1344[v{i}]"
                          for i, L in enumerate(lens))
            fc += ";" + "".join(f"[v{i}]" for i in range(len(parts))) + \
                  f"concat=n={len(parts)}:v=1:a=0,trim=0:{dur(speech):.4f},setpts=PTS-STARTPTS[v]"
            run("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[v]",
                "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", joined)
    log(key, f"walk joined {dur(joined):.2f}s for " + "+".join(f"{L:.2f}" for L in lens) + "s speech -> lip-sync")
    ls = os.path.join(workdir, "face_lipsync.mp4")
    cached_job(os.path.join(workdir, "jobs.json"), "ig_lipsync",
               ["video", "lip-sync her mouth to the speech", "-m", "sync-lipsync-v3", "--source-video", joined,
                "--speech", speech, "--set", '{"lipsync_mode":"cut_off"}'], ls, timeout="60m")
    with local_lock():
        t = 0.0
        for L, o in zip(lens, outs):
            run("ffmpeg", "-v", "error", "-y", "-ss", f"{t:.4f}", "-t", f"{L:.4f}", "-i", ls, "-an", "-c:v", "libx264", "-crf", "14",
                "-pix_fmt", "yuv420p", o)
            t += L


def tighten_ig(src, dst, keep=0.28):
    """common.tighten's pause cuts, plus a fixed pre-gain that brings the take's median speech level to -20 dBFS before
    loudnorm. Some voices (Liza, sofia) come out of ElevenLabs ~20 dB quieter; loudnorm's dynamic mode then pumps up to
    +24 dB and smears quiet phrase endings ('empezar hoy' -> 'tempe...'). Timing is identical to common.tighten."""
    if os.path.exists(dst):
        return
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    import array, math
    a = array.array("h", raw); h = 800; dbs = []
    for i in range(0, len(a) - h, h):
        s = sum(v * v for v in a[i:i + h]) / h
        d = 10 * math.log10(s / 32768 ** 2 + 1e-12)
        if d > -50:
            dbs.append(d)
    dbs.sort(); med = dbs[len(dbs) // 2] if dbs else -20
    pre = max(0.0, min(30.0, -20.0 - med))
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", src, "-af", "silencedetect=noise=-35dB:d=0.15", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    cuts = []
    for s0, s1 in zip(st, en):
        if s1 - s0 > keep + 0.08:
            rm = (s1 - s0) - keep; mid = (s0 + s1) / 2
            cuts.append((mid - rm / 2, mid + rm / 2))
    pieces, t = [], 0.0
    for x, y in cuts:
        pieces.append((t, x)); t = y
    pieces.append((t, None))
    parts = [f"[0]atrim=start={x:.3f}" + (f":end={y:.3f}" if y is not None else "") + f",asetpts=PTS-STARTPTS[p{i}]"
             for i, (x, y) in enumerate(pieces)]
    f = ";".join(parts) + ";" + "".join(f"[p{i}]" for i in range(len(pieces))) + \
        f"concat=n={len(pieces)}:v=0:a=1,volume={pre:.1f}dB,loudnorm=I=-15:TP=-2:LRA=9,aresample=44100[o]"
    run("ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", f, "-map", "[o]", dst)
    log("tighten", f"{os.path.basename(os.path.dirname(os.path.dirname(dst)))}: median {med:.1f} dB, pre-gain {pre:.1f} dB")


def fresh_1080(src, dst):
    """to_1080, but regenerate when the source is newer (a re-voiced copy must never keep its old lip-sync)."""
    if os.path.exists(dst) and os.path.getmtime(dst) < os.path.getmtime(src):
        os.remove(dst)
    return to_1080(src, dst)
