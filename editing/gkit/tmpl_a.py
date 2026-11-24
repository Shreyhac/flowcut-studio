#!/usr/bin/env python3
r"""Template A — the 100xEngineers grammar (hf91b -> hf92 -> hf94a -> here), as ONE engine both
vid95a and vid96a build on: cream grid paper, a lime `// tag` pill over a two-line Inter Tight
headline (ink line, orange line), his face in a circle top-right with an orange ring, chrome
windows that flip in, orange / lime / pink sticker labels with hard ink shadows, doodles in the
bottom band, a red word-pill caption, and full-frame A-roll beats with a cream card.

SLOWER than hf94a by the owner's note (2026-10-06, "the first one things are moving too fast"):
  * flips .6 s back.out(1.2) (was .4 s back.out(1.4)); pops .5 s back.out(1.6) (was .34 s, 2.2)
  * stamps land in .32 s from 1.5x with no shake (was .2 s from 2.3x + a 4-step jitter)
  * flashes are opt-in per beat and capped (`MAX_FLASH`); doodles turn/loop at half speed
  * headlines type at 30 ms a character (was 22); caption pills pop in .18 s (was .12)
Per-video files supply the scene art and the timeline; everything else lives here.
"""
import json
import math
import os
import re

from .core import ab, img, svgwrap, esc, typed, Doc, finish, early, W, H, FPS, BAND_Y

INK, ORANGE, LIME, PINK, CREAM, CAPRED = "#151515", "#F05A22", "#89FC2C", "#FBDED7", "#FCF3E5", "#FD4930"
DARK, DTXT, MUTE = "#1E1E1C", "#EDEBE4", "#6E6A62"
CX, CY, R = 812.0, 418.0, 215.0
WY, WH, WW, WX = 690, 700, 880, 72          # the main window band (x72-952 keeps clear of the IG rail)
MAX_FLASH = 4
HEAD_W = 515                                 # headline lines fit this width so they clear the circle (vid98: 455)

JS_HELPERS = r"""
function nc(at){ for (var i = 0; i < ORDER.length; i++) if (Math.abs(at - T[ORDER[i]]) < 0.05) return true; return false; }
function O(at){ return nc(at) ? 1 : 0; }
function pop(sel, at, o){ tl.fromTo(sel, {scale:(o&&o.s0)||0.7, opacity:O(at), rotation:(o&&o.r0)||0},
  {scale:1, opacity:1, rotation:(o&&o.r1)||0, duration:(o&&o.d)||0.5, ease:(o&&o.e)||"back.out(1.6)"}, at); }
function lift(sel, at, o){ tl.fromTo(sel, {y:(o&&o.y)||36, opacity:O(at)}, {y:0, opacity:1,
  duration:(o&&o.d)||0.5, ease:(o&&o.e)||"power3.out", stagger:(o&&o.st)||0}, at); }
function slideX(sel, at, dx, o){ tl.fromTo(sel, {x:dx, opacity:O(at)}, {x:0, opacity:1,
  duration:(o&&o.d)||0.55, ease:(o&&o.e)||"power3.out", stagger:(o&&o.st)||0}, at); }
function stamp(sel, at, r){ tl.fromTo(sel, {scale:1.5, opacity:0, rotation:(r||-3)-6},
  {scale:1, opacity:1, rotation:(r||-3), duration:0.32, ease:"power3.out"}, at); }
function typeIn(sel, at, per){ var ch = document.querySelectorAll(sel+" .ch");
  ch.forEach(function(c,i){ tl.fromTo(c, {opacity:0}, {opacity:1, duration:0.01}, at+i*(per||0.03)); }); }
function typeTC(sel, at, per){ var ch = document.querySelectorAll(sel+" .tc");
  ch.forEach(function(c,i){ tl.fromTo(c, {opacity:0}, {opacity:1, duration:0.01}, at+i*(per||0.04)); }); }
function count(sel, at, a, b, dur, fmt){ var el = document.querySelector(sel);
  tl.fromTo({v:a}, {v:a}, {v:b, duration:dur, ease:"power2.out", immediateRender:false,
    onUpdate:function(){ el.textContent = fmt(this.targets()[0].v); }}, at); }
function draw(sel, at, dur){ document.querySelectorAll(sel).forEach(function(p){
  var L = p.getTotalLength ? p.getTotalLength() : 1000;
  p.style.strokeDasharray = L; p.style.strokeDashoffset = L;
  tl.fromTo(p, {strokeDashoffset:L, opacity:0}, {strokeDashoffset:0, opacity:1, duration:dur||0.45, ease:"power2.inOut"}, at); }); }
function flash(at, to){ tl.fromTo("#flash", {opacity:0}, {opacity:to, duration:0.1, ease:"none"}, at);
  tl.to("#flash", {opacity:0, duration:0.3, ease:"none"}, at+0.1); tl.set("#flash", {opacity:0}, at+0.41); }
function bob(sel, at, dur, amp){ tl.fromTo(sel, {y:0}, {y:-(amp||8), duration:1.0, yoyo:true,
  repeat:Math.max(1, Math.floor(dur/1.0))-1, ease:"sine.inOut", immediateRender:false}, at); }
function drift(sel, at, dur, dy){ tl.fromTo(sel, {y:0}, {y:dy, duration:dur, ease:"sine.inOut", immediateRender:false}, at); }
function spin(sel, at, dur, deg){ tl.fromTo(sel, {rotation:0}, {rotation:deg, duration:dur, ease:"none", immediateRender:false}, at); }
function typeLines(sel, at, per){ var ls = document.querySelectorAll(sel+" > div");
  ls.forEach(function(l,i){ tl.fromTo(l, {opacity:0, x:-10}, {opacity:1, x:0, duration:.2}, at+i*(per||0.12)); }); }
function press(sel, at){ tl.fromTo(sel, {scale:1}, {scale:.9, duration:.12, yoyo:true, repeat:1, ease:"sine.inOut", immediateRender:false}, at); }
"""


