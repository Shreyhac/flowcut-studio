#!/usr/bin/env python3
r"""vid87 — "The deal just ended" (script #8 of scripts-12-new.md, keyword BOTS).

FAST.  16.867s, twelve cuts, 1.41s average, every cut on a word onset that
was checked against a 10 ms RMS envelope of the take (not whisper alone).
He opens full frame for 1.71s, then his face drops into the brown-framed card
at bottom-left and the field above it carries the picture.

THE ARGUMENT, one device per clause, and every device names a fact:
  s01  Google's REAL mark sends visitors down a road into your site
  s02  those visitors are money (a real checkout, the revenue ticking)
  s03  THE DEAL, huge, and the road between Google and you snaps
  s04  four REAL AI marks, a scan beam reading your page line by line
  s05  a REAL AI answer running, and the zero clicks it sends back
  s06  your traffic chart crashing, and Cloudflare's own crawl-to-visit ratio
  s07  Cloudflare's REAL mark, its AI Crawl Control rebuilt: Allow -> Charge,
       and 402 PAYMENT REQUIRED stamped
  s08  YOUR INFO, YOUR PRICE as the main event, the price being typed
  s09  the crawler (the one cast member) pays at the gate and gets in
  s10  Cloudflare's own number: 402s sent to AI bots every day
  s11  comment BOTS, niches getting stamped TAKEN, one left open

Grammar is vid80's (VAL TOWN skin, hard cuts with the furniture standing,
captions beside the card, word-synced).  No camera move anywhere: his rule.

FACE LADDER — solved on THIS take (shreyanshnew.mp4, 101 frames at 6fps
through vid75/facebox + vid75/crown, 1080x1920 space):
  crown p02 222.9 · chin p98 1130.3 · head width p98 735.7 · face cx 583..605
Every card rung lands the CHIN ON y1488.
"""
import json
import os
import re
import shutil
import sys
from html.parser import HTMLParser

import art
from art import (PAPER, DEEP, INK, TERRA, TERRAD, PEACH, RED, WHITE, MUTED,
                 TERMINAL, FIELD, LAV, TAN, SAGE, LEAF, CAFE)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

W, H = 1080, 1920
DUR = 16.867
BAND_Y = 1600
DROP = 13
EBY = 196
CF_ORANGE = "#F38020"     # Cloudflare's own orange, used ONLY inside its own UI
NOTE = "#BFE3C9"

# ══ FACTS — every on-screen number, sourced in vid87/FACTS.md ════════════
FACTS = json.load(open(os.path.join(HERE, "facts.json")))

# ══ TIMES — word onsets out of transcript.json; scene cuts envelope-checked
T = dict(
    t0=0.000, s00=0.000, n20=0.120, years=0.500, deal0=0.920, simple=1.200,
    s01=1.710, google=1.710, sent=1.920, you1=2.120, visitors1=2.240, and1=2.500,
    s02=2.760, visitors2=2.760, made=3.020, you2=3.320, money1=3.420,
    s03=3.780, that=3.780, deal=3.900, just=4.140, ended=4.460,
    s04=5.030, ai=5.030, reads=5.160, yourp=5.420, page=5.520, and2=5.720,
    s05=5.860, answers=5.860, person=6.260, directly=6.500,
    s06=7.230, so=7.230, nobody=7.320, ever=7.620, lands=7.800, site=8.360, anymore=8.620,
    s07=9.130, cloudflare=9.130, now=9.520, lets=9.680, charge=10.120, theai=10.360,
    ai2=10.540, instead=10.760,
    s08=11.290, your1=11.290, information=11.360, your2=12.040, price=12.140,
    s09=12.620, earliest=12.680, people=12.840, inw=13.120,
    s10=13.660, already=13.660, making=14.000, money2=14.280, off=14.600, this=14.820,
    s11=15.170, comment=15.170, kw=15.380, before=15.640, yourc=15.940, niche=16.160,
    isw=16.340, taken=16.520,
    end=16.867,
)

SCENES = [
    ("s00", 0.000,  1.710, "FULL"),      # his face; the cover lockup under his chin
    ("s01", 1.710,  2.760, "CARD_A"),    # Google sends visitors down the road
    ("s02", 2.760,  3.780, "CARD_A"),    # visitors are money
    ("s03", 3.780,  5.030, "CARD_A"),    # THE DEAL, snapped
    ("s04", 5.030,  5.860, "CARD_A"),    # the AI reads your page
    ("s05", 5.860,  7.230, "CARD_A"),    # and answers, zero clicks
    ("s06", 7.230,  9.130, "CARD_A"),    # your traffic crashes
    ("s07", 9.130, 11.290, "CARD_A"),    # Cloudflare: Allow -> Charge, 402
    ("s08", 11.290, 12.620, "CARD_A"),   # your info, your price
    ("s09", 12.620, 13.660, "CARD_A"),   # the crawler pays at the gate
    ("s10", 13.660, 15.170, "CARD_A"),   # 402s every day
    ("s11", 15.170, 16.867, "CARD_XL"),  # CTA, him bigger
]
for _n, _a, _b, _r in SCENES:
    assert _n in T and abs(T[_n] - _a) < 1e-6, "scene %s has no beat in T" % _n
SPAN = {n: (a, b) for n, a, b, r in SCENES}
RUNG = {n: r for n, a, b, r in SCENES}

# ══ FACE — solved for THIS take ══════════════════════════════════════════
CROWN, CHIN, HEADW = 222.9, 1130.3, 735.7
FACE_CX = dict(s00=591.0, s01=586.0, s02=583.0, s03=588.0, s04=598.0, s05=596.0,
               s06=599.0, s07=605.0, s08=593.0, s09=601.0, s10=605.0, s11=605.0)
SWAY = {"CARD_A": 40.0, "CARD_XL": 40.0, "FULL": 0.0}

CHIN_LINE = 1488.0
SCALE = dict(FULL=1.0, CARD_A=0.62, CARD_XL=0.80)
INSET = dict(FULL=0.0, CARD_A=60.0, CARD_XL=70.0)
CARD_W = dict(CARD_A=480, CARD_XL=620)


def window(rung):
    if rung == "FULL":
        return (0, 0, W, H)
    s = SCALE[rung]
    head_h = (CHIN - CROWN) * s
    h = int(round(INSET[rung] + head_h + 72))
    y = int(round(CHIN_LINE - INSET[rung] - head_h))
    return (96, y, CARD_W[rung], h)


WIN = {r: window(r) for r in SCALE}


def camera(rung, fcx):
    x, y, w, h = WIN[rung]
    s = SCALE[rung]
    if rung == "FULL":
        assert CROWN >= 150 and CHIN <= BAND_Y - 100
        return dict(tx=0.0, ty=0.0, s=1.0, chin=CHIN, crown=CROWN)
    tx = x + w / 2.0 - fcx * s
    ty = y + INSET[rung] - CROWN * s
    assert tx <= x + 0.01 and tx + W * s >= x + w - 0.01, "%s: horizontal gap" % rung
    assert ty <= y + 0.01 and ty + H * s >= y + h - 0.01, "%s: vertical gap" % rung
    assert W * s - w >= SWAY[rung] * s - 0.01, "%s: no slack for sway" % rung
    chin = CHIN * s + ty
    crown = CROWN * s + ty
    assert chin <= BAND_Y - 100, "%s: chin %.0f crowds the band" % (rung, chin)
    assert chin <= y + h - 8 and crown >= y + 8, "%s: head cropped by its card" % rung
    assert HEADW * s <= w - 20, "%s: head %.0f wide in a %d card" % (rung, HEADW * s, w)
    return dict(tx=round(tx, 2), ty=round(ty, 2), s=s, chin=round(chin, 1),
                crown=round(crown, 1))


CAM = {n: camera(RUNG[n], FACE_CX[n]) for n, a, b, r in SCENES}
_chins = sorted({round(CAM[n]["chin"]) for n, a, b, r in SCENES if r != "FULL"})
assert len(_chins) == 1, "chin is not constant across card rungs: %s" % _chins
CARD_TOP = WIN["CARD_A"][1]
ART_FLOOR = CARD_TOP - 14        # nothing drawn in the field may reach the card


def clip_inset(rung):
    x, y, w, h = WIN[rung]
    return "inset(%.1fpx %.1fpx %.1fpx %.1fpx round 12px)" % (y, W - (x + w), H - (y + h), x)


CLIPS = {n: clip_inset(RUNG[n]) for n, a, b, r in SCENES}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def face_frame(scene, tri):
    """shadow BELOW · (the A-roll paints here) · stroke-only frame ABOVE."""
    rung = RUNG[scene]
    if rung == "FULL":
        return ""
    a, b = SPAN[scene]
    x, y, w, h = WIN[rung]
    return (
        '<div class="clip" id="%s_fsh" data-start="%.3f" data-duration="%.3f" '
        'data-track-index="%d" style="position:absolute;left:%dpx;top:%dpx;width:%dpx;'
        'height:%dpx;background:%s;border-radius:12px;z-index:19"></div>\n  '
        '<div class="clip" id="%s_ffr" data-start="%.3f" data-duration="%.3f" '
        'data-track-index="%d" style="position:absolute;left:%dpx;top:%dpx;width:%dpx;'
        'height:%dpx;z-index:22">%s</div>'
        % (scene, a, b - a, tri, x + DROP, y + DROP, w, h, INK,
           scene, a, b - a, tri + 1, x, y, w, h, art.stroke_box(w, h, r=12)))


