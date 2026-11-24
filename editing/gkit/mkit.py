#!/usr/bin/env python3
r"""gkit.mkit — the "session motion" kit (2026-11-02, vid99 / vid100 for shreyansharora05).

Owner brief: "a bit of Ideogram and STYLING FROM WHAT WE HAVE FIGURED OUT IN THIS SESSION" — the three X references reverse-engineered
in refs/x-motion/BREAKDOWN.md:
  A  @acct_043   light canvas; the spoken line REVEALS letter by letter (blur + rise, synced to each word's onset); accent words in
                 serif italic + accent colour; one UI card per sentence that tilts in, settles, and builds on the words; a hand-drawn
                 ellipse on the payoff word; things clear before the next sentence (no hard pops of a whole frame)
  B  @acct_200  the Claude app "slash command -> finished thing" beat
  C  @acct_101   a 3D coverflow arc of cards
and from the Ideogram grammar (gbkit/pm.py): words on onsets, one persistent device made of the subject, a loud flat page slam.

Rides on gkit.tmpl_a.A (face modes FULL / SPLIT / NONE, plates, gates, chunked render) — the paper grid, doodles and pill captions
are switched off by css().  NO camera moves (owner law, feedback_creator_shreyansh_motion_rules): only elements move.
"""
import math
import re

from .core import ab, esc

_norm = lambda s: re.sub(r"[^a-z0-9%$]", "", s.lower())


def css(ground, ink, extra_bg=""):
    """the light ground: flat colour + whatever radial washes the build passes (radial only: linear bands in H.264)"""
    return ("#doodles{display:none}#root,#stage{background:%s}"
            "#paper{background-color:%s;background-image:%s;background-size:auto;background-position:0 0}"
            ".rv{position:absolute;color:%s;font-family:Inter;font-weight:600;letter-spacing:-.022em;text-align:center}"
            ".rv .ln{display:block;white-space:nowrap}"
            ".rv .rw{display:inline-block;white-space:nowrap}"
            ".rv .rc{display:inline-block;opacity:0;will-change:transform,filter,opacity}"
            ".rv .on .rc{opacity:1}"
            ".rv .acc{font-family:ISerif;font-style:italic;font-weight:400;letter-spacing:-.01em;font-size:1.16em;line-height:.9}"
            ".tilt{transform-style:preserve-3d}"
            % (ground, ground, extra_bg or "none", ink))


FONT_CSS = ("@font-face{font-family:Inter;src:url('assets/fonts/inter-400.woff2') format('woff2');font-weight:400;font-display:block}"
            "@font-face{font-family:Inter;src:url('assets/fonts/inter-500.woff2') format('woff2');font-weight:500;font-display:block}"
            "@font-face{font-family:Inter;src:url('assets/fonts/inter-600.woff2') format('woff2');font-weight:600;font-display:block}"
            "@font-face{font-family:Inter;src:url('assets/fonts/inter-700.woff2') format('woff2');font-weight:700;font-display:block}"
            "@font-face{font-family:ISerif;src:url('assets/fonts/instrument-serif-400i.woff2') format('woff2');font-weight:400;font-style:italic;font-display:block}")


