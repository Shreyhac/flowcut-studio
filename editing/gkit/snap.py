#!/usr/bin/env python3
r"""Preview stills + the DOM safe-zone gate, from the live composition (no HyperFrames runtime).

  python3 gkit/snap.py hf95a                 # contact sheets: +2f, 55%, last frame of every scene
  python3 gkit/snap.py hf95a 1.5 2.0 ...     # exact times
  python3 gkit/snap.py hf95a --full 12.3     # one frame at 1080x1920
  python3 gkit/snap.py hf95a --gate          # the safe-zone gate (exit 1 on any violation)

THE GATE (handoff item 3; vid94 only estimated label widths in A and had no gate in B):
at every cut +2 frames and mid-scene it seeks the timeline, walks every visible TEXT NODE (its own
Range rects, clipped by every overflow:hidden ancestor, opacity product > 0.15) and fails on
  * text above y150 or below y1600            (IG chrome / bottom UI band)
  * text right of x960 inside y900-1600       (the like/comment rail)
  * text left of x60                           (crop buffer)
  * text over the face: the circle on A's circle beats, the measured crown-chin box on full-frame beats
It also lists text whose rendered size is under 24 px at the 1080 stage (item 1: read-by-eye).
Mark an element data-sz-skip to exempt decorative type (e.g. a phone's status-bar clock).
One browser, sequential seeks: this machine has 8 GB (2026-10-06 OOM restart).
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont

FPS = 30

SEEK = """async (t) => {
  const tl = window.__timelines.root; tl.pause(); tl.seek(t, false);
  document.querySelectorAll("[data-start][data-duration]").forEach(el => {
    if (el.tagName === "AUDIO" || el.id === "root") return;
    const s = parseFloat(el.dataset.start), d = parseFloat(el.dataset.duration);
    el.style.setProperty("display", (t >= s - 0.0005 && t <= s + d + 0.0005) ? "" : "none", "important");
  });
  const vids = [...document.querySelectorAll('video')];
  await Promise.all(vids.map(v => new Promise(res => {
    const s = parseFloat(v.dataset.start || 0), d = parseFloat(v.dataset.duration || 0);
    const ms = parseFloat(v.dataset.mediaStart || 0);
    if (t < s - 0.001 || t > s + d + 0.001 || !v.duration) return res();
    const want = Math.min(Math.max(ms + (t - s), 0), v.duration - 0.02);
    let done = false; const cb = () => { if (!done) { done = true; res(); } };
    if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(cb);
    v.currentTime = want + (Math.abs(v.currentTime - want) < 0.008 ? 0.0001 : 0);
    setTimeout(cb, 1500);
  })));
  return 0;
}"""

TEXTS = """() => {
  const out = [];
  const W = document.createTreeWalker(document.getElementById('stage'), NodeFilter.SHOW_TEXT);
  let n;
  while ((n = W.nextNode())) {
    const txt = n.textContent.replace(/\\s+/g, ' ').trim();
    if (!txt) continue;
    const el = n.parentElement;
    if (el.closest('[data-sz-skip]')) continue;
    let op = 1, e = el, clip = {l:-1e9, t:-1e9, r:1e9, b:1e9}, hidden = false;
    while (e && e.id !== 'stage') {
      const cs = getComputedStyle(e);
      if (cs.display === 'none') { hidden = true; break; }
      op *= parseFloat(cs.opacity);
      if (e !== el && (cs.overflow === 'hidden' || cs.overflowX === 'hidden')) {
        const r = e.getBoundingClientRect();
        clip = {l:Math.max(clip.l, r.left), t:Math.max(clip.t, r.top), r:Math.min(clip.r, r.right), b:Math.min(clip.b, r.bottom)};
      }
      e = e.parentElement;
    }
    if (hidden || op < 0.15) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    let l = 1e9, t = 1e9, r = -1e9, b = -1e9;
    for (const q of rg.getClientRects()) { if (q.width < 1) continue; l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); }
    if (r < l) continue;
    l = Math.max(l, clip.l); t = Math.max(t, clip.t); r = Math.min(r, clip.r); b = Math.min(b, clip.b);
    if (r - l < 2 || b - t < 2) continue;
    const bb = el.getBoundingClientRect();
    const sc = el.offsetWidth ? bb.width / el.offsetWidth : 1;
    const fs = parseFloat(getComputedStyle(el).fontSize) * sc;
    out.push({txt: txt.slice(0, 40), id: el.id || (el.closest('[id]') || {}).id || '', l, t, r, b, fs: Math.round(fs * 10) / 10, op: Math.round(op * 100) / 100});
  }
  return out;
}"""


def plan_of(proj):
    return json.load(open(os.path.join(proj, "plan.json")))


def _serve(proj):
    """serve the project over local http: WebGL refuses file:// images as cross-origin (vid97's globe painted black)"""
    import functools, http.server, threading
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=proj)
    h.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


async def session(proj, fn):
    srv = _serve(proj)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--force-color-profile=srgb", "--autoplay-policy=no-user-gesture-required",
                                          "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        ctx = await b.new_context(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
        pg = await ctx.new_page()
        await pg.goto("http://127.0.0.1:%d/index.html" % srv.server_address[1], wait_until="domcontentloaded", timeout=90000)
        await pg.add_style_tag(content="html,body{width:1080px;height:1920px}#root{width:1080px!important;height:1920px!important}#stage{transform:none!important}")
        await pg.wait_for_function("() => !!(window.__timelines && window.__timelines.root)", timeout=30000)
        await pg.wait_for_function("() => document.fonts.status === 'loaded'", timeout=30000)
        await pg.wait_for_function("() => [...document.querySelectorAll('video')].every(v => v.readyState >= 2)", timeout=120000)
        await pg.wait_for_function("() => [...document.images].every(i => i.complete)", timeout=60000)
        r = await fn(pg)
        await b.close()
    srv.shutdown()
    return r


