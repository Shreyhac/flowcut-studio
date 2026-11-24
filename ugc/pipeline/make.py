#!/usr/bin/env python3
"""v1c recipe (owner-approved Yui v1c, 24 Nov) for Yui v2/v3 + the 5 JP girls. Same hook, same 8 owner recordings unmodified, same
script (each girl her own first line), big top title, per-scene subtitle bands, onset-snapped B-roll cuts, HeyGen faces, one forward
chained reaction take as the PiP. Paid steps live in gen.sh.
usage: python3 make.py <key> vo|slices|pip|build|render|final|all"""
import array, json, math, os, re, shutil, subprocess, sys, unicodedata
sys.path.insert(0, "../fleet")
from ig_common import run, dur, fresh_1080, luma_qa, tts, tighten_ig, whisper_lang, script_units, align_units, seg_starts

HERE = os.path.dirname(os.path.abspath(__file__))
YV = os.path.join(os.path.dirname(HERE), "yui_v")
CVPY = "python3"
MGTA = "$MGTA_ROOT"
IGD = os.path.join(MGTA, "fleet", "ig")
LOOKS = json.load(open(os.path.join(HERE, "looks.json")))
YUI = json.load(open(os.path.join(IGD, "hwy_scripts.json")))["yui"]
JPS = json.load(open(os.path.join(os.path.dirname(HERE), "hwy_jp", "scripts.json")))
V1C_CFG = dict(cap_y=dict(viewcount=1500, google=1530, copylink=1340, paste=1240, result=1400, calculator=1440, masonry=1300, prompt=1440),
               cap_bg=["calculator", "masonry"])
SAY = dict(JPS["_say_common"]); SAY.update({"3100万人": "さんぜんひゃくまんにん", "10万ドル": "じゅうまんドル", "AI": "エーアイ"})


def segments(k):
    seg = [list(s) for s in YUI["segments"]]
    if LOOKS[k].get("first"):
        assert seg[0][0] == "face1"; seg[0][1] = LOOKS[k]["first"]
    return seg