class A:
    def __init__(self, V, vid, here, full, sections, noface=(), take="v1", face_fill=0.83, bare=(), nocap=(), split=None):
        """bare: circle scenes allowed without a headline (vid97 s03: the owner cut the super);
        nocap: scenes whose caption pills are dropped (vid97 s15: the CTA card already says it);
        split: {scene: (x, y, w, h, s, tx[, pad])}: his face in the lower part of the frame, the crown `pad` (20) px under
        its top edge; a box touching the frame's sides is a true split (square corners), else a rounded card
        (vid97 round 4-5, Gaurav: "split screen and show" the decks above him)"""
        self.SPLIT = {n: tuple(v) + ((20,) if len(v) == 6 else ()) for n, v in (split or {}).items()}
        self.RING = ORANGE                 # the face circle's ring (vid97 round 5: "remove this red" -> INK)
        self.RING_BY = {}                  # per-scene ring colour (gb9a: white on the black HUD pages)
        self.HEAD_REVEAL = "type"          # "wipe": each headline line wipes in whole (gb9 client: a half-typed line read as a broken line break)
        self.HEAD_WS = 0.0                 # headline word-spacing in em (gb9: at -.045em tracking "#1 ON CHATGPT" read as one word)
        self.HEAD_COLS = (INK, ORANGE)     # headline line colours
        self.V, self.vid, self.here, self.take = V, vid, here, take
        self.BARE, self.NOCAP = set(bare), set(nocap)
        self.doc = Doc()
        self.FULL, self.NOFACE = set(full), set(noface)
        self.RUNG = {n: ("SPLIT" if n in self.SPLIT else "FULL" if n in self.FULL else ("NONE" if n in self.NOFACE else "CIRC")) for n in V.ORDER}
        self.SECTIONS = sections
        self.S_C = round(face_fill * 2 * R / (V.CHIN - V.CROWN), 3)
        self.CAM = {n: self.camera(n) for n in V.ORDER}
        self.CLIPS = {n: ("inset(0px 0px 0px 0px)" if self.RUNG[n] == "FULL" else
                          ("inset(0px 0px 1920px 0px)" if self.RUNG[n] == "NONE" else "circle(%dpx at %dpx %dpx)" % (R, CX, CY)))
                      for n in V.ORDER}
        for n, (x, y, w, h, sc, tx, pad) in self.SPLIT.items():
            self.CLIPS[n] = "inset(%dpx %dpx %dpx %dpx%s)" % (y, W - x - w, H - y - h, x, "" if x == 0 and w == W else " round 26px")
        self.LABELS, self.PLATES, self.nflash = [], [], 0

    # ── geometry ────────────────────────────────────────────────────────
    def camera(self, n):
        if self.RUNG[n] == "SPLIT":
            x, y, w, h, s, tx, pad = self.SPLIT[n]
            fb = self.V.face_box(*self.V.SPAN[n])
            ty = y + pad - fb["top"] * s
            assert tx <= x and tx + W * s >= x + w and ty <= y and ty + H * s >= y + h, n
            assert fb["bot"] * s + ty <= BAND_Y - 20, "%s: chin at y%d" % (n, fb["bot"] * s + ty)
            return dict(tx=round(tx, 2), ty=round(ty, 2), s=s)
        if self.RUNG[n] in ("FULL", "NONE"):
            return dict(tx=0.0, ty=0.0, s=1.0)
        s, V = self.S_C, self.V
        tx = min(max(CX - V.FACE_CX[n] * s, CX + R - W * s), CX - R)
        ty = CY - (V.CROWN + V.CHIN) / 2.0 * s
        assert tx <= CX - R + 0.01 and tx + W * s >= CX + R - 0.01, n
        assert ty <= CY - R and ty + H * s >= CY + R, n
        return dict(tx=round(tx, 2), ty=round(ty, 2), s=s)

    def S(self, n):
        return self.V.SPAN[n][0]

    def E(self, n):
        return self.V.SPAN[n][1]

    def w(self, i):
        return self.V.on(i)

    def clip(self, cid, a, b, body, style="", z=30, cls=""):
        return self.doc.clip(cid, a, b, body, style, z, cls)

    # ── vocabulary ──────────────────────────────────────────────────────
    def win(self, eid, x, y, w, h, title, right="", body="", dark=False, fill=None, glyph=None):
        """the reference's chrome window: three ring dots, a mono file name, a right label"""
        bg = fill or (DARK if dark else "#fff")
        tc = DTXT if dark else INK
        dots = "".join(ab("left:%dpx;top:20px;width:20px;height:20px;border-radius:50%%;border:4px solid %s;background:%s"
                          % (22 + k * 30, tc, (LIME if k == 0 else "transparent"))) for k in range(3))
        ttl = (('<span style="position:relative;display:inline-flex;vertical-align:-6px;margin-right:10px">%s</span>' % glyph) if glyph else "") + title
        bar = ab("left:0;top:0;width:%dpx;height:60px;border-bottom:5px solid %s;z-index:5;background:%s" % (w - 10, INK if not dark else "#3A3A36", bg),
                 dots + ab("left:0;top:14px;width:%dpx;text-align:center;font-family:GeistMono;font-weight:500;font-size:24px;color:%s" % (w - 10, tc), ttl)
                 + ab("right:22px;top:15px;font-family:GeistMono;font-weight:500;font-size:22px;color:%s" % tc, right))
        return ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:%s;border:5px solid %s;border-radius:18px;"
                  "box-shadow:12px 12px 0 %s;overflow:hidden" % (x, y, w, h, bg, INK, INK), bar + body, eid, "win")

    def label(self, eid, x, y, text, fill=ORANGE, col="#fff", size=60, rot=-3, font="IT"):
        fam = "InterTight;font-weight:900" if font == "IT" else "GeistMono;font-weight:700"
        self.LABELS.append((eid, x, y, size))
        return ab("left:%dpx;top:%dpx;background:%s;color:%s;font-family:%s;font-size:%dpx;letter-spacing:-.02em;"
                  "line-height:1;padding:10px 20px 12px;border:5px solid %s;border-radius:10px;box-shadow:8px 8px 0 %s;"
                  "white-space:nowrap;transform:rotate(%sdeg)" % (x, y, fill, col, fam, size, INK, INK, rot), text, eid, "lbl")

    def tag(self, eid, x, y, text, fill=LIME, size=26):
        return ab("left:%dpx;top:%dpx;background:%s;color:%s;font-family:GeistMono;font-weight:700;font-size:%dpx;"
                  "padding:8px 20px 9px;border:4px solid %s;border-radius:30px;box-shadow:6px 6px 0 %s;white-space:nowrap"
                  % (x, y, fill, INK, size, INK, INK), esc(text), eid)

    def sticker_logo(self, eid, src, x, y, d, burst=LIME, pad=0.22, inner_bg="#fff", html=None):
        pts = []
        for k in range(24):
            rr = d * (0.62 if k % 2 == 0 else 0.5)
            a = k * math.pi / 12
            pts.append("%.1f,%.1f" % (d * 0.65 + rr * math.cos(a), d * 0.65 + rr * math.sin(a)))
        inner = html if html is not None else ('<img src="%s" style="width:%dpx;height:%dpx;object-fit:contain">'
                                               % (src, d * 0.7 * (1 - 2 * pad), d * 0.7 * (1 - 2 * pad)))
        return ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx" % (x, y, d * 1.3, d * 1.3),
                  svgwrap(int(d * 1.3), int(d * 1.3), '<polygon points="%s" fill="%s" stroke="%s" stroke-width="5" '
                          'stroke-linejoin="round"/>' % (" ".join(pts), burst, INK))
                  + ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:50%%;background:%s;border:4px solid %s;overflow:hidden;"
                       "display:flex;align-items:center;justify-content:center" % (d * 0.3, d * 0.3, d * 0.7, d * 0.7, inner_bg, INK), inner),
                  eid)

    @staticmethod
    def burst(eid, cx, cy, r, fill, n=12, inner=0.72):
        pts = []
        for k in range(n * 2):
            rr = r if k % 2 == 0 else r * inner
            a = k * math.pi / n - math.pi / 2
            pts.append("%.1f,%.1f" % (cx + rr * math.cos(a), cy + rr * math.sin(a)))
        return '<polygon id="%s" points="%s" fill="%s" stroke="%s" stroke-width="6" stroke-linejoin="round"/>' % (eid, " ".join(pts), fill, INK)

    @staticmethod
    def strike_line(eid, x0, x1, y, col=CAPRED, sw=9):
        return '<path id="%s" d="M%d %d L%d %d" stroke="%s" stroke-width="%d" stroke-linecap="round"/>' % (eid, x0, y, x1, y + 4, col, sw)

    @staticmethod
    def mono(x, y, text, size=26, col=INK, w=None, eid=None, extra=""):
        return ab("left:%dpx;top:%dpx;%sfont-family:GeistMono;font-weight:700;font-size:%dpx;color:%s;line-height:1.3;%s"
                  % (x, y, ("width:%dpx;" % w) if w else "white-space:nowrap;", size, col, extra), text, eid)

    @staticmethod
    def it(x, y, text, size, col=INK, eid=None, extra=""):
        return ab("left:%dpx;top:%dpx;font-family:InterTight;font-weight:900;font-size:%dpx;letter-spacing:-.04em;line-height:1;"
                  "color:%s;white-space:nowrap;%s" % (x, y, size, col, extra), text, eid)

    def card_full(self, eid, top, h, body, x=60, w=890):
        """the cream card a FULL beat carries (below the chin: this take leaves no room above the head)"""
        assert top >= self.V.CHIN_P98 + 20, "%s card at y%d is on his chin (p98 %d)" % (eid, top, self.V.CHIN_P98)
        assert top + h <= BAND_Y - 10 and x + w <= 960, eid
        return ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:%s;border:5px solid %s;border-radius:22px;"
                  "box-shadow:12px 12px 0 %s" % (x, top, w, h, CREAM, INK, INK), body, eid)

    # ── stock plates: an untimed wrapper animates, the <video> never transforms ──
    def vplate(self, scene, key, x, y, w, h, ms=0.0, a=None, b=None, extra="", anim="wipe", z=31, radius=14, border=5):
        self.PLATES.append((scene, key, x, y, w, h, ms, a, b, extra, anim, z, radius, border))

    def plates_html(self):
        out = []
        for k, (scene, key, x, y, w, h, ms, a, b, extra, anim, z, rad, bd) in enumerate(self.PLATES):
            a0, b0 = self.V.SPAN[scene]
            a = a0 if a is None else a
            b = b0 if b is None else b
            out.append('<div id="pw_%d" class="pw" data-layout-allow-overflow style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;z-index:%d">'
                       '<video id="pv_%s_%d" class="plate" src="assets/plates/%s.mp4" data-start="%.4f" data-duration="%.4f" '
                       'data-track-index="%d"%s muted playsinline style="position:absolute;left:0;top:0;width:100%%;'
                       'height:100%%;object-fit:cover;border:%dpx solid %s;border-radius:%dpx;%s"></video></div>'
                       % (k, x, y, w, h, z, scene, k, key, early(a), b - early(a), self.doc.tr(),
                          (' data-media-start="%.3f"' % ms) if ms else "", bd, INK, rad, extra))
        return "\n".join(out)

    def plates_js(self):
        j = []
        for k, (scene, key, x, y, w, h, ms, a, b, extra, anim, z, rad, bd) in enumerate(self.PLATES):
            a0, b0 = self.V.SPAN[scene]
            t = (a0 if a is None else a) + 0.005   # starts ON the cut, partly open: the cut frame stands
            end = b0 if b is None else b
            if anim in ("wipe", "box"):
                # the cut frame shows a centred inset of the footage, which opens to the full plate
                j.append('tl.fromTo("#pw_%d",{clipPath:"inset(20%% 16%% 20%% 16%% round 30px)"},{clipPath:"inset(0%% 0%% 0%% 0%% round 0px)",duration:.6,ease:"power3.inOut"},%.3f);' % (k, t))
            elif anim == "iris":
                j.append('tl.fromTo("#pw_%d",{clipPath:"circle(28%% at 50%% 50%%)"},{clipPath:"circle(75%% at 50%% 50%%)",duration:.65,ease:"power3.inOut"},%.3f);' % (k, t))
            elif anim == "slide":
                j.append('tl.fromTo("#pw_%d",{x:-90,rotation:-3,clipPath:"inset(12%% 12%% 12%% 12%% round 30px)"},{x:0,rotation:0,clipPath:"inset(0%% 0%% 0%% 0%% round 0px)",duration:.65,ease:"power3.out"},%.3f);' % (k, t))
            elif anim == "rise":
                j.append('tl.fromTo("#pw_%d",{y:70,rotation:3,opacity:1},{y:0,rotation:0,opacity:1,duration:.6,ease:"power3.out"},%.3f);' % (k, t))
            # a slow drift so a held plate never sits still
            j.append('tl.fromTo("#pw_%d",{y:0},{y:-12,duration:%.3f,ease:"sine.inOut",immediateRender:false},%.3f);' % (k, max(0.4, end - t - 0.7), t + 0.65))
        return "\n".join(j)

    # ── captions: the reference's red word pill ─────────────────────────────
    def pill_chunks(self, ys=None, max_chars=15, max_words=3):
        V, out = self.V, []
        ys = ys or {}
        for n in V.ORDER:
            if n in self.NOCAP:
                continue
            idx = [i for i in V.SCENE_WORDS[n] if V.WORDS[i]["w"]]     # a word SAID blanked never shows (vid98)
            chunks, cur = [], []
            for i in idx:
                cand = cur + [i]
                txt = " ".join(V.WORDS[j]["w"] for j in cand)
                if cur and (len(txt) > max_chars or len(cur) >= max_words):
                    chunks.append(cur)
                    cur = [i]
                else:
                    cur = cand
            if cur:
                chunks.append(cur)
            a, b = V.SPAN[n]
            y = ys.get(n, 1452 if self.RUNG[n] != "FULL" else 1470)
            for ci, ch in enumerate(chunks):
                st = a if ci == 0 else V.on(ch[0])
                en = b if ci == len(chunks) - 1 else V.on(chunks[ci + 1][0]) - 0.004
                txt = esc(" ".join(V.WORDS[j]["w"] for j in ch).replace(" -", "-"))
                t0 = max(st, V.on(ch[0]))
                out.append(self.clip("cp_%s_%d" % (n, ci), st, en,
                                     '<span class="pill" data-t="%.3f"%s>%s</span>' % (t0, ' data-cut="1"' if t0 - st < 0.05 else "", txt),
                                     "left:0;top:%dpx;width:1080px;text-align:center" % y, 45, "cp"))
        return "\n".join(out)

    def doodles(self):
        sq = "M0 40 " + " ".join("Q %d %d %d 40" % (26 + k * 52, 0 if k % 2 == 0 else 80, 52 + k * 52) for k in range(9))
        dots = "".join('<circle cx="%d" cy="%d" r="4" fill="#CFC3AE"/>' % (x * 26, y * 26) for x in range(9) for y in range(6))
        star = "M40 0 L50 28 L80 30 L56 48 L64 78 L40 60 L16 78 L24 48 L0 30 L30 28 Z"
        return (ab("left:70px;top:1628px;width:84px;height:84px", '<svg viewBox="0 0 80 80" width="84" height="84"><path d="%s" '
                   'fill="none" stroke="%s" stroke-width="5" stroke-linejoin="round"/></svg>' % (star, INK), "dStar")
                + ab("left:300px;top:1690px;width:360px;height:90px;overflow:hidden",
                     '<svg id="dSquig" data-layout-allow-overflow width="480" height="90" style="position:absolute;left:0;top:0"><path d="%s" fill="none" '
                     'stroke="%s" stroke-width="9" stroke-linecap="round"/></svg>' % (sq, ORANGE))
                + ab("left:760px;top:1640px", '<svg width="220" height="140">%s</svg>' % dots)
                + ab("left:930px;top:1660px;width:70px;height:70px", '<svg viewBox="0 0 40 40" width="70" height="70"><path '
                     'd="M20 0 C22 14 26 18 40 20 C26 22 22 26 20 40 C18 26 14 22 0 20 C14 18 18 14 20 0Z" fill="%s" stroke="%s" '
                     'stroke-width="2.5"/></svg>' % (LIME, INK), "dSpark"))

    def doodle_js(self):
        D = self.V.DUR
        return ('tl.fromTo("#dStar",{rotation:0},{rotation:90,duration:%.3f,ease:"none",immediateRender:false},0);\n'
                'tl.fromTo("#dSpark",{scale:1},{scale:1.2,duration:1.2,yoyo:true,repeat:%d,ease:"sine.inOut",immediateRender:false},0);\n'
                'tl.fromTo("#dSquig",{x:0},{x:-52,duration:2.4,repeat:%d,ease:"none",immediateRender:false},0);'
                % (D, int(D / 1.2) - 1, int(D / 2.4) - 1))

    def flip(self, sel, at):
        return ('tl.fromTo("%s",{rotationX:-70,y:40,opacity:O(%.3f),transformPerspective:1400,transformOrigin:"50%% 0%%"},'
                '{rotationX:0,y:0,opacity:1,transformPerspective:1400,transformOrigin:"50%% 0%%",duration:.6,ease:"back.out(1.2)"},%.3f);' % (sel, at, at))

    def rise(self, sel, at, d=.8):
        """the calm card entrance (vid97 owner: the flip read as a "curtain"): a short lift out of a soft blur"""
        return ('tl.fromTo("%s",{y:56,scale:.965,opacity:O(%.3f),filter:"blur(8px)",transformOrigin:"50%% 50%%"},'
                '{y:0,scale:1,opacity:1,filter:"blur(0px)",duration:%.2f,ease:"expo.out"},%.3f);' % (sel, at, d, at))

    def flash(self, at, to=0.14):
        self.nflash += 1
        assert self.nflash <= MAX_FLASH, "more than %d flashes: the owner asked for calmer" % MAX_FLASH
        return 'flash(%.3f,%.2f);' % (at, to)

    @staticmethod
    def hsize(l1, l2):
        return int(min(100, 500.0 / (max(len(l1), len(l2)) * 0.62)))

    # ── assemble ────────────────────────────────────────────────────────
    def build(self, A, OV, scene_js, extra_css="", font_css="", cap_ys=None, untimed=""):
        """untimed: markup that lives outside every scene clip (vid97: deck cards holding their own timed <video>s,
        which may not sit inside a timed div); its visibility is the build's own GSAP business"""
        V = self.V
        arts = []
        for n in V.ORDER:
            a, b = V.SPAN[n]
            if n in A:
                arts.append(self.clip("art_" + n, a, b, A[n], "left:0;top:0;width:1080px;height:1920px", 30))
            if n in OV:
                arts.append(self.clip("ov_" + n, a, b, OV[n], "left:0;top:0;width:1080px;height:1920px", 33))
        arts.append(self.plates_html())
        arts.append(untimed)
        heads, hjs = [], []
        for hid, n0, n1, tg, l1, l2 in self.SECTIONS:
            a, b = V.SPAN[n0][0], V.SPAN[n1][1]
            fs = self.hsize(l1, l2)
            wipe = self.HEAD_REVEAL == "wipe"
            body = (lambda s: esc(s)) if wipe else typed
            ws = ("word-spacing:%.2fem;" % self.HEAD_WS) if self.HEAD_WS else ""
            heads.append(self.clip("hd_" + hid, a, b,
                                   self.tag(hid + "_tag", 72, 238, tg)
                                   + ab("left:72px;top:318px;font-family:InterTight;font-weight:900;font-size:%dpx;letter-spacing:-.045em;%s"
                                        "line-height:.95;color:%s;white-space:pre" % (fs, ws, self.HEAD_COLS[0]), body(l1), hid + "_l1", "hl1")
                                   + ab("left:72px;top:%dpx;font-family:InterTight;font-weight:900;font-size:%dpx;letter-spacing:-.045em;%s"
                                        "line-height:.95;color:%s;white-space:pre" % (318 + int(fs * 0.96), fs, ws, self.HEAD_COLS[1]), body(l2), hid + "_l2"),
                                   "left:0;top:0;width:1080px;height:640px", 18))
            at = a + 0.005
            if a < 0.01:
                continue                   # a headline on frame 0 is the cover: it stands, fully set (vid97)
            hjs.append('pop("#%s_tag",%.3f,{s0:.6,r0:-6});' % (hid, at))
            if wipe:
                for k, sel in enumerate(("_l1", "_l2")):       # whole lines: no frame ever shows half a word
                    hjs.append('tl.fromTo("#%s%s",{opacity:0,y:22},{opacity:1,y:0,duration:.3,ease:"power3.out"},%.3f);' % (hid, sel, at + 0.06 + k * 0.14))
            else:
                hjs.append('typeIn("#%s_l1",%.3f,.03);' % (hid, at + 0.06))
                hjs.append('typeIn("#%s_l2",%.3f,.03);' % (hid, at + 0.06 + 0.03 * len(l1)))
        covered = {n for _, n0, n1, _, _, _ in self.SECTIONS for n in V.ORDER[V.ORDER.index(n0):V.ORDER.index(n1) + 1]}
        missing = [n for n in V.ORDER if self.RUNG[n] == "CIRC" and n not in covered and n not in self.BARE]
        assert not missing, "circle scenes without a headline: %s" % missing
        rings = []
        for n in V.ORDER:
            if self.RUNG[n] != "CIRC":
                continue
            a, b = V.SPAN[n]
            rings.append(self.clip("ring_" + n, a, b, "", "left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:50%%;border:7px solid %s;"
                                   "box-shadow:0 0 0 5px %s" % (CX - R - 4, CY - R - 4, 2 * R + 8, 2 * R + 8, self.RING_BY.get(n, self.RING),
                                   "transparent" if self.RING_BY.get(n, self.RING) in (INK, "#fff", "#FFFFFF") else INK), 21))
        sfxp = os.path.join(self.here, "sfx_block.html")
        sfx = open(sfxp).read() if os.path.exists(sfxp) else ""
        html = (TEMPLATE.replace("__DUR__", "%.4f" % V.DUR).replace("__CLIP0__", self.CLIPS[V.ORDER[0]]).replace("__FONTCSS__", font_css)
                .replace("__EXTRACSS__", extra_css)
                .replace("__DOODLES__", self.doodles()).replace("__HEADS__", "\n".join(heads)).replace("__RINGS__", "\n".join(rings))
                .replace("__ARTS__", "\n".join(arts)).replace("__CAPS__", self.pill_chunks(cap_ys)).replace("__SFX__", sfx)
                .replace("__HELPERS__", JS_HELPERS).replace("__HEADW__", str(HEAD_W)).replace("__CAM__", json.dumps(self.CAM)).replace("__CLIPS__", json.dumps(self.CLIPS))
                .replace("__T__", json.dumps(V.T_table())).replace("__ORDER__", json.dumps(V.ORDER))
                .replace("__SCENEJS__", "\n".join(hjs) + "\n" + scene_js + "\n" + self.plates_js() + "\n" + self.doodle_js()))
        html, nfix = finish(html, V)
        html = re.sub(r'id="(h\d+_l[12])"', r'id="\1" data-layout-allow-overlap', html)
        open(os.path.join(self.here, "index.html"), "w", encoding="utf-8").write(html)
        plan = dict(vid=self.vid, take=self.take, dur=V.DUR, scenes=[[n, V.SPAN[n][0], V.SPAN[n][1], self.RUNG[n]] for n in V.ORDER],
                    template="A", video=V.vid, face=dict(kind="circle", cx=CX, cy=CY, r=R), full_face=self.full_face_boxes())
        json.dump(plan, open(os.path.join(self.here, "plan.json"), "w"), indent=1)
        return html, nfix

    def full_face_boxes(self):
        out = {n: self.V.face_box(*self.V.SPAN[n]) for n in self.V.ORDER if self.RUNG[n] == "FULL"}
        for n in self.SPLIT:
            fb, c = self.V.face_box(*self.V.SPAN[n]), self.CAM[n]
            out[n] = dict(top=fb["top"] * c["s"] + c["ty"], bot=fb["bot"] * c["s"] + c["ty"],
                          left=fb["left"] * c["s"] + c["tx"], right=fb["right"] * c["s"] + c["tx"])
        return out