def scene_at(plan, t):
    for n, a, b, rung in plan["scenes"]:
        if a - 1e-6 <= t < b:
            return n, rung
    return plan["scenes"][-1][0], plan["scenes"][-1][3]


def gate_times(plan):
    ts = []
    for n, a, b, rung in plan["scenes"]:
        f = int(round(a * FPS))
        ts += [round((f + 2) / FPS, 4), round((a + b) / 2, 4), round(b - 0.1, 4)]
    return ts


def violations(plan, t, rects):
    n, rung = scene_at(plan, t)
    bad, small = [], []
    face = plan.get("face")
    ff = plan.get("full_face", {}).get(n)
    for q in rects:
        l, tp, r, b = q["l"], q["t"], q["r"], q["b"]
        if r <= 0 or l >= 1080 or b <= 0 or tp >= 1920:
            continue                       # wholly off the stage (a deck pushed out, vid97a round 4): nothing paints
        why = []
        if tp < 150:
            why.append("top<150")
        if b > 1600:
            why.append("bottom>1600")
        if r > 960 and b > 900 and tp < 1600:
            why.append("rail x>960")
        if l < 60:
            why.append("left<60")
        if rung == "CIRC" and face:
            cx, cy, rr = face["cx"], face["cy"], face["r"]
            nx, ny = min(max(cx, l), r), min(max(cy, tp), b)
            if (nx - cx) ** 2 + (ny - cy) ** 2 < rr ** 2:
                why.append("over face circle")
        if ff and rung in ("FULL", "AR", "SPLIT"):
            if l < ff["right"] and r > ff["left"] and tp < ff["bot"] and b > ff["top"]:
                why.append("over face box")
        if why:
            bad.append((n, t, q["txt"], q["id"], [round(l), round(tp), round(r), round(b)], why))
        if q["fs"] < 24:
            small.append((n, t, q["txt"], q["id"], q["fs"]))
    return bad, small


def run_gate(proj):
    plan = plan_of(proj)
    times = gate_times(plan)

    async def fn(pg):
        res = []
        for t in times:
            await pg.evaluate(SEEK, t)
            res.append((t, await pg.evaluate(TEXTS)))
        return res
    res = asyncio.run(session(proj, fn))
    allbad, allsmall = [], {}
    for t, rects in res:
        bad, small = violations(plan, t, rects)
        allbad += bad
        for s in small:
            allsmall.setdefault((s[2], s[3], s[4]), s)
    print("safe-zone gate · %s · %d times · %d text runs checked" % (os.path.basename(proj), len(times), sum(len(r) for _, r in res)))
    for b in allbad:
        print("  FAIL %-4s t=%6.3f %-28r #%s %s %s" % b)
    if allsmall:
        print("  under 24 px (read-by-eye):")
        for s in sorted(allsmall.values(), key=lambda s: s[4]):
            print("    %-4s t=%6.3f %-30r #%s %.1fpx" % s)
    print("GATE %s" % ("PASS" if not allbad else "FAIL (%d)" % len(allbad)))
    return not allbad


async def shoot(pg, times, outdir):
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for t in times:
        await pg.evaluate(SEEK, t)
        await pg.wait_for_timeout(100)
        path = os.path.join(outdir, "%06.3f.png" % t)
        await pg.screenshot(path=path, clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
        paths.append((t, path))
    return paths


def sheet(plan, paths, out, cols=6, tw=270):
    th = int(tw * 1920 / 1080)
    rows = (len(paths) + cols - 1) // cols
    im = Image.new("RGB", (cols * tw, rows * (th + 26)), "#222")
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
    except Exception:
        f = None
    for i, (t, p) in enumerate(paths):
        x, y = (i % cols) * tw, (i // cols) * (th + 26)
        im.paste(Image.open(p).convert("RGB").resize((tw, th)), (x, y + 26))
        d.text((x + 6, y + 3), "%s %.2f" % (scene_at(plan, t)[0], t), fill="#fff", font=f)
    im.save(out, quality=88)
    return out


if __name__ == "__main__":
    proj = os.path.abspath(sys.argv[1])
    args = sys.argv[2:]
    plan = plan_of(proj)
    if "--gate" in args:
        sys.exit(0 if run_gate(proj) else 1)
    full = "--full" in args
    args = [a for a in args if a != "--full"]
    if args:
        times = [float(a) for a in args]
    else:
        times = []
        for n, a, b, rung in plan["scenes"]:
            f = int(round(a * FPS))
            times += [round((f + 2) / FPS, 3), round(a + (b - a) * 0.55, 3), round(b - 0.04, 3)]
    outdir = os.path.join(proj, "preview")
    paths = asyncio.run(session(proj, lambda pg: shoot(pg, times, outdir)))
    if full:
        for t, p in paths:
            print(p)
    else:
        per = 18
        for k in range(0, len(paths), per):
            print(sheet(plan, paths[k:k + per], os.path.join(outdir, "sheet_%02d.jpg" % (k // per))))
