#!/usr/bin/env python3
r"""Template B — Gaurav's own iPhone 18 Pro reel grammar (DdNELJ9z6pb = gb-apple-video-2-breakdown.md),
as ONE engine both vid95b and vid96b build on.  Apple keynote editorial: white paper #FDFDFD and
pure black flip on hard cuts (the flip IS the transition), rounded radius-60 cards holding the
footage or the live UI, Instrument Serif Italic display lines over Helvetica Neue Bold captions,
every line decoding in per character through a blur (sans left->right, serif in random order),
gold / ice glow words on the A-roll stacks, and a quiet SFX bed.

Changed from hf94b:
  * cards are 4:5 (owner, 2026-10-06: "can we have 4:5 aspect ratio cards instead of 16:9?"):
    840 x 1050 at (120, 330), radius 60; stock lives in the same 4:5 card, never letterboxed
  * cut frames stand: on a type-only scene the FIRST line is set (not decoded) on the cut frame,
    so a hard cut never lands on 2-4 near-blank frames (vid94b did; the ink gate checks it)
  * A-roll stacks are placed from the MEASURED chin of this take (p98 + 44), never copied
"""
import json
import os
import random
import re

from .core import ab, esc, Doc, finish, early, W, H, BAND_Y

PAPER, BLACK, INK = "#FDFDFD", "#000000", "#0B0B0B"
GOLD, GOLDG, ICE, ICEG = "#FBE77C", "rgba(232,181,58,.95)", "#C4F8FC", "rgba(95,184,208,.95)"
CX0, CW, CY0, CH, CR = 120, 840, 330, 1050, 60        # the 4:5 card
SANS = "font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-weight:700;letter-spacing:-.045em;line-height:1"
SERIF = "font-family:InstrumentSerif;font-style:italic;font-weight:400;letter-spacing:-.035em;line-height:.92"


