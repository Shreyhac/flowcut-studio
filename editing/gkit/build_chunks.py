#!/usr/bin/env python3
r"""Split index.html into frame-exact chunk projects on scene cuts, for the
8 GB machine whose capture path stalls after a few hundred 4K frames.

Each chunk is its own project directory under chunks/cN/ with the assets
symlinked, every timed clip re-based to the chunk's start (or dropped if it
never shows in the window), every <audio> removed (the delivered audio is
muxed once by build_mix.py over the full untouched master), and the GSAP
timeline shifted with `shiftChildren(-start)` so the same tweens play at the
same absolute times.

Chunk windows are integer frame counts; the renderer emits floor(d*fps)+1
frames, so each chunk asks for (N - 0.03)/30 s and gets exactly N frames.
Stamps sha256(index.html)[:16] into each chunk so a stale chunk is refused.

Usage: gkit/build_chunks.py <proj> [max_seconds_per_chunk] | gkit/build_chunks.py <proj> --bounds 0,234,461,...
"""
import hashlib, json, math, os, re, shutil, sys

HERE = os.path.abspath(sys.argv.pop(1))   # gkit: the project dir is argv[1]
FPS = 30

plan = json.load(open(os.path.join(HERE, "plan.json")))
DUR = float(plan["dur"])
cuts = sorted({round(a, 3) for n, a, e, s in plan["scenes"]} | {0.0})
html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
stamp = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
total_f = int(round(DUR * FPS))


def greedy_bounds(maxs):
    """extend a chunk to the last scene cut that keeps it under maxs seconds"""
    bounds_f = [0]
    while bounds_f[-1] < total_f:
        a = bounds_f[-1]
        cands = [int(round(c * FPS)) for c in cuts if int(round(c * FPS)) > a and int(round(c * FPS)) - a <= maxs * FPS]
        if total_f - a <= maxs * FPS:
            bounds_f.append(total_f)
        elif cands:
            bounds_f.append(max(cands))
        else:
            bounds_f.append(a + int(maxs * FPS))
    return bounds_f


if "--bounds" in sys.argv:
    bounds_f = sorted({int(x) for x in sys.argv[sys.argv.index("--bounds") + 1].split(",")} | {0, total_f})
    assert all(0 <= b <= total_f for b in bounds_f), bounds_f
else:
    MAXS = float(sys.argv[1]) if len(sys.argv) > 1 else 12.5
    bounds_f = greedy_bounds(MAXS)
chunks = list(zip(bounds_f, bounds_f[1:]))

VIDEO_LEAD = 0.001   # s  (ported from hfjelena2/build_chunks.py, 2026-09-22)


def floor_misfires(start, dur, nframes):
    """True if the engine would show the PREVIOUS frame of this video somewhere.
    HyperFrames picks a video frame with Math.floor((n/fps - start) * fps), and in
    doubles (123/30)*30 = 122.99999999999999: with an on-grid start, local frames
    123, 245-247 ... repeat the frame before and then skip one (LEARNINGS, the Demi
    round of 2026-09-21/22).  Starting the video 1 ms early, same end, fixes it."""
    for n in range(nframes):
        t = n / FPS
        if start <= t < start + dur:
            x = (t - start) * FPS
            if math.floor(x) != math.floor(x + 1e-6):
                return True
    return False


CLIP = re.compile(r'<(video|audio|div|img)\b([^>]*?)data-start="([\d.]+)"([^>]*?)data-duration="([\d.]+)"([^>]*)>', re.S)


LEADS = []


