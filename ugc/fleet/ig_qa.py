#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Cross-copy QA for the Instagram copies of one template (brief's 'check before delivering').

For every staged ig/<template>/<igkey>/final.mp4:
  1. format: 1080x1920, H.264, AAC, video bitrate <= 12 Mbps, duration < 90 s (hwy < 125 s)
  2. re-transcribe the FINAL file (whisper, its language): must match its own script (TTS said what we wrote)
  3. pairwise transcript similarity across copies: no two copies share a script (and hooks differ)
  4. audio: md5 of decoded PCM unique; spectral fingerprint bit-error-rate vs every other copy AND vs the
     persona's English TikTok copy of the template: shared audio would show BER well below 0.5
Writes ig/<template>/<igkey>/qa_pass when a copy passes everything; prints a table.
usage: ig_qa.py <template> igkey ...      (the python with numpy = whisper's interpreter)"""
import difflib, hashlib, json, os, subprocess, sys, unicodedata
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IG = os.path.join(HERE, "ig")
ACC = json.load(open(os.path.join(IG, "ig_accounts.json")))["accounts"]
TT = os.path.expanduser("~/masonry-tools/pranks/ugc_in")
LIM = {"highway_explainer": 125}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def pcm(p, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def fingerprint(x, sr=16000):
    """Haitsma-Kalker style: 33 log bands 300-3000 Hz, 2048-pt frames hop 512; bit = sign of band/time energy delta."""
    N, H = 2048, 512
    fr = np.lib.stride_tricks.sliding_window_view(x, N)[::H] * np.hanning(N)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(N, 1 / sr)
    edges = np.geomspace(300, 3000, 34)
    E = np.stack([S[:, (f >= a) & (f < b)].sum(1) for a, b in zip(edges[:-1], edges[1:])], 1) + 1e-12
    d = np.diff(E, axis=1)
    return (d[1:] - d[:-1]) > 0


def ber(a, b, max_shift=120):
    best = 1.0
    for s in range(-max_shift, max_shift + 1, 2):
        x, y = (a[s:], b) if s >= 0 else (a, b[-s:])
        n = min(len(x), len(y))
        if n > 200:
            best = min(best, float(np.mean(x[:n] != y[:n])))
    return best


def chars(s):
    s = unicodedata.normalize("NFKC", s).lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c.isalnum())


def transcribe(p, lang, outdir):
    js = os.path.join(outdir, "final_check.json")
    if not os.path.exists(js) or os.path.getmtime(js) < os.path.getmtime(p):
        wav = os.path.join(outdir, "final_check.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-ac", "1", "-ar", "16000", wav], check=True)
        sys.path.insert(0, HERE)
        from common import local_lock
        with local_lock():     # never alongside a render or another whisper
            subprocess.run(["nice", "-n", "19", "whisper", wav, "--model", "small", "--language", lang, "--output_format", "json",
                            "--output_dir", outdir], check=True, capture_output=True)
    return json.load(open(js))["text"]


def main(tpl, keys):
    scripts = json.load(open(os.path.join(IG, {"gta2_xavier": "gta2_scripts.json", "gta1_jazz": "gta1_scripts.json",
                                                "highway_explainer": "hwy_scripts.json"}[tpl])))
    R, bad = {}, {}
    for k in keys:
        W = os.path.join(IG, tpl, k); p = os.path.join(W, "final.mp4"); a = ACC[k]; bad[k] = []
        v = json.loads(sh("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,bit_rate:format=duration",
                          "-of", "json", p))
        vs = [s for s in v["streams"] if s["codec_type"] == "video"][0]; au = [s for s in v["streams"] if s["codec_type"] == "audio"]
        d = float(v["format"]["duration"])
        if (vs["codec_name"], vs["width"], vs["height"]) != ("h264", 1080, 1920): bad[k].append(f"video {vs['codec_name']} {vs['width']}x{vs['height']}")
        if int(vs.get("bit_rate", 0)) > 12_000_000: bad[k].append(f"bitrate {int(vs['bit_rate']) / 1e6:.1f}M")
        if not au or au[0]["codec_name"] != "aac": bad[k].append("audio not aac")
        if d >= LIM.get(tpl, 90): bad[k].append(f"duration {d:.1f}s")
        heard = transcribe(p, a["lang"], W)
        script = "".join(s for _, s in scripts[k]["segments"]).replace("|", "")
        for sk, sv in scripts[k].get("say", {}).items():   # compare against what the voice was asked to say
            script = script.replace(sk, sv)
        own = difflib.SequenceMatcher(None, chars(script), chars(heard), autojunk=False).ratio()
        if own < 0.80: bad[k].append(f"final transcript matches its script only {own:.2f}")
        x = pcm(p)
        R[k] = dict(dur=d, own=own, heard=heard, script=script, md5=hashlib.md5(x.tobytes()).hexdigest(), fp=fingerprint(x),
                    hook=chars(scripts[k]["segments"][0][1]), lang=a["lang"], persona=a["persona"])
    print(f"{'copy':10s} {'dur':>6s} {'own':>5s}  md5")
    for k in keys:
        print(f"{k:10s} {R[k]['dur']:6.1f} {R[k]['own']:5.2f}  {R[k]['md5'][:12]}")
    print("\npairwise: script similarity (transcripts of the finals) / audio fingerprint BER (0.5 = unrelated)")
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            sim = difflib.SequenceMatcher(None, chars(R[a]["heard"]), chars(R[b]["heard"]), autojunk=False).ratio()
            hs = difflib.SequenceMatcher(None, R[a]["hook"], R[b]["hook"], autojunk=False).ratio()
            br = ber(R[a]["fp"], R[b]["fp"])
            flag = ""
            if R[a]["md5"] == R[b]["md5"]: flag += " SAME-AUDIO-HASH"
            if br < 0.40: flag += " SHARED-AUDIO"
            if sim > 0.75 and R[a]["lang"] == R[b]["lang"]: flag += " SCRIPT-TOO-SIMILAR"
            if hs > 0.70: flag += " SAME-HOOK"
            print(f"  {a:9s} {b:9s} script {sim:.2f}  hook {hs:.2f}  BER {br:.3f}{flag}")
            if flag:
                bad[a].append(f"vs {b}:{flag}"); bad[b].append(f"vs {a}:{flag}")
    print("\nvs the persona's English TikTok copy (same template):")
    for k in keys:
        t = os.path.join(TT, tpl, R[k]["persona"] + ".mp4")
        if os.path.exists(t):
            br = ber(R[k]["fp"], fingerprint(pcm(t)))
            print(f"  {k:9s} vs tiktok/{R[k]['persona']:6s} BER {br:.3f}" + (" SHARED-AUDIO" if br < 0.40 else ""))
            if br < 0.40: bad[k].append("shares audio with its TikTok copy")
    print()
    for k in keys:
        ok = not bad[k]
        f = os.path.join(IG, tpl, k, "qa_pass")
        if ok:
            open(f, "w").write(json.dumps(dict(own=R[k]["own"], md5=R[k]["md5"])))
        elif os.path.exists(f):
            os.remove(f)
        print(f"{k:10s} {'PASS' if ok else 'FAIL ' + '; '.join(bad[k])}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
