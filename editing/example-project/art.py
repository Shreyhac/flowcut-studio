#!/usr/bin/env python3
r"""Drawing vocabulary for hf76 - Claude paper.

The skin is Anthropic's own design language, because the subject IS Claude and
the portfolio's locked palette is already the Anthropic family.  Every hex here
was measured off an asset Anthropic themselves published, not invented:

  paper #FAF9F5   pixel-read from anthropic.com's own webclip PNG
  ink   #141413   the `A\` glyph in that same file
  terra #D97757   the Claude mark's own fill, confirmed against claude.com's
                  favicon (11/255 mean difference, which is the 32px blur)
  peach #F2CDBE   the rewrite-highlight sweep in Anthropic's own Cowork film

Two languages, deliberately not blended:

  * the FURNITURE is crisp — hard 6px ink borders, hard offset shadows with no
    blur, flat fills.  That is neobrutalism.com (his pick #1), and it is what
    makes a real logo sitting inside it read as a mark rather than a doodle.
  * the ANNOTATION is drawn — wobbly marker circles, squiggle underlines,
    hand-lettered asides.  That is parametric.press / giorgialupi (his pick
    #6), and on a film about writing every correction should look like a
    correction somebody made by hand.

Anything that has to ACT is drawn here.  Stock is texture and material only —
the vid75 shredder lesson.

Every path is deterministic: one seeded mulberry32 per shape, so a rebuild
produces byte-identical SVG and the render engine can seek anywhere.
"""

import math

# ── palette — VAL TOWN, ported from vid73 (the $85,000 film he named) ─────
# Quantised there off a 2880x1800 dsf2 capture of val.town, not eyeballed.
# Nothing dark, no glow, no dot-grid: this skin is PRINTED, not rendered.
PAPER  = "#FFFFFF"     # val.town's paper
DEEP   = "#F6F2F0"     # the warm diagonal ground band
INK    = "#1F2219"     # the drawn outline
TERRA  = "#00BCFF"     # val.town's action blue — the accent slot
TERRAD = "#0095CC"     # one step down, for shadows under the action colour
PEACH  = "#D1A68E"     # peach fill
RED    = "#D9451F"     # marker — the orange darkened until it clears 3:1 on
                       # the warm band (#FF7250 is 2.7:1 and fails AA as text)
WHITE  = "#FFFFFF"
MUTED  = "#6B6F66"

TERMINAL = "#4B3D35"   # the warm-brown terminal card — the thing worth stealing
FIELD    = "#F0F9FF"   # the pale-blue mono input field
LAV      = "#9A8DB0"
TAN      = "#E8DAD2"
SAGE     = "#A8BC86"
LEAF     = "#9BAB7F"
CAFE     = "#697E45"
CLORANGE = "#FF7250"   # Claude orange — fills only, never type

# hf75's names kept alive so the inherited helpers keep their defaults working.
BUTTER = PEACH
ORANGE = TERRA
PINK   = PEACH

# brand accents — read out of each mark's own file by vid76/build_sprite.py.
# Nothing here is a colour invented for a company.  All four were pulled from
# the company's own site and looked at on 2026-08-27, which is the only reason
# they can be trusted at the sizes this film shows them.
ACCENT = {
    "claude": "#D97757", "anthropic": "#141413",
    "github": "#141413", "wikipedia": "#141413",
}


def prng(seed):
    """mulberry32 — the same generator the composition uses, so art and motion
    share a seed and stay reproducible across rebuilds."""
    state = [seed & 0xFFFFFFFF]

    def nxt():
        state[0] = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = state[0]
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t ^= (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)) & 0xFFFFFFFF
        t &= 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return nxt


def wob(points, seed, amp=1.4, seg=13, close=True):
    """Resample a polyline and push each sample off the line by a small seeded
    amount — a straight edge that is never quite straight, and never straight
    the same way twice."""
    r = prng(seed)
    pts = list(points)
    if close:
        pts = pts + [pts[0]]
    out = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        n = max(2, int(length / seg))
        for k in range(n):
            t = k / n
            off = (r() - 0.5) * 2 * amp
            out.append((x0 + dx * t + nx * off, y0 + dy * t + ny * off))
    if close:
        out.append(out[0])
    else:
        off = (r() - 0.5) * 2 * amp
        out.append((pts[-1][0], pts[-1][1] + off))
    d = "M%.1f %.1f" % out[0]
    for p in out[1:]:
        d += " L%.1f %.1f" % p
    if close:
        d += " Z"
    return d


def blob(cx, cy, rx, ry, seed, amp=4.0, n=44):
    """A closed hand-drawn blob."""
    r = prng(seed)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + (r() - 0.5) * 2 * amp / max(rx, ry)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    d = "M%.1f %.1f" % pts[0]
    for i in range(1, len(pts) + 1):
        p0 = pts[(i - 1) % n]
        p1 = pts[i % n]
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        d += " Q%.1f %.1f %.1f %.1f" % (p0[0], p0[1], mx, my)
    return d + " Z"


def hatch(x, y, w, h, seed, step=11, angle=-58, weight=1.6, colour=None):
    """Diagonal pencil hatching — the anti-gradient: texture that survives
    H.264 where a linear ramp bands."""
    r = prng(seed)
    colour = colour or INK
    out = []
    t = math.tan(math.radians(angle))
    k = -int(abs(h * t)) - step
    while k < w + step:
        x0, y0 = x + k, y + h
        x1, y1 = x + k + h * t * -1, y
        j = (r() - 0.5) * 2.2
        out.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="%s" stroke-width="%.2f" '
                   'stroke-linecap="round" fill="none"/>' % (x0 + j, y0, x1 + j, y1, colour, weight))
        k += step
    return "".join(out)


def stroke(d, w=4.4, colour=None, fill="none", extra=""):
    return ('<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f" '
            'stroke-linejoin="round" stroke-linecap="round"%s/>'
            % (d, fill, colour or INK, w, (" " + extra) if extra else ""))


# ══ FURNITURE — crisp, neobrutalism ══════════════════════════════════════
def card(x, y, w, h, fill=WHITE, sw=6, drop=13, r=6, gid=None, shadow=INK):
    """Hard ink border, hard offset shadow, no blur.  The shadow is a solid
    rect behind the card, not a filter — a blur would read as SaaS chrome and
    is the one thing his taste rejects across all 147 sites.
    """
    p = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s"/>'
         % (x + drop, y + drop, w, h, r, shadow),
         '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s" '
         'stroke="%s" stroke-width="%d"/>' % (x, y, w, h, r, fill, INK, sw)]
    return '<g%s>%s</g>' % ((' id="%s"' % gid) if gid else "", "".join(p))


def pill(x, y, w, h, fill=BUTTER, sw=5, drop=8, gid=None):
    return card(x, y, w, h, fill=fill, sw=sw, drop=drop, r=h / 2, gid=gid)


def mark(key, cx, cy, size, gid=None, extra=""):
    """Place a real brand mark from the namespaced sprite, centred."""
    return ('<use%s href="#mk_%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"%s/>'
            % ((' id="%s"' % gid) if gid else "", key,
               cx - size / 2, cy - size / 2, size, size,
               (" " + extra) if extra else ""))


def mark_badge(key, cx, cy, r, gid=None, fill=WHITE, sw=6, drop=10):
    """A mark inside a hard-bordered disc — what stands in for a head on the
    drawn bodies, and what the keycaps carry.

    Groq's logo is not an icon, it is a filled orange TILE with a white bolt in
    it.  A square tile dropped inside a round badge reads as a mistake, so the
    badge itself is filled Groq orange and only the bolt goes on top.
    """
    if key == "groq":
        face, glyph, gsz = ACCENT["groq"], "groq_bolt", 1.02
    else:
        face, glyph, gsz = fill, key, 1.20
    p = ['<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (cx + drop * 0.6, cy + drop * 0.7, r, INK),
         '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%d"/>'
         % (cx, cy, r, face, INK, sw),
         mark(glyph, cx, cy, r * gsz)]
    return '<g%s>%s</g>' % ((' id="%s"' % gid) if gid else "", "".join(p))