def rebase(src, a, b, d):
    """Re-base every timed element into [a,b) seconds; drop the ones outside."""
    out, drops = [], []

    def fix(m):
        tag, pre, st, mid, du, post = m.groups()
        s, dd = float(st), float(du)
        e = s + dd
        if 'id="root"' in pre:
            return '<%s%s data-start="0" data-duration="%.3f">' % (tag, re.sub(r'\s*data-(start|duration)="[\d.]+"', "", pre + mid + post).rstrip(), d)
        if tag == "audio":
            drops.append(m.group(0)[:60])
            return "<!-- audio dropped: muxed once at delivery -->" if True else m.group(0)
        if e <= a + 1e-6 or s >= b - 1e-6:
            # outside the window: keep the element but park it after the chunk
            # so its id still resolves for GSAP (tl.set on a missing target warns)
            return '<%s%sdata-start="%.3f"%sdata-duration="%.3f"%s>' % (tag, pre, (b - a) + 5.0, mid, 0.5, post)
        ns = max(s, a) - a
        nd = min(e, b) - max(s, a)
        ms_m = re.search(r'data-media-start="([\d.]+)"', pre + mid + post)
        ms = float(ms_m.group(1)) if ms_m else 0.0
        if s < a:
            ms += a - s
        # a sub-frame sliver (a clip ending a few ms after the chunk starts) is still
        # painted on that one frame in the full composition, but the extractor samples
        # zero frames from a window shorter than 1/FPS and aborts ("captured 0 of 1").
        # Half a frame: one sample at ns, and the next frame is not painted.
        if nd < 1.0 / FPS:
            # snap the media start back to the source frame the browser would show
            # anyway, and open a window just under one frame: ffmpeg then extracts
            # exactly that source frame (a 17 ms window from 7.507 yielded none).
            ms = math.floor(ms * FPS + 1e-6) / FPS
            nd = 0.97 / FPS
        if tag == "video" and floor_misfires(ns, nd, int(round((b - a) * FPS))):
            ns -= VIDEO_LEAD
            nd += VIDEO_LEAD
            LEADS.append(re.search(r'id="([^"]+)"', pre + mid + post).group(1))
        rest = pre + mid + post
        rest = re.sub(r'\s*data-media-start="[\d.]+"', "", rest)
        if tag == "video" and ms > 0:
            rest = rest.rstrip() + ' data-media-start="%.3f"' % ms
        # floor the start to the ms (a start rounded UP misses its own first frame), keep the end
        ns_f = math.floor(ns * 1000 + 1e-9) / 1000.0
        nd_f = math.floor((ns + nd - ns_f) * 1000 + 1e-9) / 1000.0
        return '<%s%s data-start="%.3f" data-duration="%.3f">' % (tag, rest.rstrip(), ns_f, nd_f)

    body = CLIP.sub(fix, src)
    return body, drops


for old in os.listdir(os.path.join(HERE, "chunks")) if os.path.isdir(os.path.join(HERE, "chunks")) else []:
    if re.fullmatch(r"c\d+", old):
        shutil.rmtree(os.path.join(HERE, "chunks", old))
for i, (fa, fb) in enumerate(chunks):
    a, b = fa / FPS, fb / FPS
    n = fb - fa
    d = (n - 0.03) / FPS
    cdir = os.path.join(HERE, "chunks", "c%d" % i)
    if os.path.isdir(cdir):
        shutil.rmtree(cdir)
    os.makedirs(cdir)
    os.symlink(os.path.join(HERE, "assets"), os.path.join(cdir, "assets"))
    shutil.copy(os.path.join(HERE, "package.json"), cdir)
    h, drops = rebase(html, a, b, d)
    # the root
    assert re.search(r'id="root"[^>]*data-duration="%.3f"' % d, h), "root duration not set"
    # the timeline: shift, then hard-set the length so nothing rescales
    # GSAP clamps shiftChildren so no child starts before 0 (measured: a -23.9s
    # shift moved everything by -0.36s).  So the chunk keeps the FULL timeline
    # and drives it from a wrapper that seeks at an offset.
    # seek WITHOUT suppressEvents: the counters write their text from onUpdate, and
    # a suppressed seek renders every tween but fires no callback, so every counter
    # in every chunk read 0 (found on h2 c5/c6: 0/100 and $0 where the full
    # composition shows 91 and $116,997).  The composition has no other callbacks.
    # full precision: '%.3f' wrote frame 1207 (40.23333 s) as 40.233, so the whole chunk ran 0.33 ms late and every
    # cut floored to 1e-4 inside it fired one frame late (hf96c v3: s15, s16 showed the previous scene on the cut frame)
    wrap = ('var __chunkA = %.9f;\n'
            'var __root = gsap.timeline({paused:true});\n'
            '__root.to({}, {duration:%.3f, ease:"none", onUpdate:function(){ tl.time(__chunkA + this.time()); }});\n'
            'tl.time(__chunkA);\n'
            'window.__timelines.root = __root;' % (a, d))
    assert "window.__timelines.root = tl;" in h
    h = h.replace("window.__timelines.root = tl;", wrap)
    open(os.path.join(cdir, "index.html"), "w", encoding="utf-8").write(h)
    open(os.path.join(cdir, ".source-hash"), "w").write(stamp)
    json.dump(dict(i=i, fa=fa, fb=fb, frames=n, start=a, end=b, dur=d), open(os.path.join(cdir, "chunk.json"), "w"))
    print("c%d  frames %5d-%5d (%d)  %.3f-%.3fs  audio dropped %d  video lead on: %s"
          % (i, fa, fb, n, a, b, len(drops), ", ".join(LEADS) or "-"))
    LEADS.clear()
json.dump(dict(stamp=stamp, take=plan["take"], chunks=[dict(i=i, fa=fa, fb=fb) for i, (fa, fb) in enumerate(chunks)]),
          open(os.path.join(HERE, "chunks", "manifest.json"), "w"), indent=1)
print("%d chunks · source %s" % (len(chunks), stamp))