class M:
    def __init__(self, V, T, acc, ink):
        self.V, self.T, self.acc, self.ink = V, T, acc, ink
        self.A, self.OV, self.J = {}, {}, []

    S = lambda self, n: self.V.SPAN[n][0]
    E = lambda self, n: self.V.SPAN[n][1]

    def at(self, n, word, k=0):
        V = self.V
        i = V.find(word, V.SCENE_WORDS[n][0])
        for _ in range(k):
            i = V.find(word, i + 1)
        assert i in V.SCENE_WORDS[n], (n, word)
        return V.on(i)

    def t0(self, n, t):
        """an entrance never fires before its scene's cut (+4 ms so the cut frame is past the clip's own start)"""
        return max(t, self.S(n) + .004)

    # ── A: the letter-by-letter reveal line ─────────────────────────────────────────
    def reveal(self, n, eid, y, text, size=58, col=None, acc=None, x=0, w=1080, lh=1.16, weight=600, align="center",
               start_all=False, extra="", word_ids=False):
        """text: words, '/' = new line, *word* = accent (serif italic, accent colour).  Each word is matched IN ORDER to the
        scene's spoken words; its letters blur-rise in across the word's own spoken length.  A word that is not in his words
        rides with the previous one (printed).  Frame 0 stands fully set (cover)."""
        V, acc = self.V, acc or self.acc
        idx = list(V.SCENE_WORDS[n])
        ptr, prev_t, k, inacc = 0, self.S(n) + .004, 0, False
        lines, events = [], []
        for line in text.split("/"):
            out = []
            for tok in line.strip().split():
                if tok.startswith("*"):
                    inacc = True
                accent = inacc
                if tok.rstrip(".,?!:;").endswith("*"):
                    inacc = False
                raw = tok.replace("*", "")
                t, dur = prev_t, .22
                if not start_all:
                    nk = _norm(raw)
                    for j in range(ptr, len(idx)):
                        wj = _norm(V.WORDS[idx[j]]["w"])
                        if nk and (wj == nk or (len(nk) > 3 and wj.startswith(nk[:4]))):
                            t = self.t0(n, V.on(idx[j]))
                            nxt = V.on(idx[j + 1]) if j + 1 < len(idx) else self.E(n)
                            dur = min(max(nxt - t, .12), .42)
                            ptr = j + 1
                            break
                    else:
                        if k:
                            print("  reveal %s: '%s' not in his words; rides with the previous word" % (n, raw))
                if k == 0 and t < self.S(n) + .2:
                    t = self.S(n) + .004
                prev_t = t
                sid = "%s_%d" % (eid, k)
                k += 1
                chars = "".join('<i class="rc">%s</i>' % esc(c) for c in raw)
                cover = self.S(n) < .01 and t < .05
                out.append('<span id="%s" class="rw%s%s"%s>%s</span>' % (sid, " acc" if accent else "", " on" if cover else "",
                                                                       (' style="color:%s"' % acc) if accent else "", chars))
                if not cover:
                    events.append((sid, t, dur, len(raw)))
            lines.append('<span class="ln">%s</span>' % " ".join(out))
        html = ab("left:%dpx;top:%dpx;width:%dpx;font-size:%dpx;line-height:%.2f;font-weight:%d;text-align:%s;%s%s"
                  % (x, y, w, size, lh, weight, align, ("color:%s;" % col) if col else "", extra), "".join(lines), eid, "rv")
        for sid, t, dur, nc in events:
            self.J.append('tl.fromTo("#%s .rc",{opacity:0,y:%d,filter:"blur(9px)"},{opacity:1,y:0,filter:"blur(0px)",duration:.3,'
                          'ease:"power2.out",stagger:%.4f,immediateRender:false},%.3f);' % (sid, int(size * .22), dur * .8 / max(nc, 1), t))
        return html

    # ── A: the UI card that tilts in and settles ───────────────────────────────────────
    def settle(self, sel, t, rx=18, ry=-14, y=80, s0=.93, d=.8, blur=10, origin="50% 60%"):
        self.J.append('tl.fromTo("%s",{opacity:O(%.3f),y:%d,scale:%.3f,rotationX:%d,rotationY:%d,filter:"blur(%dpx)",transformPerspective:1800,'
                      'transformOrigin:"%s"},{opacity:1,y:0,scale:1,rotationX:0,rotationY:0,filter:"blur(0px)",duration:%.2f,ease:"expo.out",'
                      'immediateRender:false},%.3f);' % (sel, t, y, s0, rx, ry, blur, origin, d, t))

    def rise(self, sel, t, y=40, d=.5, ease="power3.out", stagger=0):
        self.J.append('tl.fromTo("%s",{opacity:O(%.3f),y:%d},{opacity:1,y:0,duration:%.2f,ease:"%s",stagger:%.3f,immediateRender:false},%.3f);'
                      % (sel, t, y, d, ease, stagger, t))

    def pop(self, sel, t, s0=.4, d=.36, ease="back.out(2.2)", r0=0, r1=0):
        self.J.append('tl.fromTo("%s",{opacity:0,scale:%.2f,rotation:%d},{opacity:1,scale:1,rotation:%d,duration:%.2f,ease:"%s",immediateRender:false},%.3f);'
                      % (sel, s0, r0, r1, d, ease, t))

    def slam(self, sel, t, s0=2.0, r=-4, d=.26):
        self.J.append('tl.fromTo("%s",{opacity:0,scale:%.2f,rotation:%d},{opacity:1,scale:1,rotation:%d,duration:%.2f,ease:"power4.out",immediateRender:false},%.3f);'
                      % (sel, s0, r - 8, r, d, t))

    def float(self, sel, n, dy=-12, after=.8):
        """a held card keeps breathing: a slow lift for the rest of its scene (element-level, never the camera)"""
        a, b = self.S(n) + after, self.E(n) - .2          # ends before clear() starts (lint: overlapping y)
        if b - a > .3:
            self.J.append('tl.fromTo("%s",{y:0},{y:%d,duration:%.3f,ease:"sine.inOut",immediateRender:false},%.3f);' % (sel, dy, b - a, a))

    def press(self, sel, t):
        self.J.append('tl.fromTo("%s",{scale:1},{scale:.9,duration:.09,yoyo:true,repeat:1,ease:"sine.inOut",immediateRender:false},%.3f);' % (sel, t))

    def setop(self, sel, t, v=1):
        self.J.append('tl.fromTo("%s",{opacity:%d},{opacity:%d,duration:.001,immediateRender:false},%.3f);' % (sel, 1 - v, v, t))

    def count(self, sel, t, a, b, d, fmt='return Math.round(v).toString();'):
        self.J.append('count("%s",%.3f,%s,%s,%.3f,function(v){%s});' % (sel, t, a, b, d, fmt))

    def draw(self, sel, t, d=.5):
        self.J.append('draw("%s",%.3f,%.2f);' % (sel, t, d))

    def clear(self, n, ids, d=.16):
        """A's 'clear before the next sentence': the scene's groups lift + blur out in the last ~5 frames.  Only on scenes whose
        next scene is on the same ground (a face cut does its own clearing)."""
        t = self.E(n) - d - .02
        for i in ids:
            self.J.append('tl.to("#%s",{opacity:0,y:-18,filter:"blur(8px)",duration:%.2f,ease:"power2.in"},%.3f);' % (i, d, t))
            self.J.append('tl.set("#%s",{opacity:0},%.3f);' % (i, self.E(n)))   # hard kill on the boundary (lint: non-linear seeks)

    # ── A: hand-drawn ellipse + marker sweep ──────────────────────────────────────────
    @staticmethod
    def ellipse(eid, x, y, w, h, col, sw=6, seed=1.0, extra=""):
        """a hand-drawn loop around a box: one and a bit turns, wobbling radius, open ends (drawn by draw())"""
        cx, cy, rx, ry = w / 2.0 + 14, h / 2.0 + 14, w / 2.0, h / 2.0
        pts = []
        for k in range(0, 49):
            a = math.radians(-160 + k * 8.4)
            wob = 1 + .045 * math.sin(k * .9 * seed) + .02 * math.cos(k * 1.7)
            pts.append((cx + rx * wob * math.cos(a), cy + ry * wob * math.sin(a) + k * .18))
        d = "M%.1f %.1f " % pts[0] + " ".join("L%.1f %.1f" % p for p in pts[1:])
        return ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx;%s" % (x - 14, y - 14, w + 28, h + 28, extra),
                  '<svg width="%d" height="%d" style="overflow:visible"><path id="%s_p" d="%s" fill="none" stroke="%s" stroke-width="%d" '
                  'stroke-linecap="round" stroke-linejoin="round" opacity="0"/></svg>' % (w + 28, h + 28, eid, d, col, sw), eid)

    def marker(self, sel, t, d=.32):
        self.J.append('tl.fromTo("%s",{scaleX:0},{scaleX:1,duration:%.2f,ease:"power2.inOut",immediateRender:false},%.3f);' % (sel, d, t))

    # ── C: coverflow arc ─────────────────────────────────────────────────────────────
    @staticmethod
    def arc_pose(k, centre, step=330, ang=34, depth=300):
        """card k's pose when card `centre` faces the viewer"""
        off = k - centre
        return dict(x=off * step * (1 - .14 * min(abs(off), 2)), z=-depth * min(abs(off), 2.2), ry=-ang * max(-1.6, min(1.6, off)),
                    o=1 if abs(off) < 2.6 else 0)

    # ── v2: footage as material (vid99/vid100 round 2: "too text heavy, no videos") ──────────────
    def vcard(self, n, key, x, y, w, h, a=None, b=None, ms=0.0, enter="settle", r=26, z=31, rot=0.0, d=.62, shadow=True,
              ring="rgba(255,255,255,.14)"):
        """a moving plate as a card: the untimed wrapper #pw_k does the 3D entrance; the timed <video> never transforms.
        enter: settle (3D tilt out of depth) | fly (from below, spinning flat) | iris (circle opens) | drop (from above) |
               left / right (slides in from the side) | cut (stands on its first frame) .  rot = resting rotation (deg)."""
        k = len(self.T.PLATES)
        sh = ("box-shadow:0 0 0 2px %s,0 40px 80px -30px rgba(0,0,0,.75),0 16px 30px -12px rgba(0,0,0,.5);" % ring) if shadow else ""
        self.T.vplate(n, key, x, y, w, h, ms, a, b, extra=sh, anim="none", z=z, radius=r, border=0)
        t = (self.S(n) if a is None else a) + .005
        sel = "#pw_%d" % k
        P = 'transformPerspective:1600,transformOrigin:"50% 60%"'     # passed as a %s argument: single %
        if enter == "settle":
            self.J.append('tl.fromTo("%s",{rotationX:16,rotationY:-12,rotation:%.1f,scale:.86,%s},{rotationX:0,rotationY:0,rotation:%.1f,scale:1,%s,duration:%.2f,ease:"expo.out"},%.3f);'
                          % (sel, rot - 4, P, rot, P, d, t))
        elif enter == "fly":
            self.J.append('tl.fromTo("%s",{x:0,rotation:%.1f,scale:.7,%s},{rotation:%.1f,scale:1,%s,duration:%.2f,ease:"back.out(1.5)"},%.3f);'
                          % (sel, rot + 14, P, rot, P, d, t))
        elif enter == "drop":
            self.J.append('tl.fromTo("%s",{rotationX:-38,scale:1.08,rotation:%.1f,%s},{rotationX:0,scale:1,rotation:%.1f,%s,duration:%.2f,ease:"expo.out"},%.3f);'
                          % (sel, rot, P, rot, P, d, t))
        elif enter in ("left", "right"):
            dx = -1 if enter == "left" else 1
            self.J.append('tl.fromTo("%s",{x:%d,rotationY:%d,rotation:%.1f,%s},{x:0,rotationY:0,rotation:%.1f,%s,duration:%.2f,ease:"expo.out"},%.3f);'
                          % (sel, dx * 420, -dx * 30, rot, P, rot, P, d, t))
        elif enter == "iris":
            self.J.append('tl.fromTo("%s",{clipPath:"circle(18%% at 50%% 50%%)"},{clipPath:"circle(75%% at 50%% 50%%)",duration:%.2f,ease:"power3.inOut"},%.3f);' % (sel, d, t))
        elif rot:
            self.J.append('tl.set("%s",{rotation:%.1f},%.3f);' % (sel, rot, t))
        return sel

    def finish(self):
        return self.A, self.OV, "\n".join(self.J), ""


def svg_icon(path_d, size, col, vb=24, sw=2.2, fill="none"):
    return ('<svg width="%d" height="%d" viewBox="0 0 %d %d"><path d="%s" fill="%s" stroke="%s" stroke-width="%.1f" stroke-linecap="round" '
            'stroke-linejoin="round"/></svg>' % (size, size, vb, vb, path_d, fill, col, sw))


CHECK = "M5 12.5l4.5 4.5L19 7.5"