# ══ MARKS — the real ones, rasterised by vid87/marks ═════════════════════
MARK_DIR = os.path.join(ROOT, "vid87", "marks")
MARKS = json.load(open(os.path.join(MARK_DIR, "marks.json")))
OUT_MARKS = os.path.join(HERE, "assets", "marks")
os.makedirs(OUT_MARKS, exist_ok=True)
_uses = {}


def mark_img(key, x, y, size, gid=None, z=28, extra="", attrs="", w=None, h=None):
    """One <img> per USE, each a byte-identical copy under its own filename:
    the compiler flags the same src twice as a duplicate-media risk."""
    assert key in MARKS, "no mark for %s" % key
    n = _uses.get(key, 0) + 1
    _uses[key] = n
    ext = os.path.splitext(MARKS[key]["file"])[1]
    fn = "%s_%d%s" % (key, n, ext)
    shutil.copyfile(os.path.join(MARK_DIR, MARKS[key]["file"]), os.path.join(OUT_MARKS, fn))
    w = w or size
    h = h or size
    return ('<img src="assets/marks/%s" alt="" width="%d" height="%d" style="position:'
            'absolute;left:%.1fpx;top:%.1fpx;width:%dpx;height:%dpx;z-index:%d;'
            'object-fit:contain;%s"%s%s>'
            % (fn, w, h, x, y, w, h, z, extra,
               (' id="%s"' % gid) if gid else "", (" " + attrs) if attrs else ""))


# ══ B-ROLL PLATES — the real thing, moving ═══════════════════════════════
PLATES = json.load(open(os.path.join(HERE, "plates.json"))) \
    if os.path.exists(os.path.join(HERE, "plates.json")) else {}
PLATE_PLAN = []           # (scene, key, rect) — filled by scene_art()


def plate(scene, key, rect, tri, r=14, z=23, shadow=True, sw=6):
    """A real B-roll plate in its furniture, as THREE SIBLINGS: hard shadow
    BELOW, the <video> (scheduled to its own scene, never nested in a timed
    div, never CSS-transformed), and a stroke-only frame ABOVE."""
    a, b = SPAN[scene]
    src = PLATES[key]
    assert src["dur"] >= (b - a) - 0.001, \
        "plate %s is %.2fs but %s runs %.2fs" % (key, src["dur"], scene, b - a)
    x, y, w, h = rect
    d = b - a
    gid = "pl_" + scene
    sh = ('<div class="clip" id="%s_bg" data-start="%.3f" data-duration="%.3f" '
          'data-track-index="%d" style="position:absolute;left:%.1fpx;top:%.1fpx;'
          'width:%.1fpx;height:%.1fpx;background:%s;border-radius:%dpx;z-index:%d">'
          '</div>' % (gid, a, d, tri, x + (DROP if shadow else 0), y + (DROP if shadow else 0),
                      w, h, INK, r, z))
    vid = ('<video id="%s_v" class="plate" src="%s" data-start="%.3f" '
           'data-duration="%.3f" data-track-index="%d" muted playsinline '
           'style="position:absolute;left:%.1fpx;top:%.1fpx;width:%.1fpx;'
           'height:%.1fpx;object-fit:cover;border-radius:%dpx;z-index:%d"></video>'
           % (gid, src["path"], a, d, tri + 1, x, y, w, h, r, z + 1))
    fr = ('<div class="clip" id="%s" data-start="%.3f" data-duration="%.3f" '
          'data-track-index="%d" style="position:absolute;left:%.1fpx;top:%.1fpx;'
          'width:%.1fpx;height:%.1fpx;z-index:%d">%s</div>'
          % (gid, a, d, tri + 2, x, y, w, h, z + 2, art.stroke_box(w, h, r=r, sw=sw)))
    return sh + "\n  " + vid + "\n  " + fr


# ══ CAPTIONS ═════════════════════════════════════════════════════════════
def load_words():
    d = json.load(open(os.path.join(HERE, "transcript.json")))
    ws = [dict(w=x["w"], s=x["s"], e=x["e"]) for x in d["words"]]
    assert len(ws) == 66
    assert ws[7]["w"] == "Google" and ws[60]["w"] == "BOTS"
    return ws


CAP_GROUPS = [
    ("s00", "For 20 years the deal was simple,"),
    ("s01", "Google sent you visitors"),
    ("s02", "and visitors made you money."),
    ("s03", "That deal just ended."),
    ("s04", "AI reads your page"),
    ("s05", "and answers the person directly."),
    ("s06", "So nobody ever lands"),
    ("s06", "on your site anymore."),
    ("s07", "Cloudflare now lets you"),
    ("s07", "charge the AI instead,"),
    ("s08", "your information,"),
    ("s08", "your price."),
    ("s09", "The earliest people in"),
    ("s10", "are already making"),
    ("s10", "money off this."),
    ("s11", "Comment BOTS"),
    ("s11", "before your niche is taken."),
]
ACC_WORDS = {"20", "simple,", "Google", "visitors", "money.", "ended.", "AI", "page",
             "directly.", "nobody", "site", "Cloudflare", "charge", "information,",
             "price.", "earliest", "money", "BOTS", "niche", "taken."}


def build_captions(words):
    out, i = [], 0
    for gi, (scene, text) in enumerate(CAP_GROUPS):
        run, j = [], i
        while j < len(words) and len(" ".join(w["w"] for w in run)) < len(text):
            run.append(words[j])
            j += 1
        got = " ".join(w["w"] for w in run)
        if got != text:
            sys.exit("caption %d: transcript says %r, group says %r" % (gi, got, text))
        start, end = run[0]["s"], run[-1]["e"]
        nxt = words[j]["s"] if j < len(words) else DUR
        a, b = SPAN[scene]
        start = max(start, a)
        d = max(0.24, min(nxt, end + 0.34) - start)
        # the second group of a scene owns the scene's tail
        if gi + 1 == len(CAP_GROUPS) or CAP_GROUPS[gi + 1][0] != scene:
            d = b - start
        d = min(d, b - start)
        if gi + 1 < len(CAP_GROUPS) and CAP_GROUPS[gi + 1][0] == scene:
            d -= shave(start + d)   # never both groups on one frame, never neither
        assert d > 0.10, "caption %d has no time inside %s" % (gi, scene)
        style = {"CARD_XL": "xl", "FULL": "full"}.get(RUNG[scene], "top")
        # a word that is already spoken when its group appears stands; it does not
        # pop.  Decided HERE, not in JS against data-start: the chunk splitter
        # rebases data-start and the JS comparison silently stopped matching (v1).
        spans = "".join('<i class="w%s" data-t="%.3f">%s</i>'
                        % (" acc" if w["w"] in ACC_WORDS else "",
                           0.0 if w["s"] <= start + 0.001 else w["s"], esc(w["w"]))
                        for w in run)
        out.append(dict(id="cap%d" % gi, style=style, scene=scene,
                        start=round(start, 3), dur=round(d, 3), html=spans))
        i = j
    if i != len(words):
        sys.exit("caption gate: %d words never reached a caption" % (len(words) - i))
    return out


# ══ DRAWN KIT ════════════════════════════════════════════════════════════
def ebrow(scene, text, tri):
    a, b = SPAN[scene]
    return ('<div class="eyebrow clip" id="eb_%s" data-start="%.3f" '
            'data-duration="%.3f" data-track-index="%d" style="top:%dpx">%s</div>'
            % (scene, a, b - a, tri, EBY, esc(text)))


def artwrap(scene, tri, body, z=23, gid=None):
    a, b = SPAN[scene]
    return ('<div class="clip" id="%s" data-start="%.3f" data-duration="%.3f" '
            'data-track-index="%d" style="position:absolute;left:0;top:0;'
            'z-index:%d">%s</div>' % (gid or ("art_" + scene), a, b - a, tri, z, body))


def htmlwrap(scene, tri, body, z=28, gid=None):
    return artwrap(scene, tri, body, z=z, gid=gid or ("x_" + scene))


def chip(x, y, w, h, text, seed, fill=WHITE, tcol=INK, size=28, gid=None, font="GeistMono", ls=2,
         sw=5.0, style=""):
    b = [art.stroke(art.wob([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], seed, 1.1, 11),
                    sw, colour=INK, fill=fill)]
    b.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="%s" '
             'font-weight="700" font-size="%d" letter-spacing="%d" fill="%s">%s</text>'
             % (x + w / 2.0, y + h / 2.0 + size * 0.36, font, size, ls, tcol, esc(text)))
    out = "".join(b)
    return ('<g id="%s"%s>%s</g>' % (gid, (' style="%s"' % style) if style else "", out)) \
        if gid else out


def hand(x, y, text, size=56, colour=RED, rot=0.0, gid=None, anchor="start", style=""):
    t = ('<text x="%.1f" y="%.1f" font-family="Caveat" font-weight="700" font-size="%d" '
         'fill="%s" text-anchor="%s"%s>%s</text>'
         % (x, y, size, colour, anchor,
            (' transform="rotate(%.1f %.1f %.1f)"' % (rot, x, y)) if rot else "", esc(text)))
    return ('<g id="%s"%s>%s</g>' % (gid, (' style="%s"' % style) if style else "", t)) \
        if gid else t


def txt(x, y, text, size, fill=INK, font="Geist", weight=700, ls=0.0, anchor="start", extra=""):
    return ('<text x="%.1f" y="%.1f" font-family="%s" font-weight="%d" font-size="%d" '
            'letter-spacing="%.1f" fill="%s" text-anchor="%s"%s>%s</text>'
            % (x, y, font, weight, size, ls, fill, anchor, (" " + extra) if extra else "", esc(text)))


