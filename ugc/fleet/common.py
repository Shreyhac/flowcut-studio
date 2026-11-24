"""Shared helpers for the 12-account fleet (one AI woman per TikTok account).
Remote work (Masonry) runs in parallel threads; local heavy work (whisper, render) takes LOCAL_LOCK so the
8 GB Mac never runs two at once."""
import difflib, fcntl, json, os, re, shutil, subprocess, threading, time, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
MGTA = os.path.dirname(HERE)
_kf = os.path.expanduser("~/.elevenlabs/key")
EL_KEY = os.environ.get("ELEVENLABS_API_KEY") or (open(_kf).read().strip() if os.path.exists(_kf) else "")
# where finished videos land: <OUT_ROOT>/<template>/<account>.mp4 (default = the posting pipeline's inbox)
OUT_ROOT = os.path.expanduser(os.environ.get("MGTA_OUT", "~/masonry-tools/pranks/ugc_in"))
ACCOUNTS = {a["key"]: a for a in json.load(open(os.path.join(HERE, "accounts.json")))["accounts"]}
_tlock = threading.Lock()


@contextlib.contextmanager
def local_lock():
    """Cross-process lock: one whisper/render/remove-background at a time on this machine."""
    with open(os.path.join(HERE, ".local.lock"), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        warned = False
        while shutil.disk_usage(os.path.expanduser("~")).free < 3 * 1024 ** 3:   # never render into a full disk again
            if not warned:
                log("disk", "free space < 3 GB - holding local work until space frees up"); warned = True
            time.sleep(60)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def log(key, msg):
    with _tlock:
        line = f"{time.strftime('%H:%M:%S')} [{key}] {msg}"
        print(line, flush=True)
        open(os.path.join(HERE, "fleet.log"), "a").write(line + "\n")


def run(*a, **kw):
    return subprocess.run(a, check=True, **kw)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


# ---------- voice ----------
def tts(text, voice, out, speed=1.1, stability=0.45):
    if os.path.exists(out):
        return
    body = json.dumps({"text": text, "model_id": "eleven_multilingual_v2",
                       "voice_settings": {"stability": stability, "similarity_boost": 0.8, "style": 0.35,
                                          "use_speaker_boost": True, "speed": speed}})
    for _ in range(3):
        r = subprocess.run(["curl", "-s", "-X", "POST", f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_192",
                            "-H", f"xi-api-key: {EL_KEY}", "-H", "Content-Type: application/json", "-d", body, "-o", out + ".part"])
        if os.path.exists(out + ".part") and os.path.getsize(out + ".part") > 20000:
            os.rename(out + ".part", out); return
        time.sleep(5)
    raise RuntimeError(f"TTS failed for {out}: {open(out + '.part', errors='ignore').read()[:300]}")


def tighten(src, dst, keep_face=0.24, keep_rest=0.30, face_until=17.0):
    """Cap pauses using silencedetect geometry (never whisper boundaries), then loudness-normalise the voice."""
    if os.path.exists(dst):
        return
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", src, "-af", "silencedetect=noise=-35dB:d=0.15", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    cuts = []
    for s0, s1 in zip(st, en):
        keep = keep_face if s0 < face_until else keep_rest
        if s1 - s0 > keep + 0.08:
            rm = (s1 - s0) - keep; mid = (s0 + s1) / 2
            cuts.append((mid - rm / 2, mid + rm / 2))
    pieces, t = [], 0.0
    for a, b in cuts:
        pieces.append((t, a)); t = b
    pieces.append((t, None))
    parts = [f"[0]atrim=start={a:.3f}" + (f":end={b:.3f}" if b is not None else "") + f",asetpts=PTS-STARTPTS[p{i}]"
             for i, (a, b) in enumerate(pieces)]
    f = ";".join(parts) + ";" + "".join(f"[p{i}]" for i in range(len(pieces))) + \
        f"concat=n={len(pieces)}:v=0:a=1,loudnorm=I=-15:TP=-2:LRA=9,aresample=44100[o]"
    run("ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", f, "-map", "[o]", dst)


def whisper_words(wav16, outdir):
    js = os.path.join(outdir, os.path.splitext(os.path.basename(wav16))[0] + ".json")
    if not os.path.exists(js):
        with local_lock():
            run("nice", "-n", "19", "whisper", wav16, "--model", "small", "--language", "en", "--word_timestamps", "True",
                "--output_format", "json", "--output_dir", outdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.load(open(js))
    return [dict(t=w["word"].strip(), s=w["start"], e=w["end"]) for s in d["segments"] for w in s["words"]]


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def align(script_text, wwords):
    """Script words carry the TEXT, whisper words carry the TIMING. Unmatched script words get interpolated times,
    so a whisper mishearing ('the skill' for 'this skill') can never reach a caption."""
    sw = script_text.split()
    a = [norm(x) for x in sw]; b = [norm(x["t"]) for x in wwords]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    times = [None] * len(sw)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                times[i1 + k] = (wwords[j1 + k]["s"], wwords[j1 + k]["e"])
        elif tag == "replace":
            s, e = wwords[j1]["s"], wwords[j2 - 1]["e"]
            n = i2 - i1
            for k in range(n):
                times[i1 + k] = (s + (e - s) * k / n, s + (e - s) * (k + 1) / n)
    # fill any gaps (script words whisper dropped) by interpolating between neighbours
    for i in range(len(sw)):
        if times[i] is None:
            prev = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), 0.0)
            nxt = next((times[j][0] for j in range(i + 1, len(sw)) if times[j]), prev + 0.3)
            times[i] = (prev, max(prev + 0.05, (prev + nxt) / 2))
    return [dict(word=w, start=round(t[0], 3), end=round(t[1], 3)) for w, t in zip(sw, times)]