TEMPLATE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face{font-family:InterTight;src:url('assets/fonts/intertight-900.woff2') format('woff2');font-weight:800 900;font-display:block}
@font-face{font-family:Geist;src:url('assets/fonts/geist-700.woff2') format('woff2');font-weight:700;font-display:block}
@font-face{font-family:Geist;src:url('assets/fonts/geist-600.woff2') format('woff2');font-weight:600;font-display:block}
@font-face{font-family:GeistMono;src:url('assets/fonts/geist-mono-500.woff2') format('woff2');font-weight:500;font-display:block}
@font-face{font-family:GeistMono;src:url('assets/fonts/geist-mono-700.woff2') format('woff2');font-weight:700;font-display:block}
@font-face{font-family:Bricolage;src:url('assets/fonts/bricolage-800.woff2') format('woff2');font-weight:800;font-display:block}
__FONTCSS__
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;overflow:hidden}
#root{width:2160px;height:3840px;position:relative;overflow:hidden;background:#FCF3E5}
#stage{position:absolute;left:0;top:0;width:1080px;height:1920px;transform:scale(2);transform-origin:0 0;background:#FCF3E5;overflow:hidden}
svg{display:block;overflow:visible}
img{display:block}
i{font-style:normal}
.ab{position:absolute}
.ch{display:inline}
#paper{position:absolute;inset:0;z-index:0;background-color:#FCF3E5;
  background-image:linear-gradient(#F2E6D1 2px,transparent 2px),linear-gradient(90deg,#F2E6D1 2px,transparent 2px);
  background-size:54px 54px;background-position:-2px -2px}