def mono(x, y, text, size=24, fill=MUTED, ls=5, anchor="start"):
    return txt(x, y, text, size, fill=fill, font="GeistMono", weight=700, ls=ls, anchor=anchor)


def field(x, y, w, h, seed, gid=None, fill=FIELD, colour=TERRA):
    out = art.stroke(art.wob([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], seed, 1.2, 13),
                     5, colour=colour, fill=fill)
    return '<g id="%s">%s</g>' % (gid, out) if gid else out


def browser(x, y, w, h, url, seed, gid=None, fill=WHITE, bar=DEEP, url_size=22):
    """A browser window: hard card, a title bar with three dots, the URL pill."""
    b = [art.card(x, y, w, h, fill=fill, sw=6, drop=DROP, r=14)]
    b.append('<path d="M%.1f %.1f H%.1f" stroke="%s" stroke-width="5"/>' % (x + 3, y + 54, x + w - 3, INK))
    b.append('<path d="M%.1f %.1f H%.1f V%.1f H%.1f Z" fill="%s"/>'
             % (x + 3, y + 3, x + w - 3, y + 51.5, x + 3, bar))
    for k, c in enumerate((RED, "#F2C46B", SAGE)):
        b.append('<circle cx="%.1f" cy="%.1f" r="8" fill="%s" stroke="%s" stroke-width="3"/>'
                 % (x + 26 + k * 26, y + 28, c, INK))
    ux = x + 108
    b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="32" rx="16" fill="%s" stroke="%s" '
             'stroke-width="3"/>' % (ux, y + 12, w - 130, WHITE, INK))
    b.append(txt(ux + 18, y + 12 + 16 + url_size * 0.36, url, url_size, fill=INK, font="GeistMono", weight=500))
    out = "".join(b)
    return '<g id="%s">%s</g>' % (gid, out) if gid else out


def stamp(cx, cy, w, h, text, size, gid, colour=RED, rot=-7.0, fill=WHITE, sub=None):
    """A rubber stamp: double red border, red caps.  Scaled about its own
    centre by svgOrigin, never by a percentage."""
    b = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10" fill="%s" stroke="%s" '
         'stroke-width="9"/>' % (cx - w / 2, cy - h / 2, w, h, fill, colour),
         '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6" fill="none" stroke="%s" '
         'stroke-width="3"/>' % (cx - w / 2 + 12, cy - h / 2 + 12, w - 24, h - 24, colour)]
    ty = cy + size * 0.35 - (size * 0.36 if sub else 0)
    b.append(txt(cx, ty, text, size, fill=colour, anchor="middle", ls=-1))
    if sub:
        b.append(txt(cx, ty + size * 0.72, sub, int(size * 0.42), fill=colour, font="GeistMono",
                     anchor="middle", ls=3))
    return ('<g id="%s" style="opacity:0"><g transform="rotate(%.1f %.1f %.1f)">%s</g></g>'
            % (gid, rot, cx, cy, "".join(b)))


def coin(cx, cy, r, gid, style="opacity:0"):
    return ('<g id="%s" style="%s"><circle cx="%.1f" cy="%.1f" r="%.1f" fill="#F2C46B" stroke="%s" '
            'stroke-width="5"/><circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
            'stroke-width="2.5"/>%s</g>'
            % (gid, style, cx, cy, r, INK, cx, cy, r * 0.72, INK,
               txt(cx, cy + r * 0.36, "$", int(r * 1.0), fill=INK, anchor="middle")))


def typed(text, cls="", lead=0):
    out = []
    for i, c in enumerate(text):
        klass = "ch" + ((" " + cls) if cls else "") + (" lead" if i < lead else "")
        out.append('<i class="%s">%s</i>' % (klass, "&nbsp;" if c == " " else esc(c)))
    return "".join(out)


def bottom_band():
    return art.svg(1080, 320,
                   '<rect x="0" y="0" width="1080" height="320" fill="%s"/>' % PAPER
                   + art.stroke(art.wob([(-40, 34), (1120, 8)], 7999, amp=2.0, close=False),
                                w=3, colour="#E4DED9"))