def first_word_time(words, word, after=0.0):
    for w in words:
        if w["start"] >= after and norm(w["word"]) == word.lower():
            return w["start"]
    raise KeyError(word)


# ---------- masonry ----------
_submit_lock = threading.Lock()


def masonry_submit(args):
    """Serialised: parallel submits with local uploads time out client-side and the job never exists."""
    with _submit_lock:
        return _submit(args)


def _submit(args):
    attempt, waited = 0, 0
    while attempt < 4:
        r = subprocess.run(["masonry", *args], capture_output=True, text=True)
        m = re.search(r'"job_id":\s*"([^"]+)"', r.stdout)
        if m:
            return m.group(1)
        out = r.stdout + r.stderr
        msg = " ".join(re.findall(r'"message":\s*"([^"]{0,200})', out))
        if "CONCURRENCY_LIMIT" in out:          # Starter plan: 3 generations at once -> wait for a slot, not an error
            if waited > 8 * 3600:
                raise RuntimeError("waited 8h for a Masonry generation slot")
            time.sleep(45); waited += 45
            continue
        if "credit" in msg.lower():
            raise RuntimeError("OUT OF CREDITS: " + msg)
        attempt += 1
        time.sleep(20 * attempt)
    raise RuntimeError("masonry submit failed: " + (r.stdout + r.stderr)[-400:])


def masonry_wait(job, dst, timeout="40m"):
    if os.path.exists(dst):
        return dst
    r = subprocess.run(["masonry", "job", "wait", job, "--timeout", timeout, "--download", "-o", dst, "--overwrite"],
                       capture_output=True, text=True)
    if not os.path.exists(dst):
        raise RuntimeError(f"job {job} produced nothing: " + (r.stdout + r.stderr)[-400:])
    return dst


def cached_job(state_file, name, submit_args, dst, timeout="40m"):
    """Submit once (job id remembered on disk so a crash/restart never pays twice), then wait + download."""
    if os.path.exists(dst):
        return dst
    st = json.load(open(state_file)) if os.path.exists(state_file) else {}
    if name not in st:
        st[name] = masonry_submit(submit_args)
        json.dump(st, open(state_file, "w"), indent=1)
    return masonry_wait(st[name], dst, timeout)


WALK_PROMPT = ("Handheld iPhone front-camera selfie video. The woman walks slowly along the shoreline while chatting happily "
               "to the phone like a confident, upbeat TikTok creator sharing a tip: relaxed face, warm genuine smile between "
               "phrases, bright eyes, eyebrows raised with excitement, natural mouth movement as she talks, wind moving loose "
               "strands of her hair. The phone bobs gently with her steps. Real ocean waves keep rolling in and breaking with "
               "white foam behind her. Same woman, same outfit, same lighting throughout. Realistic, no cuts, no zoom.")