def keycap(cx, cy, w, h, key, accent, seed, label="", gid=None):
    """The hook's keys.  A keycap, not a door key: the thing being handed out
    is an API key, and a keyboard cap with a real mark on it says that in one
    glance where a brass key would say 'security'.

    The label is not decoration.  Groq's mark is a stylised lowercase g that
    reads as a numeral 9 at reel scale — a real mark nobody can name is worth
    nothing, so every cap is captioned.
    """
    face = ACCENT["groq"] if key == "groq" else WHITE
    glyph = "groq_bolt" if key == "groq" else key
    p = [card(cx - w / 2, cy - h / 2, w, h, fill=accent, sw=6, drop=14, r=14),
         '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s" '
         'stroke="%s" stroke-width="4"/>'
         % (cx - w * 0.37, cy - h * 0.40, w * 0.74, h * 0.62, 9, face, INK),
         mark(glyph, cx, cy - h * 0.09, min(w * 0.46, h * 0.40))]
    if label:
        p.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="%s" font-family="Geist" '
                 'font-weight="700" font-size="26" letter-spacing=".02em">%s</text>'
                 % (cx, cy + h * 0.40, INK, label))
    return '<g%s>%s</g>' % ((' id="%s"' % gid) if gid else "", "".join(p))


def stroke_box(w, h, r=7, sw=6):
    """A frame is a STROKE.  Anything painted above a video fills with none —
    a filled rect at z-index above the plate renders the plate as a black
    rectangle and every gate passes, because the rect is correctly positioned.
    """
    return ('<svg viewBox="0 0 %d %d" width="%d" height="%d" style="overflow:visible">'
            '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="none" '
            'stroke="%s" stroke-width="%d"/></svg>'
            % (w, h, w, h, sw // 2, sw // 2, w - sw, h - sw, r, INK, sw))


# ══ CAST — drawn, pudding.cool ═══════════════════════════════════════════
def figure(x, base, h, seed, shirt=ORANGE, head_r=None, arm="down",
           trouser="#2E3440", shoe=INK, gid=""):
    """A flat drawn body with an EMPTY head.  The head sits deliberately
    oversized on the body; that exaggeration is the device, not an accident.

    Returns (svg, (head_cx, head_cy, head_r)) so the caller can drop the real
    mark into the gap.
    """
    head_r = head_r or h * 0.20
    hcx, hcy = x, base - h + head_r
    neck = hcy + head_r * 0.92
    sh_y = neck + h * 0.030
    hip_y = base - h * 0.42
    bw = h * 0.155

    p = ['<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" opacity=".16"/>'
         % (x, base + 6, h * 0.155 * 1.9, h * 0.022, INK)]      # seat it
    for s in (-1, 1):                                     # arms first
        ax = x + s * bw * 0.86
        aw = h * 0.042
        if arm == "up" and s > 0:
            e = (ax + h * 0.115, sh_y - h * 0.125)
        else:
            e = (ax + s * h * 0.032, sh_y + h * 0.215)
        armp = [(ax - aw, sh_y + h * 0.012), (ax + aw, sh_y + h * 0.012),
                (e[0] + aw * 0.82, e[1]), (e[0] - aw * 0.82, e[1])]
        p.append(stroke(wob(armp, seed + 41 + s, 1.1, 12), 3.8, fill=shirt))
    for s in (-1, 1):                                     # legs + shoes
        lx = x + s * bw * 0.46
        lw = bw * 0.40
        leg = [(lx - lw, hip_y), (lx + lw, hip_y),
               (lx + lw * 0.86 + s * 3, base - h * 0.035), (lx - lw * 0.86 + s * 3, base - h * 0.035)]
        p.append(stroke(wob(leg, seed + 13 + s, 1.2, 12), 3.8, fill=trouser))
        sy = base - h * 0.035
        shoep = [(lx - lw * 0.95 + s * 3, sy), (lx + lw * 0.95 + s * 3, sy),
                 (lx + lw * 1.25 + s * 6, base), (lx - lw * 1.05 + s * 3, base)]
        p.append(stroke(wob(shoep, seed + 29 + s, 0.9, 10), 3.4, fill=shoe))
    torso = [(x - bw, sh_y), (x + bw, sh_y),
             (x + bw * 0.90, hip_y + h * 0.02), (x - bw * 0.90, hip_y + h * 0.02)]
    p.append(stroke(wob(torso, seed + 3, 1.5, 12), 4.6, fill=shirt))
    p.append(stroke(wob([(x - head_r * 0.24, neck - head_r * 0.34),
                         (x + head_r * 0.24, neck - head_r * 0.34),
                         (x + head_r * 0.24, sh_y + 3), (x - head_r * 0.24, sh_y + 3)],
                        seed + 77, 0.8, 9), 3.4, fill="#E7C4A8"))
    g = '<g%s>%s</g>' % ((' id="%s"' % gid) if gid else "", "".join(p))
    return g, (hcx, hcy, head_r)


def hand_from(fx, base, h, seed):
    """Where figure()'s raised hand actually ends up.  Solved from the same
    geometry the body is drawn with — eyeballing this is what puts a prop in
    the figure's ear."""
    head_r = h * 0.21
    sh_y = (base - h + head_r) + head_r * 0.92 + h * 0.030
    bw = h * 0.155
    ax = fx + bw * 0.86
    return (ax + h * 0.115, sh_y - h * 0.125)


# ══ PROPS ════════════════════════════════════════════════════════════════
def shredder(x, y, w, h, seed, body="#5A6472"):
    """A drawn office shredder.  Only the machine is drawn — the paper going
    through it is the real Pinterest clip, framed inside the slot."""
    p = [stroke(wob([(x, y), (x + w, y), (x + w * 0.94, y + h), (x + w * 0.06, y + h)],
                    seed, 1.6, 15), 5.0, fill=body),
         # the throat
         stroke(wob([(x + w * 0.12, y + h * 0.16), (x + w * 0.88, y + h * 0.16),
                     (x + w * 0.88, y + h * 0.28), (x + w * 0.12, y + h * 0.28)],
                    seed + 5, 1.0, 11), 4.0, fill=INK)]
    r = prng(seed + 9)
    for i in range(7):                                     # teeth
        tx = x + w * (0.17 + i * 0.11)
        p.append(stroke("M%.1f %.1f L%.1f %.1f"
                        % (tx, y + h * 0.175, tx + (r() - 0.5) * 4, y + h * 0.265), 2.6, WHITE))
    return "".join(p)


def strips(x, y, w, n, seed, colour=WHITE):
    """Shredded paper strips falling out of the slot — drawn, so they can be
    staggered per strip on the beat rather than baked into the clip."""
    r = prng(seed)
    out = []
    for i in range(n):
        sx = x + w * (i + 0.5) / n + (r() - 0.5) * 9
        L = 42 + r() * 74
        d = "M%.1f %.1f L%.1f %.1f" % (sx, y, sx + (r() - 0.5) * 16, y + L)
        # ink under, pale over: a white strip on cream paper is not a strip,
        # it is nothing, and it passed every gate on the first render.
        out.append('<g id="sp%d_%d" style="transform-origin:%.1fpx %.1fpx">%s%s</g>'
                   % (seed, i, sx, y, stroke(d, 9.0, INK), stroke(d, 5.4, colour)))
    return "".join(out)


def arrow(x0, y0, x1, y1, seed, bend=34, w=4.6, head=18, colour=None):
    """A hand-drawn curved arrow — the annotation axis of his taste, pointing
    at whatever the VO just named."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1
    nx, ny = -dy / length, dx / length
    cx, cy = mx + nx * bend, my + ny * bend
    d = "M%.1f %.1f Q%.1f %.1f %.1f %.1f" % (x0, y0, cx, cy, x1, y1)
    ang = math.atan2(y1 - cy, x1 - cx)
    h1 = "M%.1f %.1f L%.1f %.1f" % (x1, y1, x1 + math.cos(ang + math.radians(150)) * head,
                                    y1 + math.sin(ang + math.radians(150)) * head)
    h2 = "M%.1f %.1f L%.1f %.1f" % (x1, y1, x1 + math.cos(ang - math.radians(150)) * head,
                                    y1 + math.sin(ang - math.radians(150)) * head)
    c = colour or RED
    return stroke(d, w, c) + stroke(h1, w, c) + stroke(h2, w, c)


def circle_mark(cx, cy, rx, ry, seed, w=5.4, colour=None, turns=1):
    """The marker circle drawn round the thing that is actually true."""
    r = prng(seed)
    d = ""
    for k in range(turns):
        n = 44
        for i in range(n + 1):
            a = -math.pi * 0.55 + 2 * math.pi * (i / n) + k * 0.22
            k2 = 1 + (r() - 0.5) * 0.11
            px = cx + math.cos(a) * rx * k2 + k * 5
            py = cy + math.sin(a) * ry * k2 - k * 3
            d += ("M%.1f %.1f " % (px, py)) if i == 0 and k == 0 else ("L%.1f %.1f " % (px, py))
    return stroke(d.strip(), w, colour or RED)


def strike(x0, x1, y, seed, w=9.0, colour=None):
    """A marker strike-through.  Two passes, because one pass reads as an
    underline that drifted."""
    r = prng(seed)
    d = ""
    for k in range(2):
        n = 16
        for i in range(n + 1):
            t = i / n
            px = x0 + (x1 - x0) * t
            py = y + (r() - 0.5) * 5.5 + k * 5 - 2
            d += ("M%.1f %.1f " % (px, py)) if i == 0 and k == 0 else ("L%.1f %.1f " % (px, py))
    return stroke(d.strip(), w, colour or RED)


def svg(w, h, body, extra="", gid=None):
    """Wrap a body.  overflow:visible is not optional — a prop drawn at a
    negative coordinate (a raised hand, a shadow) is silently CLIPPED by the
    viewBox otherwise, and the render looks merely wrong rather than broken."""
    return ('<svg%s viewBox="0 0 %d %d" width="%d" height="%d" '
            'style="overflow:visible"%s>%s</svg>'
            % ((' id="%s"' % gid) if gid else "", w, h, w, h,
               (" " + extra) if extra else "", body))


def stub_rect(x, y, w, h, r=10):
    """A pale dashed placeholder.  Staggering content in from nothing leaves
    the paper bare for a third of a short scene, and a void is a defect even
    when every element that will land there is individually correct."""
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" '
            'stroke="%s" stroke-width="5" stroke-dasharray="16 13" opacity=".5"/>'
            % (x, y, w, h, r, DEEP, "#B9A98A"))


def stub_rules(x, y, w, n, step, weight=9):
    """Three pale rules where three mono lines are about to land."""
    return "".join('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" rx="%d" fill="%s" '
                   'opacity=".55"/>' % (x, y + i * step, w * (1 - i * 0.13), weight,
                                        weight // 2, "#DED4BB")
                   for i in range(n))


def shredder_machine(w, h, seed, body="#4E5A6B", plate="#333C49"):
    """A shredder drawn IN the skin, with its parts separable so they can move.

    The photographed one was rejected as "random weird b roll": a grey
    institutional bin does not belong on printed cream paper, and a still photo
    of a machine cannot turn its own teeth.  Drawn, the throat can swallow the
    card, the teeth can spin and the strips can fall — the beat animates
    instead of merely playing.

    Ids emitted: #shTeeth (one pitch of travel loops seamlessly), #shMouth.
    """
    r = prng(seed)
    p = []
    # feet, then body, so the ink edge of the body sits over their roots
    for fx in (w * 0.17, w * 0.83):
        p.append(stroke(wob([(fx - 26, h - 16), (fx + 26, h - 16),
                             (fx + 18, h), (fx - 18, h)], seed + 61, 1.0, 10), 4.0, fill=INK))
    # the body is inset so the top plate can overhang it and still stay inside
    # the host box — a shape that paints outside its own div is invisible to
    # every gate but the one that measures it
    p.append(stroke(wob([(14, 78), (w - 14, 78), (w * 0.90, h - 12), (w * 0.10, h - 12)],
                        seed + 3, 1.6, 16), 6.0, fill=body))
    p.append(stroke(wob([(4, 4), (w - 4, 4), (w - 10, 78), (10, 78)], seed + 7, 1.3, 15),
                    6.0, fill=plate))
    # the mouth: a dark slot with a moving tooth rail inside it
    mx0, mx1, my0, my1 = w * 0.16, w * 0.84, 24, 56
    p.append('<rect id="shMouth" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6" '
             'fill="%s"/>' % (mx0, my0, mx1 - mx0, my1 - my0, "#161A1F"))
    teeth = []
    pitch = 34.0
    n = int((mx1 - mx0) / pitch) + 3
    for i in range(n):
        tx = mx0 + i * pitch
        teeth.append('<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f Z" fill="%s"/>'
                     % (tx, my1 - 3, tx + pitch * 0.44, my0 + 4, tx + pitch * 0.88, my1 - 3, "#E8E4DA"))
    p.append('<g clip-path="url(#shclip%d)"><g id="shTeeth">%s</g></g>' % (seed, "".join(teeth)))
    p.append('<clipPath id="shclip%d"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6"/>'
             '</clipPath>' % (seed, mx0, my0, mx1 - mx0, my1 - my0))
    # a lit status pip and vent hatching, so the body is not a flat slab
    # hatch() over-draws its parallelogram by design and relies on a clip; used
    # bare it reached 40px left of the host box and the INBOX gate caught it
    hx, hy, hw, hh = w * 0.12, 118, w * 0.30, 62
    p.append('<clipPath id="shvent%d"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
             '</clipPath>' % (seed, hx, hy, hw, hh))
    p.append('<g clip-path="url(#shvent%d)">%s</g>'
             % (seed, hatch(hx, hy, hw, hh, seed + 21, step=13, weight=2.0, colour="#39424E")))
    p.append('<circle cx="%.1f" cy="%.1f" r="12" fill="%s" stroke="%s" stroke-width="4"/>'
             % (w * 0.84, 132, "#7ED957", INK))
    # a butter band across the body — four flat inks, and grey alone is drab
    p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="16" rx="8" fill="%s" '
             'stroke="%s" stroke-width="4"/>' % (w * 0.50, 124, w * 0.26, BUTTER, INK))
    return "".join(p), (mx0 + (mx1 - mx0) / 2.0, my1), pitch


def tray(w, seed, fill=DEEP):
    """The catch tray the strips fall into — closes the machine off so the
    strips do not read as hanging sticks."""
    return stroke(wob([(w * 0.06, 0), (w * 0.94, 0), (w * 0.86, 92), (w * 0.14, 92)],
                      seed, 1.4, 14), 5.4, fill=fill)


def cursor(x, y, s=1.0):
    """A drawn pointer.  A UI panel that merely appears is a picture of a
    product; a pointer that travels to the button and presses it is the beat
    the voice-over is actually describing."""
    d = ("M0 0 L0 %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z"
         % (30 * s, 8.4 * s, 22.2 * s, 13.8 * s, 30 * s, 20.4 * s, 8.4 * s))
    return ('<g transform="translate(%.1f %.1f)">%s%s</g>'
            % (x, y, stroke(d, 7.0, INK, fill=INK), stroke(d, 3.0, WHITE, fill=WHITE)))


# ══ hf76 ADDITIONS ═══════════════════════════════════════════════════════
# Everything below exists because this film is about WRITING, so its whole
# argument is made on top of prose: a tell is marked the way a human marks a
# proof, and the corrections have to look hand-made or they read as UI.

def squiggle(x0, x1, y, seed, w=5.0, colour=None, amp=5.5, wave=26.0):
    """The proof-reader's wavy underline.  A straight rule under a phrase reads
    as a link; a wave reads as 'this is wrong', which is the whole point."""
    colour = colour or RED
    n = max(4, int(abs(x1 - x0) / wave))
    r = prng(seed)
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        pts.append((x, y + math.sin(t * math.pi * 2 * (n / 2.0)) * amp
                    + (r() - 0.5) * 1.6))
    d = "M%.1f %.1f" % pts[0]
    for i in range(1, len(pts)):
        px, py = pts[i - 1]
        cx, cy = pts[i]
        d += " Q%.1f %.1f %.1f %.1f" % ((px + cx) / 2, py - amp * 0.9, cx, cy)
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%.1f" '
            'stroke-linecap="round"/>' % (d, colour, w))


def cross(cx, cy, s, seed, w=6.0, colour=None):
    """U+2717 is not in Instrument Serif's latin subset and would ship as tofu
    ([[glyph coverage is a gate]]), so every mark of this class is drawn."""
    colour = colour or RED
    r = prng(seed)
    j = lambda: (r() - 0.5) * s * 0.09
    return ('<path d="M%.1f %.1f L%.1f %.1f M%.1f %.1f L%.1f %.1f" stroke="%s" '
            'stroke-width="%.1f" stroke-linecap="round" fill="none"/>'
            % (cx - s / 2 + j(), cy - s / 2 + j(), cx + s / 2 + j(), cy + s / 2 + j(),
               cx + s / 2 + j(), cy - s / 2 + j(), cx - s / 2 + j(), cy + s / 2 + j(),
               colour, w))


def check(cx, cy, s, seed, w=6.0, colour=None):
    colour = colour or "#3B7A3B"
    r = prng(seed)
    j = lambda: (r() - 0.5) * s * 0.07
    return ('<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f" stroke="%s" '
            'stroke-width="%.1f" stroke-linecap="round" stroke-linejoin="round" '
            'fill="none"/>'
            % (cx - s * 0.46 + j(), cy + j(), cx - s * 0.10 + j(), cy + s * 0.38 + j(),
               cx + s * 0.48 + j(), cy - s * 0.42 + j(), colour, w))


def caret(cx, cy, s, seed, w=5.0, colour=None):
    """An editor's insertion caret — the mark you make when something is
    MISSING, which is what the rewrite beat is actually doing."""
    colour = colour or RED
    r = prng(seed)
    j = lambda: (r() - 0.5) * s * 0.08
    return ('<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f" stroke="%s" '
            'stroke-width="%.1f" stroke-linecap="round" stroke-linejoin="round" '
            'fill="none"/>'
            % (cx - s / 2 + j(), cy + s / 2, cx + j(), cy - s / 2 + j(),
               cx + s / 2 + j(), cy + s / 2, colour, w))


def halftone_css(cx, cy, r_in, r_out, dot=3.2, step=13.0, colour=TERRA, op=0.85):
    """Anthropic's halftone dot field, as a CSS background instead of a few
    thousand <circle>s.

    Their own films resolve every field this way — a dot screen, never a
    gradient — and it is the texture his theme bank already names as the
    anti-gradient move.  Radial only: a linear ramp bands in H.264.

    Returns a `background` value; the density ramp is a radial mask, so the
    dots stay the same SIZE and only their VISIBILITY falls off.  Scaling the
    dots instead produces a blur, which is the look this is avoiding.
    """
    return ("background-image:radial-gradient(%s %.1fpx, transparent %.1fpx);"
            "background-size:%.1fpx %.1fpx;"
            "-webkit-mask-image:radial-gradient(circle %.0fpx at %.0fpx %.0fpx,"
            "#000 0%%, #000 %.0f%%, transparent 100%%);"
            "mask-image:radial-gradient(circle %.0fpx at %.0fpx %.0fpx,"
            "#000 0%%, #000 %.0f%%, transparent 100%%);opacity:%.2f"
            % (colour, dot, dot + 0.9, step, step,
               r_out, cx, cy, 100.0 * r_in / max(r_out, 1), 
               r_out, cx, cy, 100.0 * r_in / max(r_out, 1), op))


def rule(x, y, w, weight=5, colour=None):
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" fill="%s"/>'
            % (x, y, w, weight, colour or INK))


def highlight(x, y, w, h, seed, colour=PEACH, skew=3.0):
    """Anthropic's own rewrite-highlight: a flat peach block behind a phrase,
    edges very slightly off-square so it reads as laid down by hand rather than
    as a `<mark>` tag."""
    r = prng(seed)
    j = lambda a: (r() - 0.5) * a
    return ('<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z" fill="%s"/>'
            % (x + j(skew), y + j(skew), x + w + j(skew), y - j(skew) + skew * .3,
               x + w + j(skew), y + h + j(skew), x + j(skew), y + h - j(skew),
               colour))


def dogear(x, y, w, h, seed, fill=WHITE, sw=6, drop=13, fold=54):
    """A page, not a panel.  The turned corner is the cheapest signal that the
    thing on screen is a document, and this film only ever shows documents."""
    r = prng(seed)
    j = lambda: (r() - 0.5) * 2.2
    body = ("M%.1f %.1f H%.1f L%.1f %.1f V%.1f H%.1f Z"
            % (x, y, x + w - fold, x + w + j(), y + fold, y + h, x))
    return ('<path d="%s" fill="%s" transform="translate(%d,%d)"/>'
            '<path d="%s" fill="%s" stroke="%s" stroke-width="%d" '
            'stroke-linejoin="round"/>'
            '<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f" fill="%s" stroke="%s" '
            'stroke-width="%d" stroke-linejoin="round"/>'
            % (body, INK, drop, drop,
               body, fill, INK, sw,
               x + w - fold, y, x + w - fold, y + fold, x + w, y + fold, DEEP, INK, sw))


# ══ THE CAST — drawn characters that ACT ═════════════════════════════════
# His standing rule since vid57: "animation" means a CHARACTER, not an
# interface.  Asked for an animation of an AI forgetting, I built an agent
# terminal with a draining context bar; he wanted a drawn bot with a face that
# visibly loses its memories.  Same note again on this film: "the entire video
# is text heavy, need more visuals and graphics."
#
# So the film gets a cast of two.  The BOT types the AI slop and gets caught.
# The PEN is the human hand — it does every correction on screen.  Both are
# flat, ink-outlined, and built out of named parts so the motion is
# choreography rather than a swap between two drawings.

def bot(cx, cy, s, seed, gid="bot", fill=None, caught=False):
    """A drawn robot in a 220x260 box, centred on (cx, cy) at scale s.

    Named parts, all animatable:
      <gid>Ant   antenna dot        <gid>EyeL/<gid>EyeR   pupils
      <gid>ArmL/<gid>ArmR           <gid>Mouth            the mouth bar
      <gid>XL/<gid>XR               the dead eyes, opacity 0 until it is caught
    """
    fill = fill or TERRA
    r = prng(seed)
    j = lambda a: (r() - 0.5) * a
    HW, HH = 150.0, 122.0                     # head
    hx, hy = cx - HW / 2, cy - HH / 2 - 18
    p = []
    # antenna
    p.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="%s" stroke-width="7" '
             'stroke-linecap="round" fill="none"/>'
             % (cx, hy, cx + j(6), hy - 40, INK))
    p.append('<circle id="%sAnt" cx="%.1f" cy="%.1f" r="13" fill="%s" stroke="%s" '
             'stroke-width="6"/>' % (gid, cx + j(6), hy - 46, WHITE, INK))
    # body first, so the head sits over its shoulders
    bw, bh = 118.0, 74.0
    bx, by = cx - bw / 2, cy + HH / 2 - 16
    p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="16" fill="%s" '
             'stroke="%s" stroke-width="6"/>' % (bx, by, bw, bh, DEEP, INK))
    for side, aid in ((-1, "ArmL"), (1, "ArmR")):
        ax = cx + side * (bw / 2 + 15)
        p.append('<g id="%s%s" style="transform-box:fill-box;transform-origin:%s 20%%">'
                 '<rect x="%.1f" y="%.1f" width="20" height="58" rx="10" fill="%s" '
                 'stroke="%s" stroke-width="6"/></g>'
                 % (gid, aid, "50%", ax - 11, by + 2, fill, INK))
    # head
    p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="26" fill="%s" '
             'stroke="%s" stroke-width="7"/>' % (hx, hy, HW, HH, fill, INK))
    for side, eid in ((-1, "EyeL"), (1, "EyeR")):
        ex = cx + side * 32
        ey = hy + 46
        p.append('<circle cx="%.1f" cy="%.1f" r="23" fill="%s" stroke="%s" '
                 'stroke-width="5"/>' % (ex, ey, WHITE, INK))
        p.append('<circle id="%s%s" cx="%.1f" cy="%.1f" r="10" fill="%s"/>'
                 % (gid, eid, ex + j(2), ey + 2, INK))
        # the dead eye, parked invisible until the bot is caught
        p.append('<g id="%s%s" opacity="%d">%s</g>'
                 % (gid, "XL" if side < 0 else "XR", 1 if caught else 0,
                    cross(ex, ey, 30, seed + 11 + side, w=7.0, colour=INK)))
    p.append('<rect id="%sMouth" x="%.1f" y="%.1f" width="56" height="13" rx="6" '
             'fill="%s"/>' % (gid, cx - 28, hy + 88, INK))
    # the scale argument was accepted and never applied on the first pass, so
    # every placement drew at 1.0 wherever the caller thought it had shrunk it
    return ('<g id="%sW" transform="translate(%.2f,%.2f) scale(%.4f) translate(%.2f,%.2f)">'
            '%s</g>' % (gid, cx, cy, s, -cx, -cy, "".join(p)))


def bot_extent(cx, cy, s):
    """The bot's real painted box, antenna and shadowless body included, so a
    caller can assert it clears his chin instead of guessing at a sprite size."""
    return (cx - 90 * s, cy - 138 * s, cx + 90 * s, cy + 119 * s)


def pen(x, y, s, seed, gid="pen", angle=30.0):
    """A drawn fountain pen whose NIB TIP is exactly at (x, y).

    Drawn nib-down along -y and rotated about the tip, so the caller positions
    the point that does the work rather than the middle of a sprite.  The first
    version built it around an implicit origin and the nib rendered at the wrong
    end of the barrel — a mark then appears from the cap.
    """
    r = prng(seed)
    p = [  # nib
        '<path d="M0 0 L-15 -34 L15 -34 Z" fill="%s"/>' % INK,
        '<path d="M0 -3 L0 -32" stroke="%s" stroke-width="3.5" stroke-linecap="round"/>'
        % PAPER,
        # grip
        '<rect x="-18" y="-64" width="36" height="32" rx="7" fill="%s" stroke="%s" '
        'stroke-width="5"/>' % (DEEP, INK),
        # barrel
        '<rect x="-20" y="-228" width="40" height="166" rx="16" fill="%s" stroke="%s" '
        'stroke-width="6"/>' % (TERRA, INK),
        # cap band
        '<rect x="-20" y="-254" width="40" height="30" rx="13" fill="%s" stroke="%s" '
        'stroke-width="6"/>' % (INK, INK),
    ]
    # NO baked transform.  GSAP parses an existing one and then rotates about
    # the element's own bbox centre, which put the nib 84px up-left of every
    # target; the caller sets svgOrigin "0 0" instead, so rotation and scale
    # happen about the NIB and x/y are literally where the nib goes.
    return '<g id="%s">%s</g>' % (gid, "".join(p))


def ticker(x, y, w, h, seed, fill=None):
    """The bot's output: a hard-bordered strip it types into."""
    fill = fill or WHITE
    # the tail points LEFT, at the bot standing beside it — a tail on the top
    # edge reads as a tooltip, not as something the character is saying
    ty = y + h * 0.42
    return (card(x, y, w, h, fill=fill, sw=6, drop=11, r=10)
            + '<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f Z" fill="%s" stroke="%s" '
              'stroke-width="6" stroke-linejoin="round"/>'
              % (x, ty - 26, x - 30, ty + 4, x, ty + 32, fill, INK)
            + '<rect x="%.1f" y="%.1f" width="8" height="52" fill="%s"/>'
              % (x - 1, ty - 22, fill))


# ══ vid79 — THE DARIO DEVICE ═════════════════════════════════════════════
# A real photographed head, cut out, on a hand-drawn flat body.  Ported from
# vid73 (the $85,000 film) where it carried Dario on the word "Anthropic".
#
# The head is placed by MEASURED SPAN, never by PNG box.  vid79/ref/
# dario-head.png is 939x1270 but the head inside it is only 887 wide and the
# chin sits at y1193 — a fifth of the file is hair-air and collar.  Sizing the
# file to the drawn head's diameter puts a balloon on a doll.  Measured on the
# cut-out itself with the same Vision binaries used for the A-roll:
DARIO_PNG   = "assets/media/dario-head.png"
DARIO_W     = 939.0
DARIO_H     = 1270.0
DARIO_HEADW = 886.9 / DARIO_W      # 0.9445 — head span as a fraction of file
DARIO_CHIN  = 1193.0 / DARIO_H     # 0.9394 — chin height as a fraction
DARIO_MIDX  = 470.1 / DARIO_W      # 0.5006 — head silhouette midpoint


def head_photo(cx, chin_y, head_w, src=DARIO_PNG, over=1.16, gid=None,
               extra="", attrs=""):
    """Place the cut-out head so its MEASURED head span is `head_w` wide and
    its MEASURED chin lands on `chin_y`.  `over` is the deliberate
    exaggeration that makes it a caricature rather than a paste-up."""
    hw = head_w * over
    iw = hw / DARIO_HEADW
    ih = iw * (DARIO_H / DARIO_W)
    left = cx - DARIO_MIDX * iw
    top = chin_y - DARIO_CHIN * ih
    return ('<img src="%s" alt="" width="%.1f" height="%.1f" style="position:'
            'absolute;left:%.1fpx;top:%.1fpx;width:%.1fpx;height:%.1fpx;'
            '%s"%s%s>' % (src, iw, ih, left, top, iw, ih, extra,
                          (' id="%s"' % gid) if gid else "",
                          (" " + attrs) if attrs else ""))


def head_photo_box(cx, chin_y, head_w, over=1.16):
    """The rect head_photo() will occupy, so a caller can gate it."""
    hw = head_w * over
    iw = hw / DARIO_HEADW
    ih = iw * (DARIO_H / DARIO_W)
    return (cx - DARIO_MIDX * iw, chin_y - DARIO_CHIN * ih, iw, ih)


def beer(x, y, w, h, seed, glass="#F6E7A8", foam=WHITE):
    """A drawn pint, tilted, with a handle.  He is enjoying this."""
    b = []
    body = [(x, y + h * 0.18), (x + w, y + h * 0.18),
            (x + w * 0.88, y + h), (x + w * 0.12, y + h)]
    b.append(stroke(wob([(x + w * 0.94, y + h * 0.34), (x + w * 1.30, y + h * 0.42),
                         (x + w * 1.30, y + h * 0.74), (x + w * 0.94, y + h * 0.66)],
                        seed + 5, 1.0, 10), 4.4, colour=INK, fill="none"))
    b.append(stroke(wob(body, seed, 1.2, 12), 5.0, colour=INK, fill=glass))
    foam_p = [(x - w * 0.06, y + h * 0.18), (x + w * 1.06, y + h * 0.18),
              (x + w * 0.98, y - h * 0.06), (x + w * 0.60, y + h * 0.06),
              (x + w * 0.30, y - h * 0.08), (x + w * 0.02, y + h * 0.04)]
    b.append(stroke(wob(foam_p, seed + 1, 1.6, 11), 4.6, colour=INK, fill=foam))
    for k in range(3):                                    # bubbles
        b.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity=".55"/>'
                 % (x + w * (0.26 + k * 0.22), y + h * (0.54 + (k % 2) * 0.18),
                    w * 0.055, WHITE))
    return "".join(b)


def note(cx, cy, w, seed, rot=0.0, fill="#BFE3C9", gid=None):
    """One bank note.  Flat green rectangle, wobbly edge, a ring in the middle
    so it reads as money and not as a sticky note."""
    h = w * 0.52
    b = [stroke(wob([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
                     (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)],
                    seed, 1.1, 10), 3.6, colour=INK, fill=fill)]
    b.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
             'stroke-width="3"/>' % (cx, cy, h * 0.26, INK))
    b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
             'stroke-width="3"/>' % (cx - w * 0.40, cy, cx - h * 0.30, cy, INK))
    b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
             'stroke-width="3"/>' % (cx + h * 0.30, cy, cx + w * 0.40, cy, INK))
    g = "".join(b)
    if rot:
        g = '<g transform="rotate(%.1f %.1f %.1f)">%s</g>' % (rot, cx, cy, g)
    return '<g id="%s">%s</g>' % (gid, g) if gid else g