#doodles{position:absolute;left:0;top:0;width:1080px;height:1920px;z-index:3}
#faceScene{position:absolute;left:0;top:0;width:1080px;height:1920px;z-index:20;overflow:hidden}
#faceCam{position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:0 0}
#aroll{width:1080px;height:1920px;object-fit:cover;display:block}
.cp .pill{display:inline-block;background:#FD4930;color:#fff;font-family:Bricolage;font-weight:800;font-size:54px;
  letter-spacing:-.02em;line-height:1;padding:8px 20px 12px;border-radius:14px}
#flash{position:absolute;inset:0;z-index:62;background:#fff;opacity:0;pointer-events:none}
__EXTRACSS__
</style>
</head>
<body>
<div id="root" data-composition-id="root" data-start="0" data-duration="__DUR__" data-width="2160" data-height="3840" data-track-index="0">
<div id="stage">
  <div id="paper"></div>
  <div id="doodles">__DOODLES__</div>
  __HEADS__
  <div id="faceScene" style="clip-path:__CLIP0__;-webkit-clip-path:__CLIP0__">
    <div id="faceCam" data-layout-allow-overflow>
      <video id="aroll" src="assets/aroll.mp4" data-start="0" data-duration="__DUR__" data-track-index="1" muted playsinline></video>
    </div>
  </div>
  __RINGS__
  __ARTS__
  __CAPS__
  <div id="flash"></div>