WALK_NEG = "frowning, furrowed brows, squinting, crying, sad, distressed, pained expression, extra fingers"


def last_frame(mp4, png):
    n = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", mp4], capture_output=True, text=True).stdout)
    run("ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", f"select=eq(n\\,{n - 1})", "-fps_mode", "vfr", "-frames:v", "1", png)


def talking_face(key, workdir, start_png, speech_mp3, out_mp4, tag=""):
    """Walking-selfie clip long enough for the speech (H3 15s, + continuation from its last frame if needed),
    lip-synced to the speech with Sync Lipsync 3. Returns out_mp4 (768x1344, speech length)."""
    if os.path.exists(out_mp4):
        return out_mp4
    st = os.path.join(workdir, "jobs.json")
    need = dur(speech_mp3)
    a = cached_job(st, tag + "walkA", ["video", WALK_PROMPT, "-m", "minimax-h3-max", "-i", start_png, "--duration", "15",
                                 "--no-audio", "--negative-prompt", WALK_NEG], os.path.join(workdir, tag + "walkA.mp4"))
    clips = [a]
    if need > dur(a) * 1.05:
        lf = os.path.join(workdir, tag + "walkA_last.png")
        if not os.path.exists(lf):
            last_frame(a, lf)
        more = min(15, max(5, int(need - dur(a) + 1.99)))
        b = cached_job(st, tag + "walkB", ["video", WALK_PROMPT, "-m", "minimax-h3-max", "-i", lf, "--duration", str(more),
                                     "--no-audio", "--negative-prompt", WALK_NEG], os.path.join(workdir, tag + "walkB.mp4"))
        clips.append(b)
    joined = os.path.join(workdir, tag + "walk_joined.mp4")
    if not os.path.exists(joined):
        if len(clips) == 1:
            k = max(1.0, need / dur(a))   # stretch <=5% when the speech runs a hair long
            run("ffmpeg", "-v", "error", "-y", "-i", a, "-an", "-vf", f"setpts={k:.5f}*PTS", "-t", f"{need:.3f}",
                "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", joined)
        else:
            run("ffmpeg", "-v", "error", "-y", "-i", clips[0], "-i", clips[1], "-filter_complex",
                f"[1:v]trim=start_frame=1,setpts=PTS-STARTPTS[b];[0:v][b]concat=n=2:v=1:a=0,trim=0:{need:.3f},setpts=PTS-STARTPTS[v]",
                "-map", "[v]", "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", joined)
    log(key, f"walk ready {dur(joined):.2f}s for {need:.2f}s speech -> lip-sync")
    cached_job(st, tag + "lipsync", ["video", "lip-sync her mouth to the speech", "-m", "sync-lipsync-v3", "--source-video", joined,
                               "--speech", speech_mp3, "--set", '{"lipsync_mode":"cut_off"}'], out_mp4, timeout="60m")
    return out_mp4


def to_1080(src, dst, fps=30):
    if not os.path.exists(dst):
        run("ffmpeg", "-v", "error", "-y", "-i", src, "-an", "-vf",
            f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps={fps}",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-g", "15", "-keyint_min", "15", dst)
    return dst


def luma_qa(mp4, allow_black=()):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf", "scale=54:96,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    n = 54 * 96
    L = [sum(raw[i:i + n]) / n for i in range(0, len(raw) - n + 1, n)]
    black = [i / 30 for i, v in enumerate(L) if v < 6 and not any(a <= i / 30 <= b for a, b in allow_black)]
    spikes = [i / 30 for i in range(1, len(L) - 1) if abs(L[i] - L[i - 1]) > 18 and abs(L[i] - L[i + 1]) > 18
              and (L[i] - L[i - 1]) * (L[i] - L[i + 1]) > 0]
    return black, spikes


def cleanup_after_delivery(W):
    """Free disk: the delivered file is the product; raw render + per-build assets regenerate from cached jobs."""
    for p in [os.path.join(W, "render_raw.mp4")]:
        if os.path.exists(p):
            os.remove(p)
    A = os.path.join(W, "hf", "assets")
    if os.path.isdir(A):
        for fn in os.listdir(A):
            if fn.endswith((".mp4", ".wav")):
                os.remove(os.path.join(A, fn))