class B:
    def __init__(self, V, vid, here, ground, take="v1"):
        self.V, self.vid, self.here, self.take = V, vid, here, take
        assert set(ground) == set(V.ORDER), set(V.ORDER) ^ set(ground)
        self.GROUND = ground
        self.doc = Doc()
        self.LINES, self.EXTRA, self.VIDS = [], [], []
        self.AR_TOP = int(V.CHIN_P98 + 44)          # first A-roll stack line, below his chin
        self.PAPER_CSS = "background:%s" % PAPER     # a build may swap the white ground (vid97: Gamma's sky)

    def S(self, n):
        return self.V.SPAN[n][0]

    def E(self, n):
        return self.V.SPAN[n][1]

    def w(self, i):
        return self.V.on(i)

    def clip(self, cid, a, b, body, style="", z=30):
        return self.doc.clip(cid, a, b, body, style, z)

    # ── text: every line is a row of per-character spans that decode in ───
    @staticmethod
    def chars(text):
        return "".join('<span class="c">%s</span>' % ("&nbsp;" if ch == " " else esc(ch)) for ch in text)

    def line(self, eid, at, text, kind, top, size, col=None, x=None, w=None, align="center", extra=""):
        """kind: sans | serif | gold | ice.  `at` None = stands from the clip start."""
        fam = SANS if kind == "sans" else SERIF
        if kind == "gold":
            col = GOLD
            extra += ";text-shadow:0 1px 3px rgba(0,0,0,.55),0 0 14px %s,0 0 34px %s,0 6px 24px rgba(0,0,0,.5)" % (GOLDG, GOLDG)
        elif kind == "ice":
            col = ICE
            extra += ";text-shadow:0 1px 3px rgba(0,0,0,.55),0 0 14px %s,0 0 34px %s,0 6px 24px rgba(0,0,0,.5)" % (ICEG, ICEG)
        col = col or INK
        x = 60 if x is None else x
        w = 900 if w is None else w
        assert x >= 60 and x + w <= 1020, eid
        if at is not None:
            self.LINES.append((eid, at, "sans" if kind == "sans" else "serif"))
        return ab("left:%dpx;top:%dpx;width:%dpx;text-align:%s;white-space:nowrap;font-size:%dpx;color:%s;%s;%s"
                  % (x, top, w, align, size, col, fam, extra), self.chars(text), eid, "ln")

    @staticmethod
    def arshadow():
        return "text-shadow:0 2px 6px rgba(0,0,0,.45),0 4px 22px rgba(0,0,0,.55)"

    def title_serif(self, eid, at, text, size=128, col=INK):
        return self.line(eid, at, text, "serif", int(CY0 - 24 - size * 0.86), size, col, extra="z-index:5")

    def title_sans(self, eid, at, text, size=68, col=INK):
        return self.line(eid, at, text, "sans", int(CY0 - 36 - size * 0.96), size, col, extra="z-index:5")

    def cap_sans(self, eid, at, text, size=64, col=INK, y=None):
        return self.line(eid, at, text, "sans", CY0 + CH + 34 if y is None else y, size, col, x=CX0, w=CW)

    def cap_serif(self, eid, at, text, size=104, col=INK, y=None):
        return self.line(eid, at, text, "serif", CY0 + CH + 22 if y is None else y, size, col, x=CX0, w=CW)

    def ar_stack(self, n, rows):
        """A-roll text stack below the chin. rows = [(eid, at, text, kind, size)], stacked top-down"""
        y, out = self.AR_TOP, []
        for eid, at, text, kind, size in rows:
            ex = self.arshadow() if kind == "sans" else ""
            col = "#fff" if kind in ("sans", "serif") else None
            out.append(self.line(eid, at, text, kind, y, size, col, extra=ex))
            y += int(size * (1.0 if kind == "sans" else 0.98)) + 10
        assert y <= BAND_Y - 6, "%s stack runs to y%d (band %d)" % (n, y, BAND_Y)
        return "".join(out)

    # ── cards ───────────────────────────────────────────────────────────
    def card(self, body, eid=None, bg="#111", x=CX0, y=CY0, w=CW, h=CH, r=CR, extra=""):
        return ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:%dpx;background:%s;overflow:hidden;%s"
                  % (x, y, w, h, r, bg, extra), body, eid)

    def vcard(self, scene, key, x=CX0, y=CY0, w=CW, h=CH, r=CR, ms=0.0, a=None, b=None, z=31, fit="cover"):
        self.VIDS.append((scene, key, x, y, w, h, r, ms, a, b, z, fit))

    def vids_html(self):
        out = []
        for k, (scene, key, x, y, w, h, r, ms, a, b, z, fit) in enumerate(self.VIDS):
            a0, b0 = self.V.SPAN[scene]
            a = early(a0 if a is None else a)
            b = b0 if b is None else b
            out.append('<video id="pv%d" src="assets/plates/%s.mp4" data-start="%.4f" data-duration="%.4f" data-track-index="%d"%s '
                       'muted playsinline style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;object-fit:%s;'
                       'border-radius:%dpx;z-index:%d"></video>'
                       % (k, key, a, b - a, self.doc.tr(), (' data-media-start="%.3f"' % ms) if ms else "", x, y, w, h, fit, r, z))
        return "\n".join(out)

    def extra(self, cid, a, b, body, z=40):
        self.EXTRA.append(self.clip(cid, a, b, body, "left:0;top:0;width:1080px;height:1920px", z))

    # ── timeline ────────────────────────────────────────────────────────
    def decode_js(self, seed):
        rnd = random.Random(seed)
        return "\n".join('dec("#%s",%.3f,"%s",%d);' % (eid, at, kind, rnd.randint(1, 10 ** 6)) for eid, at, kind in self.LINES)

    def build(self, A, scene_js, font_css="", extra_css="", seed=95, untimed=""):
        V = self.V
        parts = []
        for n in V.ORDER:
            a, b = V.SPAN[n]
            g = self.GROUND[n]
            if g != "AR":
                parts.append(self.clip("gr_" + n, a, b, "", "left:0;top:0;width:1080px;height:1920px;%s" % (self.PAPER_CSS if g == "W" else "background:" + BLACK), 10))
            parts.append(self.clip("art_" + n, a, b, A.get(n, ""), "left:0;top:0;width:1080px;height:1920px", 30))
        parts += self.EXTRA
        parts.append(untimed)      # outside every clip: holds its own timed <video>s (vid97)
        parts.append(self.vids_html())
        sfxp = os.path.join(self.here, "sfx_block.html")
        sfx = open(sfxp).read() if os.path.exists(sfxp) else ""
        html = (TEMPLATE.replace("__DUR__", "%.4f" % V.DUR).replace("__FONTCSS__", font_css).replace("__EXTRACSS__", extra_css)
                .replace("__ARTS__", "\n".join(parts)).replace("__HELPERS__", HELPERS).replace("__SFX__", sfx)
                .replace("__T__", json.dumps(V.T_table())).replace("__ORDER__", json.dumps(V.ORDER))
                .replace("__SCENEJS__", scene_js + "\n" + self.decode_js(seed)))
        html, nfix = finish(html, V)
        html = re.sub(r'id="(l\d\d[a-z]\w*)"', r'id="\1" data-layout-allow-overlap', html)
        open(os.path.join(self.here, "index.html"), "w", encoding="utf-8").write(html)
        plan = dict(vid=self.vid, take=self.take, dur=V.DUR, scenes=[[n, V.SPAN[n][0], V.SPAN[n][1], self.GROUND[n]] for n in V.ORDER],
                    template="B", video=V.vid, full_face={n: V.face_box(*V.SPAN[n]) for n in V.ORDER if self.GROUND[n] == "AR"})
        json.dump(plan, open(os.path.join(self.here, "plan.json"), "w"), indent=1)
        return html, nfix