</div>
</div>
<audio id="voice" src="assets/aroll.mp4" data-start="0" data-duration="__DUR__" data-track-index="9" data-volume="1"></audio>
__SFX__
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script>
var CAM = __CAM__, CLIPS = __CLIPS__, T = __T__, ORDER = __ORDER__;
window.__timelines = window.__timelines || {};
var tl = gsap.timeline({paused:true});
__HELPERS__
(function(){ var c = CAM[ORDER[0]];
  gsap.set("#faceCam", {x:c.tx, y:c.ty, scale:c.s});   /* a tl.set at 0 does not paint on a fresh load: frame 0 of a circle s00 showed the ceiling (vid97) */
  tl.set("#faceCam", {x:c.tx, y:c.ty, scale:c.s}, 0);
  tl.set("#faceScene", {clipPath:CLIPS[ORDER[0]], webkitClipPath:CLIPS[ORDER[0]]}, 0); })();
ORDER.slice(1).forEach(function(s){ var c = CAM[s], at = T[s] - 0.001;
  tl.to("#faceCam", {x:c.tx, y:c.ty, scale:c.s, duration:0.001, immediateRender:false}, at);
  tl.to("#faceScene", {clipPath:CLIPS[s], webkitClipPath:CLIPS[s], duration:0.001, immediateRender:false}, at); });
/* headlines must clear the circle: both lines share the largest size that fits 505 px */
document.querySelectorAll(".hl1").forEach(function(a){
  var b = document.getElementById(a.id.replace("_l1", "_l2")), fs = parseFloat(a.style.fontSize);
  while ((a.offsetWidth > __HEADW__ || b.offsetWidth > __HEADW__) && fs > 50) { fs -= 2; a.style.fontSize = b.style.fontSize = fs + "px"; }
  b.style.top = (318 + parseFloat(b.style.fontSize) * 0.96) + "px"; });
__SCENEJS__
/* the word pill pops on its chunk's first word; a pill that starts on a cut stands */
document.querySelectorAll(".cp .pill").forEach(function(p){
  var at = parseFloat(p.dataset.t);
  if (at < 0.04) return;
  tl.fromTo(p, {scale:.75, opacity:(p.dataset.cut ? 1 : 0)}, {scale:1, opacity:1, duration:.18, ease:"back.out(1.6)"}, at); });
tl.duration(__DUR__);
window.__timelines.root = tl;
</script>
</body>
</html>
"""