def polylen(pts):
    return sum(((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
               for i in range(len(pts) - 1))


EPS = 0.005      # NOT a whole frame (vid80: a 33 ms shave left blank frames)
BOUNDARIES = [a for n, a, b, r in SCENES if a > 0]


def shave(b, fps=30):
    """How much to end a clip early at boundary b.  5 ms clears the inclusive-end
    double paint when b sits ON a frame, but a boundary 3 ms after a frame
    (vid87 v1: s11 at 15.170, frame 455 at 15.1667) lost BOTH scenes on that
    frame and rendered a void.  Never shave past half the gap to the frame
    before the boundary."""
    import math
    prev = (math.ceil(b * fps - 1e-9) - 1) / float(fps)
    return min(EPS, (b - prev) * 0.5)


def close_boundaries(html):
    n = [0]

    def fix(m):
        st, du = float(m.group(1)), float(m.group(2))
        hit = [b for b in BOUNDARIES if abs(st + du - b) < 0.0005]
        if hit:
            n[0] += 1
            du -= shave(hit[0])
        return 'data-start="%.3f" data-duration="%.3f"' % (st, du)

    return re.sub(r'data-start="([\d.]+)" data-duration="([\d.]+)"', fix, html), n[0]


class _ClipGate(HTMLParser):
    VOID = {"img", "br", "input", "meta", "link", "source", "hr", "path", "circle",
            "rect", "line", "polyline", "polygon", "use", "stop", "text", "ellipse"}

    def __init__(self):
        super().__init__()
        self.stack, self.bad = [], []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        parent_in = self.stack[-1] if self.stack else False
        mine = parent_in or ("clip" in d.get("class", "").split())
        if re.search(r"opacity\s*:\s*0(?![.\d])", d.get("style", "")) and not mine:
            self.bad.append(d.get("id") or d.get("class") or tag)
        if tag not in self.VOID:
            self.stack.append(mine)

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.stack:
            self.stack.pop()


# ══ THE SCENES ═══════════════════════════════════════════════════════════
def scene_art():
    A, O, X = {}, {}, {}      # svg bodies · svgOrigins · extra HTML (rasters, counters)
    HID = "opacity:0"

    # ── s00 · FULL.  The lockup under his chin; nothing over his face. ───
    b = [art.card(72, 1180, 936, 250, fill=WHITE, sw=6, drop=DROP, r=16)]
    b.append(txt(290, 1312, "20 YEARS", 118, ls=-5))
    b.append(mono(294, 1370, "OF FREE GOOGLE TRAFFIC", 28, ls=6))
    b.append(chip(648, 1140, 340, 58, "AI JUST ENDED IT", 8001, fill=RED, tcol=WHITE,
                  size=24, gid="warnpill"))
    O["warnpill"] = "818 1169"
    A["S00"] = art.svg(1080, 1500, "".join(b))
    X["S00"] = mark_img("google", 110, 1218, 174, gid="coverG", z=26)

    # ── s01 · Google sends you visitors ──────────────────────────────────
    GX, GY, GS = 96, 330, 200
    BX, BY, BW, BH = 540, 290, 444, 350
    b = [art.card(GX, GY, GS, GS, fill=WHITE, sw=6, drop=DROP, r=30)]
    b.append(mono(GX + GS / 2, GY + GS + 50, "SENDS", 24, anchor="middle"))
    b.append(browser(BX, BY, BW, BH, "yoursite.com", 8101))
    road = (GX + GS + 24, GY + GS / 2, BX - 24, BY + 190)
    b.append('<path d="M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f" fill="none" stroke="%s" '
             'stroke-width="6" stroke-dasharray="4 16" stroke-linecap="round"/>'
             % (road[0], road[1], road[0] + 90, road[1] - 60, road[2] - 90, road[3] + 50,
                road[2], road[3], INK))
    for k in range(5):
        b.append('<g id="vc%d" style="%s">%s</g>' % (k, HID, art.cursor(0, 0, 1.25)))
    # visitors-this-month ledger under both
    b.append(art.card(96, 680, 888, 150, fill=WHITE, sw=6, drop=DROP, r=16))
    b.append(mono(130, 730, "VISITORS THIS MONTH", 24))
    bars = []
    for k in range(12):
        hgt = 26 + k * 6.2 + (9 if k % 3 == 1 else 0)
        bx = 610 + k * 30
        bars.append('<rect id="vb%d" x="%.1f" y="%.1f" width="20" height="%.1f" rx="4" fill="%s" '
                    'stroke="%s" stroke-width="3"/>' % (k, bx, 806 - hgt, hgt, TERRA if k > 8 else DEEP, INK))
        O["vb%d" % k] = "%.1f 806" % (bx + 10)
    b.append("".join(bars))
    A["S01"] = art.svg(1080, 950, "".join(b))
    O["road"] = road
    X["S01"] = (mark_img("google", GX + 35, GY + 35, 130, gid="s01G", z=28)
                + '<div class="num" id="visN" style="left:128px;top:742px;font-size:74px">48,120</div>')
    PLATE_PLAN.append(("s01", "browse", (BX + 12, BY + 66, BW - 24, BH - 78), dict(shadow=False, r=8, sw=4)))

    # ── s02 · visitors made you money ────────────────────────────────────
    PR = (72, 290, 600, 338)
    PLATE_PLAN.append(("s02", "checkout", PR, {}))
    b = [art.card(72, 668, 600, 160, fill=WHITE, sw=6, drop=DROP, r=16)]
    b.append(mono(104, 716, "REVENUE THIS MONTH", 24))
    b.append(chip(514, 694, 130, 50, "+12%", 8202, fill=SAGE, size=24, gid="upchip"))
    O["upchip"] = "579 719"
    # the note stack grows on "made you money"
    b.append('<g id="stackbase">%s</g>' % art.stack(740, 820, 220, 3, 8210, fill=NOTE, step=26))
    for k in range(6):
        y = 820 - (k + 4) * 26
        jit = ((8220 + k * 37) % 11 - 5) * 0.8
        b.append('<g id="sn%d" style="%s">%s</g>' % (k, HID, art.stroke(
            art.wob([(740 + jit, y), (960 + jit, y), (960 + jit, y + 24.4), (740 + jit, y + 24.4)],
                    8220 + k, 0.9, 9), 3.2, colour=INK, fill=NOTE)))
    b.append(art.note(850, 520, 190, 8240, rot=-12, fill=NOTE, gid="bignote"))
    O["bignote"] = "850 520"
    b.append(hand(850, 360, "every month", size=58, rot=-6, gid="monthhand", anchor="middle", style=HID))
    O["monthhand"] = "850 340"
    A["S02"] = art.svg(1080, 950, "".join(b))
    X["S02"] = '<div class="num" id="revN" style="left:102px;top:728px;font-size:78px">$8,940</div>'

    # ── s03 · THE DEAL, and the road snaps on "ended" ────────────────────
    b = [mono(100, 318, "THE 20-YEAR", 34, fill=MUTED, ls=8)]
    b.append('<g id="dealword">%s</g>' % txt(84, 560, "DEAL", 214, ls=-10))
    O["dealword"] = "340 480"
    b.append('<g id="dealstrike" style="%s">%s</g>' % (HID, art.strike(70, 620, 486, 8310, w=15.0)))
    O["dealstrike"] = "70 486"
    b.append(hand(842, 508, "ENDED.", size=120, rot=-10, gid="endedhand", anchor="middle", style=HID))
    O["endedhand"] = "842 478"
    # the mini deal, left to right: Google, the road, your site
    b.append(art.card(96, 640, 150, 150, fill=WHITE, sw=6, drop=DROP, r=24))
    b.append(browser(716, 626, 268, 178, "yoursite.com", 8320, url_size=15))
    b.append('<g id="roadL"><path d="M270 715 L480 715" stroke="%s" stroke-width="7" '
             'stroke-dasharray="4 16" stroke-linecap="round"/></g>' % INK)
    b.append('<g id="roadR"><path d="M480 715 L690 715" stroke="%s" stroke-width="7" '
             'stroke-dasharray="4 16" stroke-linecap="round"/></g>' % INK)
    O["roadL"] = "270 715"
    O["roadR"] = "690 715"
    b.append('<g id="crack" style="%s">%s</g>' % (HID, art.stroke(
        "M470 660 L492 690 L468 712 L494 738 L474 770", 8, colour=RED)))
    O["crack"] = "480 715"
    A["S03"] = art.svg(1080, 950, "".join(b))
    X["S03"] = mark_img("google", 126, 670, 90, gid="s03G", z=28)

    # ── s04 · AI reads your page ─────────────────────────────────────────
    b = [browser(96, 280, 440, 560, "yoursite.com/guide", 8401, url_size=18)]
    b.append('<rect x="126" y="360" width="300" height="30" rx="6" fill="%s"/>' % INK)
    lines = []
    for k in range(9):
        ly = 420 + k * 44
        lw = (360, 380, 330, 370, 250, 380, 350, 300, 200)[k]
        lines.append('<rect id="pl%d" x="126" y="%d" width="%d" height="16" rx="6" fill="%s"/>'
                     % (k, ly, lw, "#CFC8C2"))
    b.append("".join(lines))
    b.append('<rect id="beam" x="106" y="400" width="420" height="44" rx="6" fill="%s" '
             'opacity=".38" style="%s"/>' % (TERRA, HID))
    tiles = [("openai", 600, 290), ("claude", 800, 290), ("perplexity", 600, 490), ("gemini", 800, 490)]
    for k, (key, tx, ty) in enumerate(tiles):
        b.append('<g id="ait%d">%s</g>' % (k, art.card(tx, ty, 170, 170, fill=WHITE, sw=6, drop=11, r=26)))
        O["ait%d" % k] = "%.1f %.1f" % (tx + 85, ty + 85)
    for k in range(4):
        b.append('<g id="bit%d" style="%s"><rect x="0" y="0" width="120" height="14" rx="6" fill="%s"/></g>'
                 % (k, HID, TERRA))
    b.append(mono(785, 724, "ALL READING IT", 24, anchor="middle", fill=INK))
    A["S04"] = art.svg(1080, 950, "".join(b))
    X["S04"] = "".join(mark_img(key, tx + 35, ty + 35, 100, gid="aim%d" % k, z=28)
                       for k, (key, tx, ty) in enumerate(tiles))

    # ── s05 · and answers the person directly ────────────────────────────
    PR5 = (72, 290, 600, 338)
    PLATE_PLAN.append(("s05", "aianswer", PR5, {}))
    b = [art.card(72, 690, 560, 110, fill=WHITE, sw=6, drop=DROP, r=16)]
    b.append(mono(104, 736, "SOURCE", 22))
    b.append(txt(104, 784, "yoursite.com", 42, fill=INK, font="GeistMono", weight=700))
    b.append('<g id="srcstrike" style="%s">%s</g>' % (HID, art.strike(96, 430, 770, 8510, w=5.0)))
    O["srcstrike"] = "96 770"
    b.append('<g id="zeroN">%s</g>' % txt(876, 480, FACTS["click_pct"], 196, fill=RED, anchor="middle", ls=-10))
    O["zeroN"] = "876 410"
    b.append(mono(876, 540, FACTS["click_label1"], 21, anchor="middle", fill=INK, ls=2))
    b.append(mono(876, 572, "WHEN GOOGLE SHOWS", 21, anchor="middle", fill=INK, ls=2))
    b.append(mono(876, 604, "AN AI SUMMARY", 21, anchor="middle", fill=INK, ls=2))
    b.append(mono(1004, 666, "PEW, CITED BY CLOUDFLARE", 15, anchor="end", fill=MUTED, ls=1))
    b.append(hand(830, 790, "barely anyone clicks", size=56, rot=-7, gid="neverhand", anchor="middle", style=HID))
    O["neverhand"] = "830 770"
    A["S05"] = art.svg(1080, 950, "".join(b))
    A["S05RING"] = art.svg(1080, 950, '<g id="ansring" style="%s">%s</g>'
                           % (HID, art.circle_mark(PR5[0] + PR5[2] * 0.5, PR5[1] + PR5[3] * 0.5,
                                                   PR5[2] * 0.46, PR5[3] * 0.44, 8551, w=7.0, turns=2)))
    O["ansring"] = "%.1f %.1f" % (PR5[0] + PR5[2] * 0.5, PR5[1] + PR5[3] * 0.5)

    # ── s06 · nobody lands on your site anymore ──────────────────────────
    b = [art.card(72, 270, 936, 380, fill=WHITE, sw=6, drop=DROP, r=18)]
    b.append(mono(104, 322, "VISITORS TO YOUR SITE", 24))
    for k in range(4):
        gy = 370 + k * 70
        b.append('<path d="M104 %d H976" stroke="#EFE9E5" stroke-width="3"/>' % gy)
    high = [(110, 440), (190, 416), (270, 432), (350, 398), (430, 420), (510, 392)]
    crash = [(510, 392), (590, 430), (650, 470), (720, 540), (790, 590), (860, 606), (970, 612)]
    b.append(art.stroke("M" + " L".join("%.0f %.0f" % p for p in high), 9, colour=INK))
    L = polylen(crash)
    b.append('<path id="crashline" d="M%s" fill="none" stroke="%s" stroke-width="9" '
             'stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="%.1f" '
             'stroke-dashoffset="%.1f"/>' % (" L".join("%.0f %.0f" % p for p in crash), RED, L + 2, L + 2))
    O["crashL"] = round(L + 2, 1)
    b.append('<g id="crashdot" style="%s"><circle cx="970" cy="612" r="15" fill="%s" stroke="%s" '
             'stroke-width="5"/></g>' % (HID, RED, INK))
    O["crashdot"] = "970 612"
    b.append(chip(700, 296, 280, 56, FACTS["traffic_chip"], 8610, fill=RED, tcol=WHITE, size=24,
                  gid="dropchip", style=HID))
    O["dropchip"] = "840 324"
    # the ratio, Cloudflare Radar's own: Google against OpenAI
    b.append(art.card(72, 686, 936, 150, fill=DEEP, sw=6, drop=DROP, r=18))
    b.append(mono(104, 726, FACTS["ratio_label"], 21, fill=INK, ls=3))
    b.append(txt(160, 796, FACTS["ratio_google"], 48, fill=MUTED, ls=-1))
    b.append(txt(508, 796, "vs", 34, fill=MUTED, anchor="middle", font="GeistMono", weight=500))
    b.append(mono(104, 824, FACTS["ratio_source"], 15, fill=MUTED, ls=2))
    A["S06"] = art.svg(1080, 950, "".join(b))
    X["S06"] = (mark_img("google", 104, 752, 44, z=29) + mark_img("openai", 580, 742, 60, z=29)
                + '<div class="num" id="ratioN" style="left:650px;top:738px;width:340px;'
                  'text-align:right;font-size:84px">%d%s</div>' % (FACTS["ratio_start"], FACTS["ratio_suffix"]))

    # ── s07 · Cloudflare: Allow -> Charge, 402 ────────────────────────────
    b = []
    b.append(art.card(72, 440, 936, 400, fill=WHITE, sw=6, drop=DROP, r=18))
    b.append(txt(104, 496, "AI Crawl Control", 34, fill=INK, ls=-1))
    b.append(mono(976, 494, "YOURSITE.COM", 20, anchor="end"))
    b.append('<g id="livedot"><circle cx="410" cy="484" r="10" fill="%s" stroke="%s" stroke-width="3"/></g>' % (SAGE, INK))
    O["livedot"] = "410 484"
    b.append('<path d="M78 520 H1002" stroke="%s" stroke-width="4"/>' % "#E4DED9")
    rows = [("openai", "GPTBot"), ("claude", "ClaudeBot"), ("perplexity", "PerplexityBot")]
    CELL = [("Allow", 612), ("Charge", 736), ("Block", 860)]
    for r_, (key, name) in enumerate(rows):
        ry = 540 + r_ * 98
        b.append(txt(188, ry + 58, name, 40, ls=-1))
        b.append('<rect x="604" y="%d" width="380" height="66" rx="14" fill="%s" stroke="%s" '
                 'stroke-width="4"/>' % (ry + 12, DEEP, INK))
        for c, (lab, cx) in enumerate(CELL):
            fill = SAGE if c == 0 else DEEP
            b.append('<rect id="cc%d_%d" x="%d" y="%d" width="116" height="52" rx="10" fill="%s"/>'
                     % (r_, c, cx - 2, ry + 19, fill))
            b.append('<text id="ct%d_%d" x="%d" y="%d" text-anchor="middle" font-family="Geist" '
                     'font-weight="700" font-size="27" fill="%s">%s</text>'
                     % (r_, c, cx + 56, ry + 54, INK, lab))
        if r_ < 2:
            b.append('<path d="M104 %d H976" stroke="#EFE9E5" stroke-width="3"/>' % (ry + 94))
    b.append('<g id="cfcur" style="%s">%s</g>' % (HID, art.cursor(0, 0, 1.5)))
    b.append(stamp(770, 338, 440, 150, "402", 82, "stamp402", sub="PAYMENT REQUIRED", rot=-5))
    O["stamp402"] = "770 338"
    A["S07"] = art.svg(1080, 950, "".join(b))
    X["S07"] = (mark_img("cloudflare-wordmark", 80, 262, 0, gid="cfword", z=28, w=412, h=158)
                + "".join(mark_img(key, 112, 552 + r_ * 98, 58, z=28)
                          for r_, (key, name) in enumerate(rows)))

    # ── s08 · your information, your price ───────────────────────────────
    b = []
    b.append('<g id="infoline">%s</g>' % txt(78, 410, "YOUR INFO,", 142, ls=-7))
    O["infoline"] = "78 360"
    b.append(txt(78, 596, "YOUR PRICE.", 142, ls=-7, fill="#EAE4E0"))
    b.append('<g id="priceline" style="%s">%s%s</g>' % (HID,
             '<rect x="466" y="470" width="538" height="150" rx="10" fill="%s"/>' % TERRA,
             txt(78, 596, "YOUR PRICE.", 142, ls=-7)))
    O["priceline"] = "78 545"
    b.append(art.card(72, 680, 600, 150, fill=WHITE, sw=6, drop=DROP, r=16))
    b.append(mono(104, 726, FACTS["price_label"], 22))
    b.append(hand(850, 800, "you decide", size=70, rot=-8, gid="decidehand", anchor="middle", style=HID))
    O["decidehand"] = "850 776"
    A["S08"] = art.svg(1080, 950, "".join(b))

    # ── s09 · the crawler pays at the gate ───────────────────────────────
    b = []
    b.append(browser(620, 300, 364, 420, "yoursite.com", 8901))
    for k in range(6):
        b.append('<rect x="650" y="%d" width="%d" height="16" rx="6" fill="#CFC8C2"/>'
                 % (400 + k * 46, (290, 250, 300, 220, 280, 180)[k]))
    # the gate: a post, an arm, the sign
    b.append(art.stroke(art.wob([(562, 560), (590, 560), (590, 800), (562, 800)], 8910, 1.0, 10),
                        5, colour=INK, fill=TAN))
    b.append('<g id="gatearm"><rect x="356" y="636" width="226" height="30" rx="6" fill="%s" '
             'stroke="%s" stroke-width="5"/>%s</g>' % (WHITE, INK,
             "".join('<rect x="%d" y="638.5" width="20" height="25" fill="%s"/>' % (372 + k * 40, RED)
                     for k in range(5))))
    O["gatearm"] = "576 651"
    b.append('<g id="sign402">%s</g>' % chip(492, 480, 170, 70, "402", 8920, fill=RED, tcol=WHITE,
                                            size=40, font="Geist", ls=0))
    b.append('<g id="signpaid" style="%s">%s</g>' % (HID, chip(492, 480, 170, 70, "PAID", 8921,
                                                               fill=SAGE, tcol=INK, size=36,
                                                               font="Geist", ls=0)))
    O["signpaid"] = "577 515"
    b.append('<g id="botMove">%s%s</g>' % (art.bot(210, 600, 1.35, 8930, gid="crawler", fill=TERRA),
                                           mono(210, 812, "AI CRAWLER", 22, anchor="middle", fill=INK)))
    b.append(coin(0, 0, 30, "paycoin"))
    A["S09"] = art.svg(1080, 950, "".join(b))
    X["S09"] = mark_img("openai", 184, 684, 52, gid="botbadge", z=28)

    # ── s10 · already happening: the true numbers nearest the line ─────
    b = [mono(430, 334, FACTS["deals_label1"], 26, fill=INK, ls=4)]
    b.append(mono(430, 372, FACTS["deals_label2"], 26, fill=INK, ls=4))
    b.append(mono(430, 410, FACTS["deals_source"], 18, fill=MUTED, ls=3))
    b.append(art.card(72, 480, 936, 300, fill=WHITE, sw=6, drop=DROP, r=18))
    b.append(mono(104, 528, "PAY PER CRAWL, ON CLOUDFLARE", 22))
    b.append('<rect x="104" y="566" width="300" height="56" rx="10" fill="#F1ECE8"/>'
             '<rect x="470" y="580" width="420" height="22" rx="8" fill="#F1ECE8"/>'
             '<rect x="104" y="696" width="330" height="54" rx="10" fill="#F1ECE8"/>'
             '<rect x="640" y="694" width="320" height="58" rx="10" fill="#F1ECE8"/>')
    b.append('<g id="lg0" style="%s">%s%s%s</g>' % (HID,
             txt(104, 616, FACTS["b402"], 58, ls=-2),
             txt(470, 606, FACTS["b402_label"], 32, fill=INK, weight=600, ls=-0.5),
             mono(470, 636, FACTS["b402_source"], 16, fill=MUTED, ls=2)))
    b.append('<path d="M104 664 H976" stroke="#EFE9E5" stroke-width="3"/>')
    b.append('<g id="lg1" style="%s">%s%s</g>' % (HID,
             txt(190, 736, "Stack Overflow", 44, ls=-1.5),
             chip(640, 694, 320, 58, "TESTING IT NOW", 9030, fill=SAGE, size=24)))
    b.append(hand(1000, 842, FACTS["footnote"], size=56, rot=-3, gid="foothand", anchor="end", style=HID))
    O["foothand"] = "840 824"
    A["S10"] = art.svg(1080, 950, "".join(b))
    X["S10"] = ('<div class="num" id="bigN" style="left:80px;top:268px;width:300px;font-size:176px">5+</div>'
                + '<div class="clip" id="lgm1" data-start="%.3f" data-duration="%.3f" '
                  'data-track-index="470" style="position:absolute;left:0;top:0;z-index:29;'
                  'opacity:0">%s</div>'
                  % (SPAN["s10"][0], SPAN["s10"][1] - SPAN["s10"][0],
                     mark_img("stackoverflow", 100, 688, 72, z=29)))

    # ── s11 · CTA ────────────────────────────────────────────────────────
    b = [field(70, 252, 700, 96, 9101, gid="ctaf")]
    b.append(art.card(806, 246, 130, 120, fill=WHITE, sw=6, drop=DROP, r=22, gid="ctaCard"))
    niches = ["RECIPES", "FINANCE", "TRAVEL", "REVIEWS", "HEALTH", "YOURS?"]
    for k, name in enumerate(niches):
        c, r_ = k % 3, k // 3
        x, y = 70 + c * 300, 470 + r_ * 110
        last = k == 5
        b.append('<g id="nt%d">%s</g>' % (k, chip(x, y, 270, 80, name, 9110 + k,
                                                 fill=FIELD if last else WHITE, size=28,
                                                 tcol=INK)))
        if not last:
            b.append(stamp(x + 135, y + 40, 210, 64, "TAKEN", 38, "tk%d" % k, rot=-8 + (k % 3) * 5))
            O["tk%d" % k] = "%.1f %.1f" % (x + 135, y + 40)
    O["nt5"] = "805 620"
    A["S11"] = art.svg(1080, 950, "".join(b))
    X["S11"] = mark_img("cloudflare", 826, 256, 90, gid="ctaCF", z=31)
    return A, O, X


def build():
    words = load_words()
    caps = build_captions(words)
    PLATE_PLAN.clear()
    A, O, X = scene_art()

    EYEBROWS = [("s01", "THE OLD DEAL"), ("s02", "VISITORS = MONEY"),
                ("s03", "THEN AI SHOWED UP"), ("s04", "AI READS YOUR PAGE"),
                ("s05", "AND ANSWERS FOR YOU"), ("s06", "YOUR SITE, NOW"),
                ("s07", "CLOUDFLARE'S NEW SWITCH"), ("s08", "YOU SET THE PRICE"),
                ("s09", "THE CRAWLER PAYS"), ("s10", "ALREADY HAPPENING"),
                ("s11", "3 BUSINESS IDEAS")]

    plates = "\n  ".join(plate(sc, key, rect, 300 + i * 3, **opt)
                         for i, (sc, key, rect, opt) in enumerate(PLATE_PLAN) if key in PLATES)
    missing = [key for sc, key, rect, opt in PLATE_PLAN if key not in PLATES]
    if missing:
        print("  WARNING: no plate yet for %s" % ", ".join(missing))
    rings = artwrap("s05", 430, A["S05RING"], z=27, gid="ring_s05")

    xs = "\n  ".join(htmlwrap(n, 110 + i, X[n.upper()], z=28 if n != "s11" else 31)
                     for i, (n, a, b, r) in enumerate(SCENES) if n.upper() in X)

    parts = dict(
        XS=xs, PLATES=plates, RINGS=rings,
        BAND=bottom_band(),
        CTATYPE=typed("BOTS"),
        PRICETYPE=typed("$0.01"),
        CAPS="\n  ".join(
            '<div class="cap %s clip" id="%s" data-start="%.3f" data-duration="%.3f" '
            'data-track-index="%d">%s</div>' % (c["style"], c["id"], c["start"],
                                                c["dur"], 140 + i, c["html"])
            for i, c in enumerate(caps)),
        FACES="\n  ".join(face_frame(n, 200 + i * 2) for i, (n, a, b, r) in enumerate(SCENES)),
        EYEBROWS="\n  ".join(ebrow(n, t, 60 + i) for i, (n, t) in enumerate(EYEBROWS)),
        ARTS="\n  ".join(artwrap(n, 80 + i, A[n.upper()])
                         for i, (n, a, b, r) in enumerate(SCENES) if n.upper() in A),
        SFX=open(os.path.join(HERE, "sfx_block.html"), encoding="utf-8").read()
        if os.path.exists(os.path.join(HERE, "sfx_block.html")) else "",
        TIMES=json.dumps(T), CAM=json.dumps(CAM), CLIPS=json.dumps(CLIPS),
        ORIGINS=json.dumps(O), FACTS=json.dumps(FACTS), DUR="%.3f" % DUR, CLIP0=CLIPS["s00"],
    )
    for n, a, b, r in SCENES:
        if "__T_%s__" % n.upper() in TEMPLATE:
            parts["T_%s" % n.upper()] = "%.3f" % a
            parts["D_%s" % n.upper()] = "%.3f" % (b - a)

    unused = [k for k in parts if "__%s__" % k not in TEMPLATE]
    if unused:
        sys.exit("build: parts with no placeholder: %s" % ", ".join(sorted(unused)))
    left = re.findall(r"__([A-Z0-9_]+)__", TEMPLATE)
    missing = [k for k in set(left) if k not in parts]
    if missing:
        sys.exit("build: template wants %s" % ", ".join(sorted(missing)))

    html = TEMPLATE
    for k, v in parts.items():
        before = html
        html = html.replace("__%s__" % k, v)
        assert html != before or v == "", "part %s substituted nothing" % k

    stripped = re.sub(r"/\*.*?\*/", " ", html, flags=re.S)
    if re.search(r"visibility\s*[:\"']", stripped):
        sys.exit("build: the composition switches `visibility`. Use opacity.")
    for m in re.finditer(r"<video[^>]*>", html):
        if re.search(r"transform\s*:", m.group(0)):
            sys.exit("build: a <video> carries a CSS transform")

    g = _ClipGate()
    g.feed(html)
    if g.bad:
        sys.exit("build: %d element(s) hidden by inline opacity:0 outside a clip: %s"
                 % (len(g.bad), ", ".join(g.bad)))

    gids = set(re.findall(r'<g id="([A-Za-z0-9_]+)"', html))
    offenders = []
    for m in re.finditer(r'tl\.(?:from|to|fromTo)\(\s*"#([A-Za-z0-9_]+)"(.*?)\);', html, re.S):
        tid, body = m.group(1), m.group(2)
        if tid in gids and re.search(r"\b(scale|scaleX|scaleY|rotate|rotation)\s*:", body) \
                and "svgOrigin" not in body:
            offenders.append(tid)
    if offenders:
        sys.exit("build: SVG group(s) transformed without an svgOrigin: %s"
                 % ", ".join(sorted(set(offenders))))

    # every id the timeline names must exist (GSAP fails silently on a dead selector)
    ids = set(re.findall(r'\bid="([A-Za-z0-9_]+)"', html))
    script = html[html.index("var T = "):]
    dead = sorted({s for s in re.findall(r'"#([A-Za-z][A-Za-z0-9_]*)"(?!\s*\+)', script) if s not in ids and not re.fullmatch(r"[0-9A-Fa-f]{6}", s)})
    if dead:
        sys.exit("build: timeline names ids that do not exist: %s" % ", ".join(dead))

    for m in re.finditer(r'src="(assets/marks/[^"]+)"', html):
        assert os.path.exists(os.path.join(HERE, m.group(1))), "missing %s" % m.group(1)

    html, nfix = close_boundaries(html)
    assert nfix >= 11, "boundary pass matched only %d clips" % nfix
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(html)
    return html, caps, nfix


TEMPLATE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face{font-family:Geist;src:url('assets/fonts/geist-700.woff2') format('woff2');font-weight:700;font-display:block}
@font-face{font-family:Geist;src:url('assets/fonts/geist-600.woff2') format('woff2');font-weight:600;font-display:block}
@font-face{font-family:Geist;src:url('assets/fonts/geist-400.woff2') format('woff2');font-weight:400;font-display:block}
@font-face{font-family:GeistMono;src:url('assets/fonts/geist-mono-500.woff2') format('woff2');font-weight:500;font-display:block}
@font-face{font-family:GeistMono;src:url('assets/fonts/geist-mono-700.woff2') format('woff2');font-weight:700;font-display:block}
@font-face{font-family:Caveat;src:url('assets/fonts/caveat-700.woff2') format('woff2');font-weight:700;font-display:block}

:root{
  --paper:#FFFFFF; --deep:#F6F2F0; --ink:#1F2219; --sky:#00BCFF;
  --skyd:#0095CC; --skyink:#0077A8; --peach:#D1A68E; --red:#D9451F; --term:#4B3D35;
  --field:#F0F9FF; --muted:#6B6F66; --lav:#9A8DB0; --tan:#E8DAD2;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;overflow:hidden}
#root{width:2160px;height:3840px;position:relative;overflow:hidden;background:var(--paper)}
#stage{position:absolute;left:0;top:0;width:1080px;height:1920px;
  transform:scale(2);transform-origin:0 0;background:var(--paper);overflow:hidden}
svg{display:block;overflow:visible}
img{display:block}

#paper{position:absolute;inset:0;z-index:0;background:var(--paper)}
#bandwarm{position:absolute;left:-260px;top:640px;width:1700px;height:1500px;
  z-index:1;background:var(--deep);transform:rotate(-13deg);opacity:.85}
#glow{position:absolute;inset:0;z-index:2;pointer-events:none;
  background:radial-gradient(120% 58% at 50% 12%, #FFFFFF 0%, rgba(255,255,255,0) 62%)}

#faceScene{position:absolute;left:0;top:0;width:1080px;height:1920px;z-index:20;overflow:hidden}
#faceCam{position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:0 0}
#aroll{width:1080px;height:1920px;object-fit:cover;display:block}

.eyebrow{position:absolute;z-index:30;font-family:GeistMono;font-weight:500;
  font-size:25px;letter-spacing:.19em;color:var(--muted);white-space:nowrap;
  left:0;width:1080px;text-align:center}

.num{position:absolute;z-index:29;font-family:Geist;font-weight:700;color:var(--ink);
  letter-spacing:-.045em;line-height:1;white-space:nowrap;font-variant-numeric:tabular-nums}

.termtx{position:absolute;z-index:34;font-family:GeistMono;font-weight:700;
  font-size:64px;color:var(--skyink);white-space:pre;letter-spacing:.06em}
.termtx .ch{display:inline-block;opacity:0}
.termtx .ch.lead{opacity:1}

.cap{position:absolute;z-index:40;font-family:Geist;font-weight:700;
  letter-spacing:-.022em;line-height:1.24;color:var(--ink)}
.cap .w{font-style:normal;display:inline-block;transform-origin:50% 100%;
  margin-right:.26em}
.cap .acc{color:var(--ink);background:var(--sky);border-radius:5px;
  padding:0 10px 4px;margin:0 1px}
.cap.top{left:600px;top:986px;width:352px;font-size:42px}
.cap.xl{left:742px;top:960px;width:214px;font-size:36px}
.cap.full{left:72px;top:1462px;width:936px;font-size:46px;background:var(--paper);
  border:5px solid var(--ink);border-radius:12px;padding:10px 22px 14px;box-shadow:10px 10px 0 var(--ink)}

#band{position:absolute;left:0;top:1600px;width:1080px;height:320px;z-index:12}
#flash{position:absolute;inset:0;z-index:62;background:var(--field);opacity:0;pointer-events:none}
</style>
</head>
<body>
<div id="root" data-composition-id="root" data-start="0" data-duration="__DUR__"
     data-width="2160" data-height="3840" data-track-index="0">
<div id="stage">

  <div id="paper"></div>
  <div id="bandwarm" data-layout-allow-overflow></div>
  <div id="glow"></div>

  <div id="faceScene" style="clip-path:__CLIP0__;-webkit-clip-path:__CLIP0__">
    <div id="faceCam" data-layout-allow-overflow>
      <video id="aroll" src="assets/aroll.mp4" data-start="0" data-duration="__DUR__"
             data-track-index="1" muted playsinline></video>
    </div>
  </div>
  __FACES__

  <div id="band" class="clip" data-start="0" data-duration="__DUR__"
       data-track-index="4">__BAND__</div>

  __EYEBROWS__
  __ARTS__

  <!-- ── the real thing, moving ── -->
  __PLATES__
  __RINGS__

  <!-- ── rasters + counters: every real mark sits outside its SVG ── -->
  __XS__

  <!-- ── typed fields ── -->
  <div class="termtx clip" id="priceTx" data-start="__T_S08__" data-duration="__D_S08__"
       data-track-index="120" style="left:104px;top:742px;font-size:66px">__PRICETYPE__</div>
  <div class="termtx clip" id="ctaTx" data-start="__T_S11__" data-duration="__D_S11__"
       data-track-index="122" style="left:112px;top:262px">__CTATYPE__</div>
  <div class="clip" id="ctaSub" data-start="15.640" data-duration="1.227"
       data-track-index="123" style="position:absolute;left:70px;top:380px;width:760px;
       z-index:30;font-family:Geist;font-weight:700;font-size:46px;letter-spacing:-1.6px;
       color:var(--ink)">3 business ideas, in your DMs</div>

  __CAPS__

  <div id="flash"></div>
</div>
</div>

<audio id="voice" src="assets/aroll.mp4" data-start="0" data-duration="__DUR__"
       data-track-index="9" data-volume="1"></audio>
__SFX__

<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script>
var T = __TIMES__, CAM = __CAM__, CLIPS = __CLIPS__, O = __ORIGINS__, F = __FACTS__;
window.__timelines = window.__timelines || {};
var tl = gsap.timeline({paused:true});

/* ── the camera: a hard step at every scene boundary, never a move inside a
      scene.  His standing rule is no camera movement at all. ── */
function cut(at, key){
  var c = CAM[key];
  tl.to("#faceCam", {x:c.tx, y:c.ty, scale:c.s, duration:0.001, immediateRender:false}, at);
  tl.to("#faceScene", {clipPath:CLIPS[key], webkitClipPath:CLIPS[key],
                       duration:0.001, immediateRender:false}, at);
}
(function(){
  var c = CAM["s00"];
  tl.set("#faceCam",   {x:c.tx, y:c.ty, scale:c.s}, 0);
  tl.set("#faceScene", {clipPath:CLIPS["s00"], webkitClipPath:CLIPS["s00"]}, 0);
})();
["s01","s02","s03","s04","s05","s06","s07","s08","s09","s10","s11"].forEach(function(s){
  cut(T[s]-0.001, s); });

function flash(at, to){
  tl.fromTo("#flash", {opacity:0}, {opacity:to, duration:0.06, ease:"power1.out", immediateRender:false}, at);
  tl.to("#flash", {opacity:0, duration:0.20, ease:"power1.in"}, at+0.06);
}
function typeIn(sel, at, per){
  tl.to(sel+" .ch:not(.lead)", {opacity:1, duration:0.01, stagger:per||0.022}, at);
}
function settle(sel, at, dy){
  tl.from(sel, {y:-(dy||18), duration:0.34, ease:"power3.out"}, at+0.01);
}
function slam(sel, at, from, org, dur){
  tl.fromTo(sel, {scale:from, opacity:0, svgOrigin:org},
    {scale:1, opacity:1, duration:dur||0.30, ease:"power4.out", svgOrigin:org}, at);
}
function pop(sel, at, org, dur){
  tl.fromTo(sel, {scale:0.3, opacity:0, svgOrigin:org},
    {scale:1, opacity:1, duration:dur||0.34, ease:"back.out(2.4)", svgOrigin:org}, at);
}
function show(sel, at, dur){
  tl.fromTo(sel, {opacity:0}, {opacity:1, duration:dur||0.12, ease:"power1.out"}, at);
}
/* a counter: the text is written from a tween's own progress, so a seek to
   any frame renders the same digits */
function count(sel, at, dur, a, b, fmt){
  var el = document.querySelector(sel), o = {v:a};
  tl.fromTo(o, {v:a}, {v:b, duration:dur, ease:"power2.out", immediateRender:false,
    onUpdate:function(){ el.textContent = fmt(o.v); }}, at);
}
function commas(n){ return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ","); }

/* every eyebrow is furniture: it stands at the cut and settles */
["s01","s02","s03","s04","s05","s06","s07","s08","s09","s10","s11"].forEach(function(s){
  tl.from("#eb_"+s, {y:-8, duration:0.24, ease:"power2.out"}, T[s]+0.01);
});

/* ══ s00 · FULL.  The cover stands whole at frame 0.  The G turns, the pill nods. ══ */
settle("#art_s00", 0, 22);
tl.to("#coverG", {rotation:-14, transformOrigin:"50% 50%", duration:0.40, ease:"power2.out"}, T.years);
tl.to("#coverG", {rotation:8, transformOrigin:"50% 50%", duration:0.50, ease:"sine.inOut"}, T.years+0.40);
tl.fromTo("#warnpill", {rotation:-3, svgOrigin:O.warnpill}, {rotation:3, svgOrigin:O.warnpill,
  duration:0.30, ease:"sine.inOut"}, T.deal0);
tl.to("#warnpill", {rotation:-2, svgOrigin:O.warnpill, duration:0.30, ease:"sine.inOut"}, T.deal0+0.30);

/* ══ s01 · Google sends visitors down the road into your site ══ */
settle("#art_s01", T.s01, 16);
tl.from("#s01G", {rotation:-90, scale:0.6, transformOrigin:"50% 50%", duration:0.40,
  ease:"back.out(1.8)"}, T.s01+0.01);
(function(){
  var r = O.road;             // x0 y0 x1 y1 of the dotted road
  for (var k=0;k<5;k++){
    var at = T.sent + k*0.12, id = "#vc"+k;
    tl.fromTo(id, {x:r[0], y:r[1]-20, opacity:0}, {x:(r[0]+r[2])/2, y:(r[1]+r[3])/2-44, opacity:1,
      duration:0.20, ease:"none", immediateRender:false}, at);
    tl.to(id, {x:r[2]+30, y:r[3]-14, duration:0.20, ease:"power1.in"}, at+0.20);
    tl.to(id, {opacity:0, duration:0.06}, at+0.40);
  }
})();
count("#visN", T.sent, 0.84, 48120, 51870, commas);
for (var k=0;k<12;k++){
  tl.fromTo("#vb"+k, {scaleY:0.35, svgOrigin:O["vb"+k]}, {scaleY:1, svgOrigin:O["vb"+k],
    duration:0.26, ease:"back.out(2)"}, T.you1 + k*0.03);
}

/* ══ s02 · visitors are money ══ */
settle("#art_s02", T.s02, 16);
count("#revN", T.visitors2, 0.95, 8940, 12480, function(v){ return "$"+commas(v); });
for (var k=0;k<6;k++){
  tl.fromTo("#sn"+k, {y:-60, opacity:0}, {y:0, opacity:1, duration:0.18, ease:"power3.out",
    immediateRender:false}, T.made + k*0.075);
}
pop("#upchip", T.you2, O.upchip, 0.28);
tl.fromTo("#bignote", {rotation:-24, svgOrigin:O.bignote}, {rotation:6, svgOrigin:O.bignote,
  duration:0.60, ease:"sine.inOut"}, T.s02+0.02);
pop("#monthhand", T.money1, O.monthhand, 0.30);
flash(T.money1, 0.18);

/* ══ s03 · THE DEAL.  It shakes on "just"; on "ended" the road snaps. ══ */
tl.from("#dealword", {y:-26, duration:0.30, ease:"power3.out"}, T.s03+0.01);
tl.to("#dealword", {x:-9, duration:0.05, repeat:5, yoyo:true, ease:"none"}, T.just);
tl.fromTo("#dealstrike", {opacity:0, scaleX:0, svgOrigin:O.dealstrike},
  {opacity:1, scaleX:1, svgOrigin:O.dealstrike, duration:0.20, ease:"power3.out"}, T.ended);
slam("#endedhand", T.ended+0.10, 2.2, O.endedhand, 0.32);
show("#crack", T.ended, 0.05);
tl.to("#roadL", {rotation:16, svgOrigin:O.roadL, duration:0.34, ease:"back.in(1.4)"}, T.ended+0.02);
tl.to("#roadR", {rotation:-16, svgOrigin:O.roadR, duration:0.34, ease:"back.in(1.4)"}, T.ended+0.02);
tl.to("#s03G", {filter:"grayscale(1)", opacity:0.45, duration:0.30}, T.ended+0.10);
flash(T.ended, 0.26);

/* ══ s04 · four real AI marks; the beam reads your page line by line ══ */
for (var k=0;k<4;k++){
  tl.from("#ait"+k, {y:-20, duration:0.26, ease:"power3.out"}, T.s04+0.01+k*0.03);
  tl.from("#aim"+k, {y:-20, duration:0.26, ease:"power3.out"}, T.s04+0.01+k*0.03);
}
show("#beam", T.reads, 0.06);
tl.fromTo("#beam", {attr:{y:410}}, {attr:{y:774}, duration:0.62, ease:"none", immediateRender:false}, T.reads);
for (var k=0;k<9;k++){
  tl.to("#pl"+k, {attr:{fill:"#0095CC"}, duration:0.05}, T.reads + 0.02 + k*0.066);
}
for (var k=0;k<4;k++){
  tl.fromTo("#bit"+k, {x:150, y:430+k*90, opacity:1},
    {x:700+ (k%2)*120, y:360+(k>1?200:0), opacity:0, duration:0.30, ease:"power2.in",
     immediateRender:false}, T.page + k*0.05);
}

/* ══ s05 · a real AI answer; barely anyone clicks through ══ */
tl.from("#zeroN", {y:-24, duration:0.30, ease:"power3.out"}, T.s05+0.01);
tl.fromTo("#ansring", {opacity:0, scale:0.7, svgOrigin:O.ansring},
  {opacity:1, scale:1, svgOrigin:O.ansring, duration:0.32, ease:"power3.out"}, T.person);
tl.fromTo("#srcstrike", {opacity:0, scaleX:0, svgOrigin:O.srcstrike},
  {opacity:1, scaleX:1, svgOrigin:O.srcstrike, duration:0.22, ease:"power3.out"}, T.directly);
tl.fromTo("#zeroN", {scale:1}, {scale:1.14, svgOrigin:O.zeroN, duration:0.12, ease:"power2.out",
  yoyo:true, repeat:1, immediateRender:false}, T.directly);
pop("#neverhand", T.directly+0.14, O.neverhand, 0.30);
flash(T.directly, 0.20);

/* ══ s06 · the chart crashes; Cloudflare's ratio counts up ══ */
tl.fromTo("#crashline", {attr:{"stroke-dashoffset":O.crashL}}, {attr:{"stroke-dashoffset":0},
  duration:0.90, ease:"power2.in", immediateRender:false}, T.nobody);
pop("#crashdot", T.site-0.10, O.crashdot, 0.26);
slam("#dropchip", T.lands, 1.8, O.dropchip, 0.28);
count("#ratioN", T.ever, 1.10, F.ratio_start, F.ratio_to, function(v){ return commas(v) + F.ratio_suffix; });
tl.fromTo("#ratioN", {scale:1}, {scale:1.12, transformOrigin:"100% 50%", duration:0.12, yoyo:true,
  repeat:1, immediateRender:false}, T.anymore);
flash(T.anymore, 0.20);

/* ══ s07 · CLOUDFLARE.  Allow -> Charge, down all three rows; 402 stamped. ══ */
tl.from("#cfword", {y:-30, duration:0.36, ease:"back.out(2)"}, T.s07+0.01);
tl.fromTo("#livedot", {scale:1, svgOrigin:O.livedot}, {scale:1.6, svgOrigin:O.livedot, duration:0.22,
  yoyo:true, repeat:8, ease:"sine.inOut", immediateRender:false}, T.s07+0.05);
for (var r=0;r<3;r++){
  tl.fromTo("#cc"+r+"_0", {attr:{fill:"#A8BC86"}}, {attr:{fill:"#CFDDB6"}, duration:0.16, yoyo:true, repeat:1,
    immediateRender:false}, T.now + r*0.09);
}
tl.fromTo("#cfcur", {x:1000, y:900, opacity:0}, {x:790, y:590, opacity:1, duration:0.40, ease:"power2.out",
  immediateRender:false}, T.charge-0.42);
tl.to("#cfcur", {y:600, duration:0.06, yoyo:true, repeat:1}, T.charge-0.02);
for (var r=0;r<3;r++){
  var at = T.charge + 0.04 + r*0.11;
  tl.to("#cc"+r+"_0", {attr:{fill:"#F6F2F0"}, duration:0.06}, at);
  tl.to("#cc"+r+"_1", {attr:{fill:"#F38020"}, duration:0.06}, at);
  tl.to("#ct"+r+"_1", {attr:{fill:"#FFFFFF"}, duration:0.06}, at);
}
tl.to("#cfcur", {opacity:0, duration:0.20}, T.theai);
slam("#stamp402", T.ai2, 2.0, O.stamp402, 0.30);
flash(T.ai2, 0.24);

/* ══ s08 · YOUR INFO, YOUR PRICE ══ */
tl.fromTo("#infoline", {scale:1.24, svgOrigin:O.infoline}, {scale:1, svgOrigin:O.infoline,
  duration:0.30, ease:"power4.out"}, T.s08+0.001);
typeIn("#priceTx", T.information, 0.07);
slam("#priceline", T.your2, 1.26, O.priceline, 0.28);
pop("#decidehand", T.price+0.12, O.decidehand, 0.30);
flash(T.your2, 0.22);

/* ══ s09 · the crawler pays at the gate and walks in ══ */
tl.fromTo("#paycoin", {x:340, y:620, opacity:0}, {x:420, y:470, opacity:1, duration:0.16,
  ease:"power2.out", immediateRender:false}, T.people-0.10);
tl.to("#paycoin", {x:520, y:560, duration:0.16, ease:"power2.in"}, T.people+0.06);
tl.to("#paycoin", {opacity:0, duration:0.04}, T.people+0.22);
tl.fromTo("#gatearm", {rotation:0, svgOrigin:O.gatearm}, {rotation:78, svgOrigin:O.gatearm,
  duration:0.28, ease:"back.out(1.6)", immediateRender:false}, T.inw);
pop("#signpaid", T.inw, O.signpaid, 0.24);
tl.to("#sign402", {opacity:0, duration:0.08}, T.inw);
tl.to("#botMove", {x:150, duration:0.34, ease:"power2.inOut"}, T.inw+0.20);
tl.to("#botbadge", {x:150, duration:0.34, ease:"power2.inOut"}, T.inw+0.20);
tl.to("#botMove", {y:-10, duration:0.12, yoyo:true, repeat:3, ease:"sine.inOut"}, T.s09+0.02);
tl.to("#botbadge", {y:-10, duration:0.12, yoyo:true, repeat:3, ease:"sine.inOut"}, T.s09+0.02);

/* ══ s10 · already happening: 50+ deals, 1B+ 402s a day, Stack Overflow testing ══ */
tl.from("#bigN", {y:-20, duration:0.30, ease:"power3.out"}, T.s10+0.01);
count("#bigN", T.already, 0.62, 5, F.deals_to, function(v){ return Math.round(v) + "+"; });
tl.fromTo("#bigN", {scale:1}, {scale:1.12, transformOrigin:"0% 60%", duration:0.12, yoyo:true,
  repeat:1, immediateRender:false}, T.making);
tl.fromTo("#lg0", {x:-40, opacity:0}, {x:0, opacity:1, duration:0.22, ease:"power3.out",
  immediateRender:false}, T.money2);
tl.fromTo("#lg1", {x:-40, opacity:0}, {x:0, opacity:1, duration:0.22, ease:"power3.out",
  immediateRender:false}, T.off);
tl.fromTo("#lgm1", {x:-40, opacity:0}, {x:0, opacity:1, duration:0.22, ease:"power3.out",
  immediateRender:false}, T.off);
pop("#foothand", T.this, O.foothand, 0.30);
flash(T.money2, 0.18);

/* ══ s11 · CTA.  BOTS types beside Cloudflare; niches get taken. ══ */
tl.from("#ctaf", {y:14, duration:0.30, ease:"power3.out"}, T.s11+0.01);
tl.from("#ctaCard", {y:-16, duration:0.30, ease:"power3.out"}, T.s11+0.01);
tl.from("#ctaCF", {rotation:-60, scale:0.5, transformOrigin:"50% 50%", duration:0.44,
  ease:"back.out(1.9)"}, T.s11+0.02);
typeIn("#ctaTx", T.kw, 0.07);
tl.from("#ctaSub", {opacity:0, y:10, duration:0.24, ease:"power2.out"}, T.before);
for (var k=0;k<6;k++){ tl.from("#nt"+k, {y:-14, duration:0.26, ease:"power3.out"}, T.s11+0.01+k*0.02); }
[0,2,4].forEach(function(k, i){ slam("#tk"+k, T.niche + i*0.08, 2.2, O["tk"+k], 0.22); });
[1,3].forEach(function(k, i){ slam("#tk"+k, T.taken + i*0.08, 2.2, O["tk"+k], 0.22); });
tl.to("#nt5", {scale:1.08, svgOrigin:O.nt5, duration:0.16, yoyo:true, repeat:3, ease:"sine.inOut"}, T.taken+0.18);
flash(T.niche, 0.18);

/* ── captions: each word lifts on its own onset. ── */
document.querySelectorAll(".cap").forEach(function(cap){
  var s0 = parseFloat(cap.dataset.start);
  if (cap.id === "cap0") return;      /* frame 0 is the cover: its sentence stands whole */
  cap.querySelectorAll(".w").forEach(function(w){
    var at = parseFloat(w.dataset.t);
    if (at < 0.05 || at <= s0 + 0.001) return;
    tl.from(w, {y:16, opacity:0, duration:0.20, ease:"power3.out"}, at);
  });
});

tl.duration(__DUR__);
window.__timelines.root = tl;
</script>
</body>
</html>
"""

if __name__ == "__main__":
    html, caps, nfix = build()
    print("hf87 built · %d bytes · %d captions · %d scenes · %d boundary clips closed"
          % (len(html), len(caps), len(SCENES), nfix))
    for n, a, b, r in SCENES:
        c = CAM[n]
        print("  %-3s %6.2f-%6.2f %-7s s=%.2f tx=%7.1f ty=%7.1f crown=%6.1f chin=%6.1f  win=%s"
              % (n, a, b, r, c["s"], c["tx"], c["ty"], c["crown"], c["chin"], WIN[r]))