HELPERS = r"""
function rng(seed){ return function(){ seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }; }
function dec(sel, at, kind, seed){
  var ch = Array.prototype.slice.call(document.querySelectorAll(sel + " .c"));
  if (kind === "sans") {
    ch.forEach(function(c, i){ tl.fromTo(c, {opacity:0, filter:"blur(10px)"}, {opacity:1, filter:"blur(0px)", duration:.3, ease:"power2.out"}, at + i * .035); });
  } else {
    var r = rng(seed), order = ch.map(function(c, i){ return [r(), i]; }).sort(function(a, b){ return a[0] - b[0]; });
    order.forEach(function(o, k){ tl.fromTo(ch[o[1]], {opacity:0, filter:"blur(26px)"}, {opacity:1, filter:"blur(0px)", duration:.5, ease:"power2.out"}, at + k * .032); });
  }
}
function typeChars(sel, at, per){ document.querySelectorAll(sel).forEach(function(c, i){ tl.fromTo(c, {opacity:0}, {opacity:1, duration:.01}, at + i * per); }); }
function count(sel, at, a, b, dur, fmt){ var el = document.querySelector(sel);
  tl.fromTo({v:a}, {v:a}, {v:b, duration:dur, ease:"power2.out", immediateRender:false,
    onUpdate:function(){ el.textContent = fmt ? fmt(this.targets()[0].v) : Math.round(this.targets()[0].v); }}, at); }
function lift(sel, at, o){ tl.fromTo(sel, {y:(o&&o.y)||24, opacity:0, filter:"blur(10px)"}, {y:0, opacity:1, filter:"blur(0px)",
  duration:(o&&o.d)||0.45, ease:"power3.out", stagger:(o&&o.st)||0}, at); }
function press(sel, at){ tl.fromTo(sel, {scale:1}, {scale:.92, duration:.12, yoyo:true, repeat:1, ease:"sine.inOut", immediateRender:false}, at); }
function drift(sel, at, dur, o){ tl.fromTo(sel, {x:(o&&o.x0)||0, y:(o&&o.y0)||0, scale:(o&&o.s0)||1},
  {x:(o&&o.x1)||0, y:(o&&o.y1)||0, scale:(o&&o.s1)||1, duration:dur, ease:"sine.inOut", immediateRender:false}, at); }
"""

TEMPLATE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face{font-family:InstrumentSerif;src:url('assets/fonts/instrument-serif-400i.woff2') format('woff2');font-style:italic;font-weight:400;font-display:block}
@font-face{font-family:GeistMono;src:url('assets/fonts/geist-mono-500.woff2') format('woff2');font-weight:500;font-display:block}
__FONTCSS__
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;overflow:hidden}
#root{width:2160px;height:3840px;position:relative;overflow:hidden;background:#000}
#stage{position:absolute;left:0;top:0;width:1080px;height:1920px;transform:scale(2);transform-origin:0 0;background:#000;overflow:hidden}
svg{display:block;overflow:visible}
img{display:block}
i{font-style:normal}
.ab{position:absolute}
.c{display:inline-block}
#aroll{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover;z-index:5}
__EXTRACSS__
</style>
</head>
<body>
<div id="root" data-composition-id="root" data-start="0" data-duration="__DUR__" data-width="2160" data-height="3840" data-track-index="0">
<div id="stage">
  <video id="aroll" src="assets/aroll.mp4" data-start="0" data-duration="__DUR__" data-track-index="1" muted playsinline></video>
  __ARTS__
</div>
</div>
<audio id="voice" src="assets/aroll.mp4" data-start="0" data-duration="__DUR__" data-track-index="9" data-volume="1"></audio>
__SFX__
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script>
var T = __T__, ORDER = __ORDER__;
window.__timelines = window.__timelines || {};
var tl = gsap.timeline({paused:true});
__HELPERS__
__SCENEJS__
tl.duration(__DUR__);
window.__timelines.root = tl;
</script>
</body>
</html>
"""