def cannon(x, y, w, h, seed, body="#4B3D35", band=TERRA):
    """The money cannon.  A drawn barrel on a two-wheel carriage, muzzle
    pointing right, so the notes have somewhere to come FROM."""
    b = []
    barrel = [(x, y + h * 0.22), (x + w * 0.78, y + h * 0.06),
              (x + w * 0.78, y + h * 0.74), (x, y + h * 0.60)]
    b.append(stroke(wob(barrel, seed, 1.4, 13), 5.4, colour=INK, fill=body))
    muzzle = [(x + w * 0.74, y - h * 0.02), (x + w, y - h * 0.06),
              (x + w, y + h * 0.86), (x + w * 0.74, y + h * 0.82)]
    b.append(stroke(wob(muzzle, seed + 1, 1.2, 11), 5.0, colour=INK, fill=band))
    b.append(stroke(wob([(x + w * 0.10, y + h * 0.26), (x + w * 0.22, y + h * 0.24),
                         (x + w * 0.22, y + h * 0.62), (x + w * 0.10, y + h * 0.60)],
                        seed + 2, 0.9, 9), 3.6, colour=INK, fill=TAN))
    for k, cx in enumerate((x + w * 0.24, x + w * 0.60)):   # wheels
        b.append(stroke(wob([(cx - h * 0.30, y + h * 0.72), (cx + h * 0.30, y + h * 0.72),
                             (cx + h * 0.30, y + h * 1.30), (cx - h * 0.30, y + h * 1.30)],
                            seed + 7 + k, 1.0, 14), 4.4, colour=INK, fill=TAN))
        b.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>'
                 % (cx, y + h * 1.01, h * 0.07, INK))
    return "".join(b)