def vo(k, N=3):
    """Girls: N ElevenLabs takes of the v1c script (own first line), best by whisper-medium token check, then small-model alignment
    and the v1c onset snap. Yui: her approved v1c VO as is."""
    W = os.path.join(HERE, k); D = os.path.join(W, "vo_v1c")
    if os.path.exists(os.path.join(D, "beats.json")):
        return
    if k.startswith("yui"):
        shutil.copytree(os.path.join(YV, "vo_v1c"), D); return
    L = LOOKS[k]; units, text = script_units(segments(k), "ja", SAY)
    norm = lambda s: re.sub(r"[\s、。，,.!?！？「」]", "", unicodedata.normalize("NFKC", s)).lower()
    need = ["3100万", "100万回", "1000ドル", "12000ドル", "10万ドル", "youtube", "google", "masonry", "dm", "動画", "1日3回"]
    best = None
    for t in range(1, N + 1):
        d = os.path.join(W, f"take{t}"); os.makedirs(d, exist_ok=True)
        if not os.path.exists(os.path.join(d, "vo_full.mp3")):
            tts(text, L["voice"], os.path.join(d, "vo_full.mp3"), speed=L["speed"])
        tighten_ig(os.path.join(d, "vo_full.mp3"), os.path.join(d, "vo_tight.wav"), keep=0.28)
        w16 = os.path.join(d, "vo_tight16.wav")
        if not os.path.exists(w16):
            run("ffmpeg", "-v", "error", "-y", "-i", os.path.join(d, "vo_tight.wav"), "-ac", "1", "-ar", "16000", w16)
        mt = os.path.join(d, "med", "vo_tight16.txt")
        if not os.path.exists(mt):
            subprocess.run(["nice", "-n", "10", "whisper", w16, "--model", "medium", "--language", "ja", "--output_format", "txt",
                            "--output_dir", os.path.join(d, "med")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        heard = norm(open(mt).read()).replace(",", "")
        heard = heard.replace("メイソンリー", "masonry").replace("ユーチューブ", "youtube").replace("グーグル", "google")
        hit = [n for n in need if n in heard]; story = any(x in heard for x in ("ストーリー", "ストリー", "story"))
        score = len(hit) + story
        print(f"{k} take{t}: {score}/{len(need) + 1} missing={[n for n in need if n not in hit] + ([] if story else ['ストーリー'])} | {heard[:120]}")
        if best is None or score > best[0]:
            best = (score, t)
        if score == len(need) + 1:
            break
    d = os.path.join(W, f"take{best[1]}"); raw = os.path.join(W, "vo"); os.makedirs(raw, exist_ok=True)
    for f in ("vo_full.mp3", "vo_tight.wav", "vo_tight16.wav"):
        shutil.copy(os.path.join(d, f), raw)
    shutil.copytree(os.path.join(d, "med"), os.path.join(raw, "med"), dirs_exist_ok=True)
    ww, heard = whisper_lang(os.path.join(raw, "vo_tight16.wav"), raw, "ja")
    al = align_units(units, ww); B = seg_starts(al)
    low = [u["text"] for u in al if u["matched"] < 0.6 * u["chars"]]
    print(f"{k}: chose take{best[1]} ({best[0]}/{len(need) + 1}); VO {dur(os.path.join(raw, 'vo_tight.wav')):.2f}s; weak units {low}")
    snap(raw, al, B, D)


def snap(raw, U, B, D):
    """v1c onset snap: B-roll -> B-roll cuts move forward to the next RMS speech onset after a >=90 ms gap; face cuts stay put."""
    os.makedirs(D, exist_ok=True); shutil.copy(os.path.join(raw, "vo_tight.wav"), D)
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(raw, "vo_tight.wav"), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    a = array.array("h", pcm); k = 480; F = 0.03
    env = [math.sqrt(sum(x * x for x in a[i:i + k]) / k) for i in range(0, len(a) - k, k)]
    for name in ["google", "calculator", "masonry", "paste", "prompt", "result"]:
        b = B[name]; i = int(round(b / F)); j = i; rn = 0; found = None
        while j < min(len(env), i + int(0.8 / F)):
            rn = rn + 1 if env[j] < 400 else 0
            if rn >= 3:
                found = j; break
            j += 1
        if found is None:
            print(f"  {name}: no gap, keep {b:.2f}"); continue
        j = found
        while j < len(env) - 1 and env[j] < 1500:
            j += 1
        nb = round(j * F - 0.03, 3)
        if nb <= b:
            print(f"  {name}: keep {b:.2f}"); continue
        print(f"  {name}: {b:.2f} -> {nb:.2f}")
        first = next(n for n, u in enumerate(U) if u["beat"] == name)
        U[first]["start"] = nb; U[first - 1]["end"] = min(U[first - 1]["end"], nb - 0.02); B[name] = nb
    order = ["face1", "viewcount", "google", "calculator", "face2", "copylink", "masonry", "paste", "prompt", "result", "face3"]
    assert all(B[order[n]] < B[order[n + 1]] for n in range(len(order) - 1)), B
    json.dump(B, open(os.path.join(D, "beats.json"), "w"), indent=1)
    json.dump(U, open(os.path.join(D, "aligned.json"), "w"), ensure_ascii=False, indent=0)
    for u in U:
        print(f"   {u['beat']:10s} {u['start']:6.2f} {u['end']:6.2f} {u['text']}")


def slices(k):
    W = os.path.join(HERE, k); g = os.path.join(W, "gen"); os.makedirs(g, exist_ok=True); D = os.path.join(W, "vo_v1c")
    V = os.path.join(D, "vo_tight.wav"); L = dur(V); b = json.load(open(os.path.join(D, "beats.json")))
    spans = [(0.0, b["viewcount"] - 0.06), (b["face2"] - 0.06, b["copylink"] - 0.06), (b["face3"] - 0.06, L)]
    for i, (s, e) in enumerate(spans, 1):
        sp = os.path.join(g, f"speech{i}.mp3"); Ls = e - s
        if not os.path.exists(sp):
            run("ffmpeg", "-v", "error", "-y", "-ss", f"{s:.3f}", "-t", f"{Ls:.3f}", "-i", V, "-af",
                f"afade=t=out:st={max(0, Ls - 0.08):.3f}:d=0.08,apad=whole_dur={max(2.05, Ls):.3f}", "-c:a", "libmp3lame", "-b:a", "192k", sp)
        print(f"{k} speech{i}: {s:.2f}-{e:.2f} = {Ls:.2f}s")


def pip(k):
    """= yui_v/make.py pip_chain (v1c): takes joined forward, cut out, eroded matte, crop face x1.45, stretched over the whole hook."""
    W = os.path.join(HERE, k); g = os.path.join(W, "gen"); out = os.path.join(g, "hook_pip.mp4"); hook30 = os.path.join(YV, "hook30.mp4")
    if os.path.exists(out):
        return
    takes = sorted((f for f in os.listdir(W) if re.fullmatch(r"react\d+\.mp4", f)), key=lambda f: int(f[5:-4]))
    assert len(takes) == 4, takes
    j = os.path.join(g, "react_join.mp4")
    if not os.path.exists(j):
        ins = sum([["-i", os.path.join(W, t)] for t in takes], [])
        parts = "".join(f"[{n}:v]{'trim=start_frame=1,' if n else ''}setpts=PTS-STARTPTS,fps=24,scale=360:640[p{n}];" for n in range(len(takes)))
        run("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", parts + "".join(f"[p{n}]" for n in range(len(takes))) +
            f"concat=n={len(takes)}:v=1:a=0[v]", "-map", "[v]", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", j)
    cut = os.path.join(g, "react_cut.webm")
    if not os.path.exists(cut):
        run("nice", "-n", "19", "npx", "--yes", "hyperframes@0.7.87", "remove-background", j, "-o", cut, "--quality", "best",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    f0 = os.path.join(g, "react0.png")
    run("ffmpeg", "-v", "error", "-y", "-i", j, "-frames:v", "1", "-vf", "scale=720:1280", f0)
    x, y, w, h = map(int, subprocess.run([os.path.join(YV, "facebox"), f0], capture_output=True, text=True).stdout.split())
    x, y, w, h = [z / 2 for z in (x, y, w, h)]
    cw = min(360, int(w * 1.45)) // 2 * 2; ch = min(640, int(cw * 314 / 238)) // 2 * 2
    x0 = int(min(max(0, x + w / 2 - cw / 2), 360 - cw)); y0 = int(min(max(0, y - 0.62 * h), 640 - ch))
    Hd = dur(hook30); stretch = Hd / dur(j)
    print(f"{k} chain pip crop {cw}x{ch}+{x0}+{y0}; {dur(j):.2f}s stretched x{stretch:.3f}")
    fix = os.path.join(g, "react_fix.mov")   # alpha repair + hole/drop-out check (peer review 25 Nov); fails the build if frames still fail
    r = subprocess.run([CVPY, os.path.join(HERE, "alphafix.py"), j, cut, fix, f"{x0},{y0},{x0 + cw},{y0 + ch}"], capture_output=True, text=True)
    open(os.path.join(W, "alphafix.log"), "w").write(r.stdout + r.stderr); print(r.stdout.strip())
    if r.returncode:
        raise RuntimeError(f"{k}: alpha check failed, see {W}/alphafix.log")
    fc = (f"[0:v]drawbox=x=0:y=1306:w=1080:h=614:color=black:t=fill[h];"
          f"[1:v]crop={cw}:{ch}:{x0}:{y0},scale=238:314:flags=lanczos,format=yuva444p,split=2[pc][pa];"
          f"[pa]alphaextract,erosion,erosion,erosion,gblur=sigma=0.8[pe];[pc][pe]alphamerge,premultiply=inplace=1,format=yuva420p,"
          f"setpts={stretch:.5f}*(PTS-STARTPTS),fps=30,trim=0:{Hd:.3f}[pip];"
          f"[h][pip]overlay=x=812:y={615 + 93 - 314}:eof_action=pass,format=yuv420p[v]")
    run("nice", "-n", "19", "ffmpeg", "-v", "error", "-y", "-i", hook30, "-i", fix, "-filter_complex", fc, "-map", "[v]",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
        "-g", "15", "-keyint_min", "15", out)


def build(k, render=True):
    W = os.path.join(HERE, k); hf = os.path.join(W, "hf"); A = os.path.join(hf, "assets"); D = os.path.join(W, "vo_v1c"); L = LOOKS[k]
    os.makedirs(os.path.join(A, "fonts"), exist_ok=True)
    shutil.copy(os.path.join(MGTA, "gta1", "hf_sample", "package.json"), hf)
    for f in os.listdir(os.path.join(IGD, "fonts")):
        shutil.copy(os.path.join(IGD, "fonts", f), os.path.join(A, "fonts", f))
    shutil.copy(os.path.join(YV, "build_tpl_v1c.py"), os.path.join(hf, "build.py"))
    for i in (1, 2, 3):
        fresh_1080(os.path.join(W, "gen", f"face{i}.mp4"), os.path.join(A, f"face{i}_src.mp4"))
    cfg = json.load(open(os.path.join(YV, "yui_cfg_orig.json")))
    cfg.update(V1C_CFG); cfg["hook_pip"] = os.path.join(W, "gen", "hook_pip.mp4")
    cfg["music"] = os.path.join(IGD, "music", L["music"]); cfg["music_at"] = L["music_at"]
    json.dump(cfg, open(os.path.join(hf, "cfg.json"), "w"), ensure_ascii=False, indent=1)
    env = dict(os.environ, MGTA=MGTA, VO_WAV=os.path.join(D, "vo_tight.wav"), UNITS=os.path.join(D, "aligned.json"),
               BEATS=os.path.join(D, "beats.json"), CFG=os.path.join(hf, "cfg.json"), HWY_SDR=os.path.join(YV, "sdr"), MOCKS_DIR=YV)
    b = subprocess.run([sys.executable, "build.py"], cwd=hf, env=env, capture_output=True, text=True)
    open(os.path.join(W, "build.log"), "w").write(b.stdout + b.stderr)
    if b.returncode:
        raise RuntimeError("build failed: " + (b.stdout + b.stderr)[-1500:])
    print(k, b.stdout.strip())
    if not render:
        return
    raw = os.path.join(W, "render_raw.mp4")
    r = subprocess.run(["nice", "-n", "19", "npx", "--yes", "hyperframes@0.7.87", "render", "-q", "high", "-f", "30", "-w", "1", "--sdr",
                        "-o", raw], cwd=hf, capture_output=True, text=True)
    open(os.path.join(W, "render.log"), "w").write(r.stdout + r.stderr)
    if r.returncode or '"effectiveHdr":"sdr"' not in (r.stdout + r.stderr):
        raise RuntimeError(f"render failed or not SDR (see {W}/render.log)")


def final(k):
    W = os.path.join(HERE, k); L = LOOKS[k]; raw = os.path.join(W, "render_raw.mp4"); out = os.path.join(W, "final.mp4"); trim = L["trim"]
    run("ffmpeg", "-v", "error", "-y", "-ss", f"{trim / 30:.4f}", "-i", raw, "-t", f"{dur(raw) - (trim + 1) / 30:.4f}", "-vf",
        f"{L['grade']},format=yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-colorspace", "bt709", "-c:v", "libx264", "-preset", "medium", "-b:v", "10M", "-maxrate", "12M", "-bufsize", "18M",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-f", "mp4", out + ".tmp")
    black, spikes = luma_qa(out + ".tmp")
    if spikes:
        raise RuntimeError(f"QA failed: spikes={spikes[:5]}")
    os.replace(out + ".tmp", out)
    print(k, f"final {dur(out):.2f}s")


if __name__ == "__main__":
    k = sys.argv[1]; st = sys.argv[2] if len(sys.argv) > 2 else "all"
    assert k in LOOKS and not k.startswith("_"), k
    if st in ("vo", "all"): vo(k)
    if st in ("slices", "all"): slices(k)
    if st in ("pip", "all"): pip(k)
    if st == "build": build(k, render=False)
    if st in ("render", "all"): build(k)
    if st in ("final", "all"): final(k)
