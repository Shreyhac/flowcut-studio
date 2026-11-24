#!/usr/bin/env python3
"""Highway explainer x 12 accounts -> ~/masonry-tools/pranks/ugc_in/highway_explainer/<key>.mp4.
Per account: VO -> aligned words + beat starts; 3 silent reaction clips -> cut-outs -> ping-pong PiP over the 78s hook;
the three face beats (H1, H5, H11-12) from ONE lip-synced walking clip, split. Restartable. usage: python3 hwy.py [key ...]"""
import concurrent.futures as cf, json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

TPL = "highway_explainer"
DELIV = os.path.join(OUT_ROOT, TPL)
SHARED = os.path.join(HERE, TPL, "_shared"); os.makedirs(SHARED, exist_ok=True)
# script as written by the owner, with the "$1 to $12,000" typo corrected to match the Google clip and the reference VO
SCRIPT = ('You just watched that whole video, didn\'t you? So did thirty-one million other people. And according to Google, '
          'YouTube pays one thousand to twelve thousand dollars for just a million views. So if we do some quick math, just this '
          'video alone made over six figures. And this is exactly how you\'re going to do it, too. First, copy the link. Then head '
          'over to Masonry A.I. Paste in your link, then just paste this exact prompt. Just like that, you have an AI-generated '
          'video of exactly what you wanted. All you have to do is start posting three times a day and start raking in the views. '
          'If that wasn\'t clear enough, comment "story" and I\'ll personally DM you to help you get started today.')
REACT = ("Handheld iPhone front-camera video. The woman stands still on the beach holding her phone at chest height and watches "
         "a funny video on it, glancing between the phone screen and the camera, reacting silently with natural changing "
         "expressions: curious, surprised, amused smirk, raised eyebrows, a small laugh. She does not speak. Camera steady, "
         "waves moving softly behind her. Same woman, same outfit, same lighting throughout. Realistic, no cuts, no zoom.")
REACT_VARIANTS = ["", " Mostly amused and laughing toward the end.", " Mostly shocked, mouth open, then a disbelieving laugh."]


