#!/usr/bin/env python3
r"""gkit.core — what every Gaurav cut shares, per video: the take, the words, the cut table,
the face numbers, the boundary shave and the build gates.  Generalised from vid94/common94.py
(2026-10-06) so the four vid95/vid96 builds (two templates x two videos) import ONE copy and a
fix lands in all of them.

    from gkit.core import Video
    V = Video("vid95", cuts=[("s00", 0, "If you're ..."), ...], said={12: "Muse"})

Every cut sits on the ENVELOPE onset of its first word (words_env.json: a 10 ms RMS trace
decides where whisper is late or early), floored to the frame at or before it, so the picture
changes on or just before the syllable, never after it.
"""
import csv
import json
import math
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
W, H = 1080, 1920
BAND_Y = 1600


def fr(t):
    """frame at-or-before t, as a time"""
    return math.floor(t * FPS + 1e-6) / FPS


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def early(t):
    """a clip start written to 4 decimals can round UP past its own frame (11.26667 ->
    11.2667) and the clip is not live on the cut frame (vid91a v2).  Start 0.3 ms early."""
    return 0.0 if t <= 0 else math.floor((t - 0.0003) * 10000) / 10000.0


class Video:
    def __init__(self, vid, cuts, said=None, nwords=None, min_scene=0.9):
        self.vid = vid
        self.dir = os.path.join(ROOT, vid)
        nf = int(json.load(open(os.path.join(self.dir, "probe.json")))["nb_frames"])
        self.NF = nf
        self.DUR = nf / float(FPS)
        self.WORDS = json.load(open(os.path.join(self.dir, "words_env.json")))
        if nwords is not None:
            assert len(self.WORDS) == nwords, (len(self.WORDS), nwords)
        for i, w in (said or {}).items():
            self.WORDS[i]["w"] = w
        self.ONSET = self._onsets()
        self.CUTS = cuts
        self.ORDER = [n for n, _, _ in cuts]
        starts = [0.0 if k == 0 else self.on(wi) for k, (n, wi, line) in enumerate(cuts)]
        # FLOOR to 1e-4, never round: a cut at frame 1367 is 45.56667 s and round() wrote 45.5667, a hair PAST
        # the frame, so every clip ending on that cut painted on the next scene's first frame (vid95a v1: s12 and
        # s16 cut frames showed the outgoing scene; the s16 one was also a chunk seam).
        fl = lambda t: math.floor(t * 10000 + 1e-7) / 10000.0
        self.SPAN = {n: (fl(starts[k]), fl(starts[k + 1] if k + 1 < len(cuts) else self.DUR))
                     for k, (n, wi, line) in enumerate(cuts)}
        for n, (a, b) in self.SPAN.items():
            assert b - a >= min_scene, "%s is only %.2fs (floor %.1f)" % (n, b - a, min_scene)
            assert abs(a * FPS - round(a * FPS)) < 0.01, "%s does not start on a frame" % n
            assert a <= round(a * FPS) / FPS + 1e-9, "%s starts after its own frame" % n
        self.SCENE_WORDS = {n: self.check_line(n) for n in self.ORDER}
        self._face()

    # ── words ──────────────────────────────────────────────────────────
    def _onsets(self):
        """The envelope is exact after a pause and wrong inside continuous speech.  Take it
        only when it does not eat into the previous word and is not >80 ms after whisper's
        own start; else whisper.  Then force strictly increasing onsets."""
        out = []
        for i, w in enumerate(self.WORDS):
            env, ws = w["on"], w["s"]
            prev_end = self.WORDS[i - 1]["e"] if i else -1.0
            t = env if (env >= prev_end - 0.02 and env <= ws + 0.08) else ws
            if out:
                t = max(t, out[-1] + 0.05)
            out.append(t)
        return out

    def on(self, i):
        return fr(self.ONSET[i])

    def wend(self, i):
        return self.WORDS[i]["e"]

    def check_line(self, n):
        """the scene's words, joined, must equal its beat line: a wrong index is a build error"""
        k = self.ORDER.index(n)
        i0 = self.CUTS[k][1]
        i1 = self.CUTS[k + 1][1] if k + 1 < len(self.CUTS) else len(self.WORDS)
        got = " ".join(w["w"] for w in self.WORDS[i0:i1] if w["w"])   # SAID may blank a spurious token (vid98 "the")
        assert got == self.CUTS[k][2], "%s: words say %r, table says %r" % (n, got, self.CUTS[k][2])
        return list(range(i0, i1))

    def find(self, phrase, after=0):
        """index of the first word of `phrase` (punctuation-insensitive) at or after `after`"""
        norm = lambda s: re.sub(r"[^a-z0-9']", "", s.lower())
        p = [norm(x) for x in phrase.split()]
        ws = [norm(w["w"]) for w in self.WORDS]
        for i in range(after, len(ws) - len(p) + 1):
            if ws[i:i + len(p)] == p:
                return i
        raise KeyError(phrase)

    def T_table(self):
        T = {"w%d" % i: math.floor(self.on(i) * 10000 + 1e-7) / 10000.0 for i in range(len(self.WORDS))}
        for n in self.ORDER:
            T[n] = self.SPAN[n][0]
        T["end"] = self.DUR
        return T

    # ── face (vid75/facebox + crown at 6 fps, 1080x1920 space) ─────────────
    def _face(self):
        fb_p, cr_p = os.path.join(self.dir, "facebox.csv"), os.path.join(self.dir, "crown.csv")
        self.FB = list(csv.DictReader(open(fb_p)))
        self.CR = list(csv.DictReader(open(cr_p)))
        p = lambda v, q: sorted(v)[int(q * (len(v) - 1))]
        crowns = [float(r["crownY"]) * H for r in self.CR if r["crownY"]]
        chins = [float(r["contourBot"]) * H for r in self.FB if r["contourBot"]]
        self.CROWN, self.CHIN = p(crowns, 0.5), p(chins, 0.5)
        self.CROWN_P02, self.CHIN_P98 = p(crowns, 0.02), p(chins, 0.98)
        heads = [(float(r["headR"]) - float(r["headL"])) * W for r in self.CR if r["headL"]]
        self.HEADW = p(heads, 0.5)
        self.FACE_CX = {n: self.face_cx(*self.SPAN[n]) for n in self.ORDER}

    def face_cx(self, a, b):
        v = sorted((float(r["contourLeft"]) + float(r["contourRight"])) / 2 * W
                   for i, r in enumerate(self.FB) if a <= i / 6.0 < b and r["contourLeft"])
        return round(v[len(v) // 2], 1) if v else 540.0

    def face_box(self, a, b, q=0.98):
        """the face's extent inside [a,b): crown p(1-q) to chin p(q), x from contour"""
        rows = [i for i in range(len(self.FB)) if a <= i / 6.0 < b]
        cy = sorted(float(self.CR[i]["crownY"]) * H for i in rows if i < len(self.CR) and self.CR[i]["crownY"])
        ch = sorted(float(self.FB[i]["contourBot"]) * H for i in rows if self.FB[i]["contourBot"])
        xl = sorted(float(self.FB[i]["contourLeft"]) * W for i in rows if self.FB[i]["contourLeft"])
        xr = sorted(float(self.FB[i]["contourRight"]) * W for i in rows if self.FB[i]["contourRight"])
        pk = lambda v, qq: v[int(qq * (len(v) - 1))]
        return dict(top=pk(cy, 1 - q), bot=pk(ch, q), left=pk(xl, 1 - q), right=pk(xr, q))

    def summary(self):
        lines = []
        for n in self.ORDER:
            a, b = self.SPAN[n]
            lines.append("%-4s %6.3f-%6.3f (%4.2fs) f%4d  fcx %5.1f  %s" % (
                n, a, b, b - a, round(a * FPS), self.FACE_CX[n], self.CUTS[self.ORDER.index(n)][2]))
        lines.append("%d scenes, avg %.2fs, min %.2fs, DUR %.4f · crown %.0f chin %.0f (p98 %.0f) head %.0f" % (
            len(self.ORDER), self.DUR / len(self.ORDER), min(b - a for a, b in self.SPAN.values()),
            self.DUR, self.CROWN, self.CHIN, self.CHIN_P98, self.HEADW))
        return "\n".join(lines)


# ══ BUILD HELPERS (one copy for all four builds) ══════════════════════════
class Doc:
    """a per-build element factory: one track counter, the clip/ab/img/svg vocabulary"""

    def __init__(self, track0=500):
        self._t = track0

    def tr(self):
        self._t += 1
        return self._t

    def clip(self, cid, a, b, body, style="", z=30, cls=""):
        a0 = early(a)
        return ('<div class="clip %s" id="%s" data-start="%.4f" data-duration="%.4f" data-track-index="%d" '
                'style="position:absolute;z-index:%d;%s">%s</div>' % (cls, cid, a0, b - a0, self.tr(), z, style, body))


def ab(style, body="", eid=None, cls=""):
    return '<div%s class="ab %s" style="%s">%s</div>' % ((' id="%s"' % eid) if eid else "", cls, style, body)


def img(src, style, eid=None):
    return '<img%s src="%s" alt="" style="position:absolute;%s">' % ((' id="%s"' % eid) if eid else "", src, style)


def svgwrap(w, h, body, eid=None, style=""):
    return ('<svg%s viewBox="0 0 %d %d" width="%d" height="%d" style="position:absolute;left:0;top:0;'
            'overflow:visible;%s">%s</svg>' % ((' id="%s"' % eid) if eid else "", w, h, w, h, style, body))


def close_boundaries(html, bounds):
    """A clip's last frame is inclusive: one ending exactly on a cut paints ON the next
    scene's first frame.  Shave it by less than its distance to the frame before the cut."""
    n = [0]

    def fix(m):
        st, du = float(m.group(1)), float(m.group(2))
        e = st + du
        for b in bounds:
            if abs(e - b) < 0.0005:
                prev = (math.ceil(b * FPS - 1e-6) - 1) / FPS
                du -= min(0.005, (b - prev) / 2.0)
                n[0] += 1
                break
        return 'data-start="%.4f" data-duration="%.4f"' % (st, du)

    return re.sub(r'data-start="([\d.]+)" data-duration="([\d.]+)"', fix, html), n[0]


class ClipGate(HTMLParser):
    """Every element hidden by an inline opacity:0 must live inside a clip."""
    VOID = {"img", "br", "input", "meta", "link", "source", "hr", "path", "circle",
            "rect", "line", "polyline", "polygon", "use", "stop", "text", "ellipse"}

    def __init__(self):
        super().__init__()
        self.stack, self.bad = [], []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        parent_in = self.stack[-1] if self.stack else False
        mine = parent_in or ("clip" in (d.get("class") or "").split())
        if re.search(r"opacity\s*:\s*0(?![.\d])", d.get("style") or "") and not mine:
            self.bad.append(d.get("id") or d.get("class") or tag)
        if tag not in self.VOID:
            self.stack.append(mine)

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.stack:
            self.stack.pop()


def dedupe_imgs(html):
    """identical <img> nodes are discovered as one duplicated media entry; a per-occurrence
    query keeps each distinct"""
    seen = {}

    def fix(m):
        src = m.group(1)
        seen[src] = seen.get(src, 0) + 1
        return 'src="%s%s"' % (src, "" if seen[src] == 1 else "?n=%d" % seen[src])
    return re.sub(r'(?<=<img )[^>]*?src="([^"?]+)"', lambda m: m.group(0).replace('src="%s"' % m.group(1), fix(m)), html)


def gates(html):
    """The build refuses what lint cannot see."""
    stripped = re.sub(r"/\*.*?\*/", " ", html, flags=re.S)
    if re.search(r"visibility\s*:", stripped):
        sys.exit("gate: the composition switches `visibility`; use opacity")
    for m in re.finditer(r"<video[^>]*>", html):
        if re.search(r"transform\s*:", m.group(0)):
            sys.exit("gate: a <video> carries a CSS transform")
    # a timed <video> inside a timed div is the nested-media trap
    g = ClipGate()
    g.feed(html)
    if g.bad:
        sys.exit("gate: hidden by inline opacity:0 outside any clip: %s" % ", ".join(g.bad))
    ids = set(re.findall(r'(?<![-\w])id="([A-Za-z0-9_\-]+)"', html))
    js = html[html.rfind("<script>"):]
    dead = sorted({m for m in re.findall(r'["\']#([A-Za-z][A-Za-z0-9_\-]*)["\' +]', js)
                   if m not in ids and not re.fullmatch(r"[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}", m)})
    if dead:
        sys.exit("gate: timeline names ids that do not exist: %s" % ", ".join(dead))
    dup = [i for i in ids if len(re.findall(r'(?<![-\w])id="%s"' % re.escape(i), html)) > 1]
    if dup:
        sys.exit("gate: duplicate ids: %s" % ", ".join(sorted(dup)))
    # GSAP parses a numeric-looking string end value as a number (demi8: "+9.4%" painted "0%")
    bad_txt = re.findall(r'(?:innerHTML|textContent)\s*:\s*"[-+$]?\d', js)
    if bad_txt:
        sys.exit("gate: a tween writes numeric-looking text: %s" % bad_txt[:3])


def cut_frame_gate(html, V):
    """No clip that started before a cut may still paint ON the cut frame (clip ends are inclusive).
    vid95a v1 shipped two such frames: the cut table had rounded 45.56667 up to 45.5667."""
    cuts = [round(V.SPAN[n][0] * FPS) / FPS for n in V.ORDER if V.SPAN[n][0] > 0]
    bad = []
    for m in re.finditer(r'id="([^"]+)"[^>]*?data-start="([\d.]+)" data-duration="([\d.]+)"', html):
        cid, st, du = m.group(1), float(m.group(2)), float(m.group(3))
        if cid in ("root", "aroll", "voice") or cid.startswith("sfx_"):
            continue
        e = st + du
        for c in cuts:
            if st < c - 1e-4 and c - 1e-6 <= e < c + 0.9 / FPS:
                bad.append((cid, round(st, 4), round(e, 5), round(c, 5)))
    if bad:
        sys.exit("gate: %d clips paint on the next scene's cut frame: %s" % (len(bad), bad[:6]))


def finish(html, V, extra_bounds=()):
    """the shared tail of every build: leftovers, boundary shave, dedupe, gates"""
    left = re.findall(r"__[A-Z0-9]+__", html)
    assert not left, left
    html, nfix = close_boundaries(html, [V.SPAN[n][0] for n in V.ORDER if V.SPAN[n][0] > 0] + list(extra_bounds))
    html = dedupe_imgs(html)
    gates(html)
    cut_frame_gate(html, V)
    return html, nfix


def plan_json(V, vid, take, rung, **kw):
    return dict(vid=vid, take=take, dur=V.DUR, scenes=[[n, V.SPAN[n][0], V.SPAN[n][1], rung[n]] for n in V.ORDER], **kw)


def typed(text, cls="ch"):
    return "".join('<i class="%s">%s</i>' % (cls, " " if c == " " else esc(c)) for c in text)