def stack(x, base, w, n, seed, fill="#BFE3C9", step=None):
    """A stack of notes sitting on a surface, drawn bottom-up."""
    step = step or w * 0.115
    b = []
    for k in range(n):
        y = base - (k + 1) * step
        jitter = ((seed + k * 37) % 11 - 5) * 0.8
        b.append(stroke(wob([(x + jitter, y), (x + w + jitter, y),
                             (x + w + jitter, y + step * 0.94), (x + jitter, y + step * 0.94)],
                            seed + k, 0.9, 9), 3.2, colour=INK, fill=fill))
    return "".join(b)


# ══ vid79 — THE CLAUDE MARK ══════════════════════════════════════════════
# The official starburst, traced out of claude.com's OWN app icon
# (claude.com/images/claude_app_icon.png) rather than redrawn: the outline is a
# contour of that file, supersampled 8x and simplified, normalised into a
# 0..1000 box.  The fill is the mark's own measured colour, #D97757 — the
# median of the saturated pixels in that same file, which is Anthropic's
# published Claude terracotta.
CLAUDE_MARK_PATH = "M 482.99 807.51 L 475.22 807.51 L 466.72 799.37 L 461.72 797.34 L 460.98 793.64 L 458.39 791.05 L 458.03 787.72 L 455.44 785.13 L 455.07 781.80 L 452.48 779.22 L 452.48 767.75 L 455.44 764.42 L 455.44 752.96 L 458.39 749.63 L 458.39 738.17 L 461.35 734.84 L 461.35 726.33 L 464.31 723.00 L 464.31 711.54 L 467.27 708.21 L 467.27 696.75 L 470.23 693.42 L 470.23 681.95 L 473.19 678.62 L 473.19 667.16 L 476.15 663.83 L 476.15 652.37 L 479.11 649.04 L 479.11 634.62 L 482.06 631.29 L 482.06 616.86 L 485.02 613.54 L 485.02 596.15 L 487.98 592.83 L 487.98 584.32 L 490.94 580.99 L 490.94 575.07 L 490.01 574.15 L 488.54 574.52 L 482.43 580.62 L 481.69 584.69 L 473.56 592.46 L 472.82 596.52 L 467.64 601.33 L 466.90 605.40 L 458.76 613.17 L 458.03 617.23 L 449.89 625.00 L 449.15 629.07 L 441.01 636.83 L 440.27 640.90 L 432.14 648.67 L 431.40 652.74 L 426.22 657.54 L 425.48 661.61 L 417.34 669.38 L 416.61 673.45 L 408.47 681.21 L 407.73 685.28 L 399.59 693.05 L 398.85 697.12 L 390.72 704.88 L 389.98 708.95 L 349.30 749.26 L 348.93 752.22 L 347.63 753.88 L 345.04 754.25 L 335.06 760.17 L 324.33 760.17 L 313.42 749.63 L 313.42 738.17 L 316.38 734.84 L 316.75 728.55 L 321.93 723.74 L 322.67 719.67 L 330.81 711.91 L 331.55 707.84 L 339.68 700.07 L 340.42 696.01 L 351.52 685.28 L 352.26 681.21 L 363.35 670.49 L 364.09 666.42 L 375.18 655.70 L 375.92 651.63 L 384.06 643.86 L 384.80 639.79 L 395.89 629.07 L 396.63 625.00 L 404.77 617.23 L 405.51 613.17 L 413.65 605.40 L 414.39 601.33 L 422.52 593.57 L 423.26 589.50 L 437.32 575.81 L 438.05 571.75 L 452.11 558.06 L 452.48 554.36 L 455.07 552.14 L 455.07 551.04 L 453.40 550.48 L 451.55 553.07 L 447.86 553.44 L 443.05 558.25 L 438.24 559.73 L 434.17 564.16 L 429.36 565.64 L 425.30 570.08 L 414.57 574.52 L 410.50 578.96 L 405.70 580.44 L 401.63 584.87 L 396.82 586.35 L 392.75 590.79 L 387.94 592.27 L 383.88 596.71 L 379.07 598.19 L 375.00 602.63 L 370.19 604.11 L 366.12 608.54 L 361.32 610.02 L 357.25 614.46 L 346.52 618.90 L 342.46 623.34 L 337.65 624.82 L 333.58 629.25 L 328.77 630.73 L 324.70 635.17 L 319.90 636.65 L 315.83 641.09 L 311.02 642.57 L 306.95 647.00 L 302.14 648.48 L 298.08 652.92 L 293.27 654.40 L 289.20 658.84 L 285.87 659.58 L 281.80 662.54 L 271.08 662.54 L 267.01 665.50 L 250.37 665.50 L 239.46 654.96 L 239.46 634.62 L 251.85 621.86 L 256.66 620.38 L 260.72 615.94 L 265.53 614.46 L 269.60 610.02 L 274.41 608.54 L 281.43 601.15 L 286.24 599.67 L 290.31 595.23 L 295.12 593.75 L 299.19 589.31 L 302.51 588.57 L 305.10 586.35 L 315.83 581.92 L 319.90 577.48 L 323.22 576.74 L 326.55 574.15 L 329.14 573.78 L 331.73 571.56 L 342.46 567.12 L 346.52 562.68 L 349.85 561.95 L 353.18 559.36 L 355.77 558.99 L 359.10 556.40 L 361.69 556.03 L 364.28 553.81 L 369.08 552.33 L 373.15 547.89 L 376.48 547.15 L 379.07 544.93 L 389.79 540.50 L 393.86 536.06 L 397.19 535.32 L 399.78 533.10 L 403.11 532.36 L 413.09 526.44 L 416.42 525.70 L 420.49 521.26 L 423.82 520.53 L 425.85 518.86 L 425.85 513.31 L 423.82 511.65 L 407.17 511.65 L 403.11 508.69 L 312.50 508.69 L 308.43 505.73 L 244.45 505.73 L 240.38 502.77 L 191.20 502.77 L 182.69 494.64 L 177.88 493.16 L 174.74 490.01 L 174.00 485.95 L 171.41 483.36 L 171.41 468.93 L 179.36 461.35 L 210.80 461.35 L 214.87 464.31 L 252.22 464.31 L 256.29 467.27 L 296.60 467.27 L 300.67 470.23 L 343.93 470.23 L 348.00 473.19 L 373.52 473.19 L 377.59 476.15 L 403.11 476.15 L 407.17 479.11 L 423.82 479.11 L 425.85 477.44 L 425.48 474.11 L 419.38 468.01 L 414.57 466.53 L 410.50 462.09 L 405.70 460.61 L 401.63 456.18 L 396.82 454.70 L 389.79 447.30 L 384.99 445.82 L 380.92 441.38 L 376.11 439.90 L 372.04 435.47 L 367.23 433.99 L 363.17 429.55 L 358.36 428.07 L 354.29 423.63 L 349.48 422.15 L 345.41 417.71 L 340.61 416.24 L 336.54 411.80 L 331.73 410.32 L 327.66 405.88 L 322.86 404.40 L 318.79 399.96 L 313.98 398.48 L 309.91 394.05 L 299.19 389.61 L 295.12 385.17 L 290.31 383.69 L 283.28 376.29 L 278.48 374.82 L 271.45 367.42 L 266.64 365.94 L 262.57 361.50 L 257.77 360.02 L 250.74 352.63 L 245.93 351.15 L 241.86 346.71 L 237.06 345.23 L 230.95 339.13 L 230.21 335.06 L 225.04 330.25 L 224.30 326.18 L 222.08 324.33 L 221.34 320.27 L 218.75 317.68 L 218.75 306.21 L 221.34 303.62 L 221.71 300.30 L 224.67 296.97 L 225.04 293.64 L 234.10 284.58 L 235.58 283.84 L 264.05 283.84 L 266.64 286.06 L 271.45 287.54 L 278.48 294.93 L 283.28 296.41 L 290.31 303.81 L 295.12 305.29 L 305.10 315.64 L 309.91 317.12 L 316.94 324.52 L 321.75 326.00 L 331.73 336.35 L 336.54 337.83 L 343.57 345.23 L 348.37 346.71 L 355.40 354.11 L 360.21 355.58 L 367.23 362.98 L 372.04 364.46 L 376.11 368.90 L 380.92 370.38 L 387.94 377.77 L 392.75 379.25 L 399.78 386.65 L 404.59 388.13 L 411.61 395.53 L 416.05 396.63 L 421.23 401.81 L 422.89 400.89 L 422.89 394.97 L 420.30 392.38 L 419.93 389.05 L 416.97 385.72 L 416.61 382.40 L 411.43 377.59 L 411.06 374.26 L 408.47 371.67 L 408.10 368.34 L 405.51 365.75 L 404.77 361.69 L 402.18 359.10 L 401.81 355.77 L 396.63 350.96 L 396.26 347.63 L 393.68 345.04 L 393.31 341.72 L 390.72 339.13 L 390.35 335.80 L 387.76 333.21 L 387.39 329.88 L 384.80 327.29 L 384.06 323.22 L 378.88 318.42 L 378.51 315.09 L 375.92 312.50 L 375.18 308.43 L 370.01 303.62 L 369.27 299.56 L 367.05 297.71 L 366.68 294.38 L 363.72 291.05 L 363.35 287.72 L 358.17 282.91 L 357.43 278.85 L 355.21 277.00 L 354.84 273.67 L 351.89 270.34 L 351.52 267.01 L 346.34 262.20 L 345.97 258.88 L 343.01 255.55 L 342.64 252.22 L 337.46 247.41 L 336.72 243.34 L 331.55 238.54 L 330.81 234.47 L 328.59 232.62 L 327.85 228.55 L 325.26 225.96 L 325.26 220.41 L 322.30 217.09 L 322.30 208.58 L 319.34 205.25 L 319.34 190.83 L 322.30 187.50 L 322.30 181.95 L 327.85 176.41 L 328.22 173.45 L 329.51 171.78 L 333.58 170.67 L 337.65 166.24 L 343.93 165.50 L 348.00 162.54 L 367.60 162.54 L 371.67 165.50 L 376.48 165.50 L 379.07 167.71 L 383.88 169.19 L 389.98 175.30 L 390.35 178.62 L 393.31 181.95 L 393.68 185.28 L 396.26 187.87 L 396.26 193.42 L 398.85 196.01 L 399.22 199.33 L 402.18 202.66 L 402.55 205.99 L 404.77 207.84 L 405.14 211.17 L 408.10 214.50 L 408.10 220.04 L 410.69 222.63 L 411.06 225.96 L 413.65 228.55 L 414.02 231.88 L 416.61 234.47 L 417.34 238.54 L 419.93 241.12 L 419.93 246.67 L 422.52 249.26 L 422.89 252.59 L 425.48 255.18 L 425.85 258.51 L 428.44 261.09 L 428.81 264.42 L 431.77 267.75 L 431.77 273.30 L 437.32 278.85 L 437.68 282.17 L 440.27 284.76 L 440.64 288.09 L 443.23 290.68 L 443.60 294.01 L 446.19 296.60 L 446.56 299.93 L 449.15 302.51 L 449.52 305.84 L 452.11 308.43 L 452.48 311.76 L 455.44 315.09 L 455.81 318.42 L 458.03 320.27 L 458.76 324.33 L 460.98 326.18 L 461.35 329.51 L 463.94 332.10 L 464.31 335.43 L 466.90 338.02 L 467.27 341.35 L 469.86 343.93 L 470.23 347.26 L 473.19 350.59 L 473.56 353.92 L 475.78 355.77 L 476.52 359.84 L 479.11 362.43 L 479.11 365.01 L 481.69 367.60 L 482.06 370.93 L 485.02 374.26 L 485.39 377.59 L 487.98 380.18 L 487.98 385.72 L 490.94 389.05 L 490.94 394.60 L 493.90 397.93 L 493.90 403.48 L 497.41 407.36 L 498.89 407.73 L 499.82 406.80 L 499.82 386.09 L 502.77 382.77 L 502.77 350.59 L 505.73 347.26 L 505.73 323.96 L 508.69 320.64 L 508.69 297.34 L 511.65 294.01 L 511.65 261.83 L 514.61 258.51 L 514.61 229.29 L 517.57 225.96 L 517.57 208.58 L 520.53 205.25 L 520.53 199.70 L 523.11 197.12 L 523.48 193.79 L 526.07 191.20 L 526.44 187.87 L 529.03 185.28 L 529.77 181.21 L 532.91 178.07 L 537.72 176.59 L 543.27 171.41 L 551.04 171.41 L 553.62 173.63 L 564.35 178.07 L 573.41 187.13 L 574.15 191.20 L 576.74 193.79 L 576.74 211.17 L 573.78 214.50 L 573.78 231.88 L 570.82 235.21 L 570.82 249.63 L 567.86 252.96 L 567.86 267.38 L 564.90 270.71 L 564.90 282.17 L 561.95 285.50 L 561.95 296.97 L 558.99 300.30 L 558.99 314.72 L 556.03 318.05 L 556.03 329.51 L 553.07 332.84 L 553.07 344.30 L 550.11 347.63 L 550.11 359.10 L 547.15 362.43 L 547.15 376.85 L 544.19 380.18 L 544.19 388.31 L 545.49 389.98 L 548.82 389.98 L 555.66 383.51 L 556.40 379.44 L 564.53 371.67 L 565.27 367.60 L 573.41 359.84 L 574.15 355.77 L 585.24 345.04 L 585.98 340.98 L 594.12 333.21 L 594.86 329.14 L 605.95 318.42 L 606.69 314.35 L 617.79 303.62 L 618.53 299.56 L 635.54 282.91 L 636.28 278.85 L 677.88 237.24 L 681.21 236.50 L 685.28 233.54 L 687.87 233.17 L 691.20 230.58 L 701.92 230.58 L 705.99 233.54 L 712.28 234.28 L 727.26 249.26 L 727.63 255.55 L 730.58 258.88 L 730.58 279.22 L 728.00 281.80 L 727.63 285.13 L 724.67 288.46 L 724.67 294.01 L 719.12 299.56 L 718.38 303.62 L 707.29 314.35 L 706.55 318.42 L 698.41 326.18 L 697.67 330.25 L 686.58 340.98 L 685.84 345.04 L 677.70 352.81 L 676.96 356.88 L 668.82 364.64 L 668.08 368.71 L 662.91 373.52 L 662.54 376.85 L 659.58 380.18 L 659.21 383.51 L 654.03 388.31 L 653.29 392.38 L 648.11 397.19 L 647.37 401.26 L 642.20 406.07 L 641.46 410.13 L 633.32 417.90 L 632.58 421.97 L 627.40 426.78 L 626.66 430.84 L 621.49 435.65 L 620.75 439.72 L 615.57 444.53 L 615.94 446.01 L 630.92 446.56 L 634.99 443.60 L 645.71 443.60 L 649.78 440.64 L 660.50 440.64 L 664.57 437.68 L 672.34 437.68 L 676.41 434.73 L 687.13 434.73 L 691.20 431.77 L 701.92 431.77 L 705.99 428.81 L 716.72 428.81 L 720.78 425.85 L 734.47 425.85 L 738.54 422.89 L 752.22 422.89 L 756.29 419.93 L 769.97 419.93 L 774.04 416.97 L 784.76 416.97 L 788.09 414.39 L 791.79 416.97 L 799.56 416.97 L 801.04 417.71 L 805.10 422.15 L 809.91 423.63 L 813.42 427.51 L 813.42 447.86 L 810.84 450.44 L 810.10 454.51 L 806.95 457.66 L 803.62 458.39 L 799.56 461.35 L 791.79 461.35 L 787.72 464.31 L 779.96 464.31 L 775.89 467.27 L 768.12 467.27 L 764.05 470.23 L 756.29 470.23 L 752.22 473.19 L 741.49 473.19 L 737.43 476.15 L 726.70 476.15 L 722.63 479.11 L 711.91 479.11 L 707.84 482.06 L 697.12 482.06 L 693.05 485.02 L 685.28 485.02 L 681.21 487.98 L 670.49 487.98 L 666.42 490.94 L 658.65 490.94 L 654.59 493.90 L 646.82 493.90 L 642.75 496.86 L 634.99 496.86 L 630.92 499.82 L 620.19 499.82 L 616.12 502.77 L 608.73 502.77 L 604.66 505.36 L 600.22 505.36 L 597.82 507.03 L 598.37 508.32 L 600.59 509.06 L 619.08 508.69 L 623.15 511.65 L 704.88 511.65 L 708.95 514.61 L 743.34 514.61 L 747.41 517.57 L 781.80 517.57 L 787.35 522.74 L 792.16 524.22 L 796.23 528.66 L 801.04 530.14 L 805.10 534.58 L 809.91 536.06 L 816.01 542.16 L 816.38 560.28 L 813.79 562.87 L 813.05 566.94 L 809.91 570.08 L 806.58 570.82 L 803.99 573.04 L 799.93 574.15 L 798.08 576.00 L 794.75 576.74 L 790.68 579.70 L 774.04 579.70 L 769.97 576.74 L 762.20 576.74 L 758.14 573.78 L 747.41 573.78 L 743.34 570.82 L 735.58 570.82 L 731.51 567.86 L 723.74 567.86 L 719.67 564.90 L 711.91 564.90 L 707.84 561.95 L 700.07 561.95 L 696.01 558.99 L 685.28 558.99 L 681.21 556.03 L 673.45 556.03 L 669.38 553.07 L 661.61 553.07 L 657.54 550.11 L 649.78 550.11 L 645.71 547.15 L 637.94 547.15 L 633.88 544.19 L 626.11 544.19 L 622.04 541.24 L 614.28 541.24 L 610.21 538.28 L 596.15 538.28 L 594.86 539.57 L 603.92 549.37 L 608.73 550.85 L 648.30 590.79 L 653.11 592.27 L 677.88 617.42 L 682.69 618.90 L 722.26 658.84 L 727.07 660.32 L 745.01 678.25 L 745.75 682.32 L 748.34 684.91 L 748.34 696.38 L 745.75 698.96 L 745.01 703.03 L 740.38 706.92 L 732.62 706.92 L 730.03 704.70 L 725.22 703.22 L 718.20 695.82 L 713.39 694.34 L 706.36 686.95 L 701.55 685.47 L 694.53 678.07 L 689.72 676.59 L 682.69 669.19 L 677.88 667.71 L 673.82 663.28 L 669.01 661.80 L 644.23 636.65 L 639.42 635.17 L 626.48 621.86 L 621.67 620.38 L 605.77 604.11 L 601.33 603.00 L 596.89 598.19 L 595.41 597.82 L 594.49 598.74 L 594.86 605.40 L 603.00 613.17 L 603.74 617.23 L 608.91 622.04 L 609.65 626.11 L 614.83 630.92 L 615.57 634.99 L 620.75 639.79 L 621.49 643.86 L 626.66 648.67 L 627.40 652.74 L 632.58 657.54 L 633.32 661.61 L 638.50 666.42 L 639.24 670.49 L 644.42 675.30 L 645.16 679.36 L 650.33 684.17 L 651.07 688.24 L 656.25 693.05 L 656.99 697.12 L 662.17 701.92 L 662.91 705.99 L 668.08 710.80 L 668.45 720.04 L 671.41 723.37 L 671.41 746.67 L 668.82 749.26 L 668.45 752.22 L 667.16 753.88 L 661.61 754.25 L 657.54 757.21 L 652.74 757.21 L 649.41 759.80 L 645.71 757.21 L 634.99 757.21 L 621.49 744.45 L 620.75 740.38 L 615.57 735.58 L 614.83 731.51 L 609.65 726.70 L 608.91 722.63 L 603.74 717.83 L 603.00 713.76 L 597.82 708.95 L 597.08 704.88 L 591.90 700.07 L 591.16 696.01 L 585.98 691.20 L 585.24 687.13 L 580.07 682.32 L 579.33 678.25 L 576.74 675.67 L 576.37 672.34 L 571.19 667.53 L 570.45 663.46 L 565.27 658.65 L 564.53 654.59 L 559.36 649.78 L 558.62 645.71 L 553.44 640.90 L 553.07 637.57 L 550.11 634.25 L 550.11 631.66 L 547.15 628.33 L 546.78 625.00 L 541.61 620.19 L 540.87 616.12 L 538.28 613.54 L 537.91 610.21 L 532.73 605.40 L 532.36 602.07 L 529.77 599.48 L 529.03 595.78 L 527.37 594.49 L 525.52 594.49 L 523.48 596.52 L 523.48 610.58 L 520.53 613.91 L 520.53 643.12 L 517.57 646.45 L 517.57 675.67 L 514.61 678.99 L 514.61 708.21 L 511.65 711.54 L 511.65 737.80 L 508.69 741.12 L 508.69 770.34 L 505.73 773.67 L 505.73 791.05 L 496.30 800.85 L 492.97 801.59 L 482.99 807.51 Z"
CLAUDE_TERRA = "#D97757"