def shared_setup():
    hook30 = os.path.join(SHARED, "hook30.mp4")
    if not os.path.exists(hook30):
        run("ffmpeg", "-v", "error", "-y", "-i", os.path.join(MGTA, "assets.noindex", "hwy", "hook.mp4"), "-an", "-vf", "fps=30",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:v", "libx264", "-crf", "17",
            "-pix_fmt", "yuv420p", hook30)
    bed = os.path.join(MGTA, "ref.noindex", "sep", "htdemucs", "hwy_body", "no_vocals.wav")
    if not os.path.exists(bed):
        body = os.path.join(MGTA, "ref.noindex", "hwy_body.wav")
        run("ffmpeg", "-v", "error", "-y", "-ss", "73.4", "-i", os.path.join(MGTA, "ref.noindex", "hwy.mp4"), "-vn", "-ac", "2", "-ar", "44100", body)
        with local_lock():
            run("nice", "-n", "19", "uvx", "--python", "3.11", "--from", "demucs", "--with", "torchaudio<2.9", "--with", "soundfile",
                "demucs", "-d", "cpu", "--two-stems", "vocals", "-o", os.path.join(MGTA, "ref.noindex", "sep"), body,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return hook30


def phrase_sub(words, spoken, shown):
    """Replace a spoken phrase with its display form for captions, keeping its timing."""
    sp = [norm(x) for x in spoken.split()]
    out, i = [], 0
    while i < len(words):
        if [norm(w["word"]) for w in words[i:i + len(sp)]] == sp:
            out.append(dict(word=shown, start=words[i]["start"], end=words[i + len(sp) - 1]["end"])); i += len(sp)
        else:
            out.append(words[i]); i += 1
    return out


def one(key, idx, hook30):
    a = ACCOUNTS[key]
    W = os.path.join(HERE, TPL, key); vo = os.path.join(W, "vo"); gen = os.path.join(W, "gen"); hf = os.path.join(W, "hf")
    for d in (vo, gen, os.path.join(hf, "assets", "fonts")):
        os.makedirs(d, exist_ok=True)
    final = os.path.join(DELIV, key + ".mp4")
    if os.path.exists(final):
        return key, "already delivered"
    avatar = os.path.join(HERE, "avatars", key + ".png")
    st = os.path.join(gen, "jobs.json")
    # reaction clips go to Masonry first (they don't depend on the voice)
    react_jobs = []
    for r in range(3):
        dst = os.path.join(gen, f"react{r}.mp4")
        if not os.path.exists(dst):
            j = json.load(open(st)) if os.path.exists(st) else {}
            if f"react{r}" not in j:
                j[f"react{r}"] = masonry_submit(["video", REACT + REACT_VARIANTS[r], "-m", "minimax-h3-max", "-i", avatar,
                                                 "--duration", "10", "--no-audio", "--negative-prompt", "talking, crying, distressed, extra fingers"])
                json.dump(j, open(st, "w"), indent=1)
            react_jobs.append((j[f"react{r}"], dst))
    # voice
    tts(SCRIPT, a["voice"], os.path.join(vo, "vo_full.mp3"))
    tighten(os.path.join(vo, "vo_full.mp3"), os.path.join(vo, "vo_tight.wav"), keep_face=0.3, keep_rest=0.3)
    w16 = os.path.join(vo, "vo_tight16.wav")
    if not os.path.exists(w16):
        run("ffmpeg", "-v", "error", "-y", "-i", os.path.join(vo, "vo_tight.wav"), "-ac", "1", "-ar", "16000", w16)
    words = align(SCRIPT, whisper_words(w16, vo))
    f = lambda w, after=0.0: first_word_time(words, w, after)
    segs = {"face1": 0.0}
    segs["viewcount"] = f("so", f("didn't"))
    segs["google"] = f("and", f("people"))
    segs["calculator"] = f("so", f("views"))
    segs["face2"] = f("and", f("figures"))
    segs["copylink"] = f("first")
    segs["masonry"] = f("then", segs["copylink"])
    segs["paste"] = f("paste", segs["masonry"])
    segs["prompt"] = f("then", segs["paste"])
    segs["result"] = f("just", f("prompt"))
    segs["face3"] = f("all", segs["result"])
    VO_LEN = dur(os.path.join(vo, "vo_tight.wav"))
    lead = lambda t: max(0.0, t - 0.06)
    for k in list(segs):
        if k != "face1":
            segs[k] = round(lead(segs[k]), 3)
    json.dump(segs, open(os.path.join(vo, "segs.json"), "w"), indent=1)
    cw = phrase_sub(phrase_sub(words, "thirty-one million", "31 million"), "one thousand to twelve thousand dollars", "$1,000 to $12,000")
    json.dump(cw, open(os.path.join(vo, "caption_words.json"), "w"), indent=0)
    # face speech = the three face beats back to back
    parts = [(0.0, segs["viewcount"]), (segs["face2"], segs["copylink"]), (segs["face3"], VO_LEN)]
    speech = os.path.join(gen, "face_speech.mp3")
    if not os.path.exists(speech):
        fc = ";".join(f"[0]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS[p{i}]" for i, (s, e) in enumerate(parts))
        run("ffmpeg", "-v", "error", "-y", "-i", os.path.join(vo, "vo_tight.wav"), "-filter_complex",
            fc + ";[p0][p1][p2]concat=n=3:v=0:a=1[o]", "-map", "[o]", "-c:a", "libmp3lame", "-b:a", "192k", speech)
    log(key, f"HWY VO ready, face speech {dur(speech):.1f}s")
    lips = talking_face(key, gen, avatar, speech, os.path.join(gen, "f_face_lipsync.mp4"), "f_")
    # split back into the three beats; face1 holds its first frame through the 0.2s before the first line
    off = 0.0; faces = []
    for i, (s, e) in enumerate(parts):
        d = e - s; out = os.path.join(gen, f"face{i + 1}_1080.mp4")
        if not os.path.exists(out):
            pre = "tpad=start_mode=clone:start_duration=0.2," if i == 0 else ""
            run("ffmpeg", "-v", "error", "-y", "-ss", f"{off:.3f}", "-t", f"{d:.3f}", "-i", lips, "-an", "-vf",
                f"{pre}scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps=30",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:v", "libx264", "-crf", "16",
                "-pix_fmt", "yuv420p", "-g", "15", "-keyint_min", "15", out)
        faces.append(out); off += d
    # reaction PiP baked into the hook
    for job, dst in react_jobs:
        masonry_wait(job, dst)
    hook_pip = os.path.join(gen, "hook_pip.mp4")
    if not os.path.exists(hook_pip):
        cuts = []
        for r in range(3):
            c = os.path.join(gen, f"react{r}_cut.webm")
            if not os.path.exists(c):
                with local_lock():
                    run("nice", "-n", "19", "npx", "--yes", "hyperframes@0.7.87", "remove-background", os.path.join(gen, f"react{r}.mp4"),
                        "-o", c, "--quality", "best", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cuts.append(c)
        H = dur(hook30)
        seq = [0, 1, 2, "r2", "r1", "r0", 0, 1, 2, "r2"]
        fc = []
        for r in range(3):
            fc.append(f"[{r + 1}:v]crop=iw*0.6:ih*0.55:iw*0.2:0,scale=330:-2:flags=lanczos,fps=30,format=yuva420p,split=2[f{r}][b{r}]")
            fc.append(f"[b{r}]reverse[r{r}]")
        # each stream may be used once per concat; split again as needed
        uses = {}
        for s in seq:
            uses[str(s)] = uses.get(str(s), 0) + 1
        for r in range(3):
            for kind in ("f", "r"):
                n = uses.get(str(r) if kind == "f" else f"r{r}", 0)
                if n:
                    fc.append(f"[{kind}{r}]split={n}" + "".join(f"[{kind}{r}_{u}]" for u in range(n)))
        cnt, labels = {}, []
        for s in seq:
            kind, r = ("r", int(str(s)[1])) if str(s).startswith("r") else ("f", int(s))
            u = cnt.get((kind, r), 0); cnt[(kind, r)] = u + 1
            labels.append(f"[{kind}{r}_{u}]")
        fc.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0,trim=0:{H:.3f},setpts=PTS-STARTPTS[pip]")
        fc.append(f"[0:v][pip]overlay=x=726:y=150:eof_action=pass,format=yuv420p[v]")   # shoulders overlap the video top edge (~y615) like the reference
        with local_lock():
            run("nice", "-n", "19", "ffmpeg", "-v", "error", "-y", "-i", hook30,
                *sum([["-c:v", "libvpx-vp9", "-i", c] for c in cuts], []),
                "-filter_complex", ";".join(fc), "-map", "[v]", "-color_primaries", "bt709", "-color_trc", "bt709",
                "-colorspace", "bt709", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-g", "15", "-keyint_min", "15", hook_pip)
    # build + render
    if not os.path.exists(os.path.join(hf, "build.py")):
        for fnt in ("geist-600.woff2", "geist-700.woff2"):
            src = os.path.join(MGTA, "gta2", "hf", "assets", "fonts", fnt)
            if not os.path.exists(src):
                src = os.path.join(MGTA, "gta1", "hf_sample", "assets", "fonts", fnt)
            shutil.copy(src, os.path.join(hf, "assets", "fonts", fnt))
        shutil.copy(os.path.join(MGTA, "gta1", "hf_sample", "package.json"), hf)
        shutil.copy(os.path.join(HERE, "templates", "hwy_build.py"), os.path.join(hf, "build.py"))
    raw = os.path.join(W, "render_raw.mp4")
    if not os.path.exists(raw):
        env = dict(os.environ, MGTA=MGTA, VO_DIR=vo, WORDS=os.path.join(vo, "caption_words.json"), HOOK_PIP=hook_pip,
                   FACE1=faces[0], FACE2=faces[1], FACE3=faces[2], SEGS=os.path.join(vo, "segs.json"))
        with local_lock():
            b = subprocess.run([sys.executable, "build.py"], cwd=hf, env=env, capture_output=True, text=True)
            if b.returncode:
                raise RuntimeError("build failed: " + b.stderr[-500:])
            r = subprocess.run(["nice", "-n", "19", "npx", "--yes", "hyperframes@0.7.87", "render", "-q", "high", "-f", "30",
                                "-w", "1", "--sdr", "-o", raw], cwd=hf, capture_output=True, text=True)
            open(os.path.join(W, "render.log"), "w").write(r.stdout + r.stderr)
            if r.returncode or '"effectiveHdr":"sdr"' not in (r.stdout + r.stderr):
                raise RuntimeError(f"render failed or not SDR (see {W}/render.log)")
    trim = (idx * 3) % 7; z = 1.0 + (idx % 3) * 0.012
    os.makedirs(DELIV, exist_ok=True)
    tmp = final + ".partial"
    with local_lock():
        run("ffmpeg", "-v", "error", "-y", "-ss", f"{trim / 30:.4f}", "-i", raw, "-t", f"{dur(raw) - (trim + 1) / 30:.4f}", "-vf",
            f"scale=iw*{z:.4f}:-2,crop=1080:1920,{a['grade']},format=yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-colorspace", "bt709", "-c:v", "libx264", "-preset", "medium", "-b:v", "12M", "-maxrate", "16M", "-bufsize", "24M",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-f", "mp4", tmp)
    black, spikes = luma_qa(tmp)
    if spikes:
        raise RuntimeError(f"QA failed: spikes={spikes[:5]}")
    os.rename(tmp, final)
    cleanup_after_delivery(W)
    return key, f"delivered {dur(final):.1f}s"


if __name__ == "__main__":
    hook30 = shared_setup()
    keys = sys.argv[1:] or list(ACCOUNTS)
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(one, k, list(ACCOUNTS).index(k), hook30): k for k in keys}
        for fu in cf.as_completed(futs):
            k = futs[fu]
            try:
                log(k, "HWY " + fu.result()[1])
            except Exception as e:
                log(k, f"HWY ERROR {type(e).__name__}: {str(e)[:300]}")