def claude_mark(cx, cy, size, fill=CLAUDE_TERRA, gid=None, opacity=None, rot=0.0):
    """The Claude starburst, centred on (cx, cy) and `size` across."""
    s = size / 1000.0
    x0, y0 = cx - size / 2.0, cy - size / 2.0
    op = ' opacity="%.3f"' % opacity if opacity is not None else ""
    body = ('<g transform="translate(%.2f %.2f) scale(%.5f)%s">'
            '<path d="%s" fill="%s"/></g>'
            % (x0, y0, s, (" rotate(%.1f 500 500)" % rot) if rot else "",
               CLAUDE_MARK_PATH, fill))
    if gid:
        return '<g id="%s"%s>%s</g>' % (gid, op, body)
    return '<g%s>%s</g>' % (op, body) if op else body


def plate_frame(x, y, w, h, r=14, sw=6, drop=13):
    """The furniture a video plate sits in: a hard offset shadow BELOW the
    media and a stroke-only frame ABOVE it.  A filled shadow rect emitted over
    the plate is a blackout — vid75 shipped five of those."""
    return (art_shadow(x, y, w, h, r, drop), stroke_box(w, h, r=r, sw=sw))


def art_shadow(x, y, w, h, r, drop):
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s"/>'
            % (x + drop, y + drop, w, h, r, INK))
