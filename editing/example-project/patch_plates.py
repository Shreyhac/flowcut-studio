import re
p='build_index.py'; s=open(p).read()
def sub(a,b):
    global s
    assert a in s, "MISSING: "+a[:80]
    s=s.replace(a,b,1)

# ── 1. plate geometry + loader + helper, right after the marks block ──────
sub('''# the fifteen, in grid order.  The four the VO names take the first row.''',
'''# ══ B-ROLL PLATES — the real product, moving ═════════════════════════════
# ONE card rect for every tool scene, so four cuts read as one system rather
# than four layouts.  The plate is 660x368 on stage = 1320x736 in the delivered
# frame, which is native size for a cropped 1080p screen recording: no upscale,
# so the product's own type stays as sharp as the source.  It sits LEFT of the
# rocket column (x760..960) and never under it: a drawn object standing on top
# of footage is the "just a layer on the video" note, and this composition puts
# them side by side on the same ground instead.
PLATE_RECT = (72, 392, 660, 368)
FLD_RECT = (72, 240, 560, 76)
CHIP_RECT = (72, 782, 300, 58)
PLATES = json.load(open(os.path.join(HERE, "plates.json"))) \\
    if os.path.exists(os.path.join(HERE, "plates.json")) else {}


def plate(scene, key, tri, r=14, z=23):
    """A real B-roll plate in its furniture, as THREE SIBLINGS.

    Four rules, each paid for on an earlier film:
      · the media is SCHEDULED to its scene — a <video> outside its own window
        renders BLACK, and the plate file must be longer than the scene;
      · a <video> carrying data-start may NOT be nested inside a div that also
        carries data-start: the extractor resolves the video's start from its
        own attribute while visibility comes from the wrapper, so the clip
        shows the wrong source frames and then vanishes mid-slot;
      · the hard offset shadow goes BELOW the media and the frame ABOVE it as a
        stroke only — a filled shadow rect over a plate is a blackout;
      · nothing CSS-transforms a <video>: a scale over media deadlocks capture.
    """
    a, b = SPAN[scene]
    src = PLATES[key]
    assert src["dur"] >= (b - a) - 0.001, \\
        "plate %s is %.2fs but %s runs %.2fs" % (key, src["dur"], scene, b - a)
    x, y, w, h = PLATE_RECT
    d = b - a
    gid = "pl_" + scene
    sh = ('<div class="clip" id="%s_bg" data-start="%.3f" data-duration="%.3f" '
          'data-track-index="%d" style="position:absolute;left:%.1fpx;top:%.1fpx;'
          'width:%.1fpx;height:%.1fpx;background:%s;border-radius:%dpx;z-index:%d">'
          '</div>' % (gid, a, d, tri, x + DROP, y + DROP, w, h, INK, r, z))
    vid = ('<video id="%s_v" class="plate" src="%s" data-start="%.3f" '
           'data-duration="%.3f" data-track-index="%d" muted playsinline '
           'style="position:absolute;left:%.1fpx;top:%.1fpx;width:%.1fpx;'
           'height:%.1fpx;object-fit:cover;border-radius:%dpx;z-index:%d"></video>'
           % (gid, src["path"], a, d, tri + 1, x, y, w, h, r, z + 1))
    fr = ('<div class="clip" id="%s" data-start="%.3f" data-duration="%.3f" '
          'data-track-index="%d" style="position:absolute;left:%.1fpx;top:%.1fpx;'
          'width:%.1fpx;height:%.1fpx;z-index:%d">%s</div>'
          % (gid, a, d, tri + 2, x, y, w, h, z + 2, art.stroke_box(w, h, r=r)))
    return sh + "\\n  " + vid + "\\n  " + fr


# the fifteen, in grid order.  The four the VO names take the first row.''')

# ── 2. the four tool scenes, rebuilt on the real UI ──────────────────────
old = s[s.index("    # ── s03 · POMELLI"):s.index("    # ── s07 · CTA")]
new = '''    # ── the four tool scenes ────────────────────────────────────────────
    # Every one is the same composition: the REAL product running in the
    # plate card on the left, its REAL mark riding a drawn rocket on the pad
    # to the right, one hand-drawn assertion over or beside it.  Nothing is a
    # drawing OF the product any more — the drawn kit is only what has to ACT
    # (the rocket, the marker, the strike, the arrow).
    PX, PY, PW, PH = PLATE_RECT
    FX, FY, FW, FH = FLD_RECT
    CX_, CY_, CW_, CH_ = CHIP_RECT

    def tool_base(scene, seed, chip_text, chip_fill, ring_at=None):
        """pad, exhaust, name chip.  Returns the svg parts list."""
        bb = [pad(860, PADY, seed)]
        bb.append(puffs(860, PADY - 6, seed + 9, "pf%s_" % scene[-1]))
        for k in range(3):
            O["pf%s_%d" % (scene[-1], k)] = "%.1f %.1f" % (860 + (-64, 0, 64)[k], PADY - 40)
        bb.append(chip(CX_, CY_, CW_, CH_, chip_text, seed + 19, fill=chip_fill,
                       tcol=INK, size=24, gid="lab" + scene[-1]))
        O["lab" + scene[-1]] = "%.1f %.1f" % (CX_ + CW_ / 2, CY_ + CH_ / 2)
        return bb

    # ── s03 · POMELLI · a website link becomes a brand's posts ──────────
    b = tool_base("s03", 8301, "", TERRA)
    b.append(field(FX, FY, FW, FH, 8330, gid="urlf"))
    O["urlf"] = "%.1f %.1f" % (FX + FW / 2, FY + FH / 2)
    b.append('<g id="urlarrow" style="opacity:0">%s</g>'
             % art.arrow(FX + FW - 40, FY + FH + 10, PX + PW - 90, PY - 14, 8340, bend=34))
    O["urlarrow"] = "%.1f %.1f" % (FX + FW - 40, FY + FH + 10)
    A["S03"] = art.svg(1080, 950, "".join(b))
    # the marker ring is drawn OVER the plate, so it lives in its own layer
    A["S03RING"] = art.svg(1080, 950, '<g id="postring" style="opacity:0">%s</g>'
                           % art.circle_mark(PX + PW * 0.66, PY + PH * 0.52,
                                             PW * 0.28, PH * 0.36, 8351, w=7.0, turns=2))
    O["postring"] = "%.1f %.1f" % (PX + PW * 0.66, PY + PH * 0.52)
    X["S03"] = (rocket("s03", 860, PADY, 400, 8360, "pomelli-icon", nose=RED, fin=TERRA)
                + '<div class="clip" id="lab3w" data-start="%.3f" data-duration="%.3f" '
                  'data-track-index="410" style="position:absolute;left:0;top:0;z-index:29">'
                  '%s</div>'
                % (SPAN["s03"][0], SPAN["s03"][1] - SPAN["s03"][0],
                   mark_img("pomelli-ink", CX_ + 50, CY_ - 71, 200, gid="lab3m", z=29)))

    # ── s04 · STITCH · a sentence becomes a screen ──────────────────────
    b = tool_base("s04", 8401, "STITCH", PEACH)
    b.append(field(FX, FY, FW, FH, 8430, gid="promptf"))
    O["promptf"] = "%.1f %.1f" % (FX + FW / 2, FY + FH / 2)
    b.append('<g id="pharrow" style="opacity:0">%s</g>'
             % art.arrow(FX + FW - 40, FY + FH + 10, PX + PW - 90, PY - 14, 8440, bend=34))
    O["pharrow"] = "%.1f %.1f" % (FX + FW - 40, FY + FH + 10)
    A["S04"] = art.svg(1080, 950, "".join(b))
    A["S04RING"] = art.svg(1080, 950, '<g id="scrring" style="opacity:0">%s</g>'
                           % art.circle_mark(PX + PW * 0.62, PY + PH * 0.54,
                                             PW * 0.30, PH * 0.36, 8451, w=7.0, turns=2))
    O["scrring"] = "%.1f %.1f" % (PX + PW * 0.62, PY + PH * 0.54)
    X["S04"] = rocket("s04", 860, PADY, 402, 8460, "stitch", nose=TERRA, fin=PEACH)

    # ── s05 · OPAL · a real canvas, and the code that is not there ──────
    b = tool_base("s05", 8501, "OPAL", SAGE)
    b.append(chip(FX, FY - 4, 210, 84, "</>", 8550, fill=WHITE, size=42, gid="codechip"))
    O["codechip"] = "%.1f %.1f" % (FX + 105, FY + 38)
    b.append('<g id="codestrike" style="opacity:0">%s</g>'
             % art.strike(FX - 4, FX + 214, FY + 38, 8560, w=11.0))
    O["codestrike"] = "%.1f %.1f" % (FX - 4, FY + 38)
    b.append(hand(FX + 250, FY + 56, "no code at all", size=56, rot=-4, gid="nohand"))
    O["nohand"] = "%.1f %.1f" % (FX + 250, FY + 36)
    A["S05"] = art.svg(1080, 950, "".join(b))
    X["S05"] = rocket("s05", 860, PADY, 404, 8570, "opal", nose=SAGE, fin=RED)

    # ── s06 · ANTIGRAVITY · the real editor, and the price ──────────────
    b = tool_base("s06", 8601, "ANTIGRAVITY", LAV)
    b.append(hand(FX + 150, FY + 74, "FREE", size=96, rot=-11, gid="freehand", anchor="middle"))
    O["freehand"] = "%.1f %.1f" % (FX + 150, FY + 44)
    b.append('<g id="zerochip">%s</g>'
             % chip(FX + 320, FY - 2, 300, 80, "$0 / MONTH", 8620, fill=WHITE, size=30))
    O["zerochip"] = "%.1f %.1f" % (FX + 470, FY + 38)
    A["S06"] = art.svg(1080, 950, "".join(b))
    A["S06RING"] = art.svg(1080, 950, '<g id="idering" style="opacity:0">%s</g>'
                           % art.circle_mark(PX + PW * 0.34, PY + PH * 0.56,
                                             PW * 0.28, PH * 0.34, 8651, w=7.0, turns=2))
    O["idering"] = "%.1f %.1f" % (PX + PW * 0.34, PY + PH * 0.56)
    X["S06"] = rocket("s06", 860, PADY, 406, 8640, "antigravity", nose=LAV, fin=SAGE)

'''
s = s.replace(old, new, 1)

# ── 3. build(): emit the plates and the over-plate ring layers ───────────
sub('''    parts = dict(
        S00X=X["S00"], S01X=X["S01"], S03X=X["S03"], S04X=X["S04"], S05X=X["S05"],
        S06X=X["S06"], S07X=X["S07"],''',
'''    PLATE_PLAN = [("s03", "pomelli"), ("s04", "stitch"),
                  ("s05", "opal"), ("s06", "antigravity")]
    plates = "\\n  ".join(plate(sc, key, 300 + i * 3)
                         for i, (sc, key) in enumerate(PLATE_PLAN))
    rings = "\\n  ".join(
        artwrap(sc, 430 + i, A[sc.upper() + "RING"], z=27, gid="ring_" + sc)
        for i, sc in enumerate(("s03", "s04", "s06")))

    parts = dict(
        S00X=X["S00"], S01X=X["S01"], S03X=X["S03"], S04X=X["S04"], S05X=X["S05"],
        S06X=X["S06"], S07X=X["S07"], PLATES=plates, RINGS=rings,''')

sub('''  __EYEBROWS__
  __ARTS__''','''  __EYEBROWS__
  __ARTS__

  <!-- ── the real product, moving, one plate per tool scene ── -->
  __PLATES__
  __RINGS__''')

# ── 4. the timeline for the four tool scenes ────────────────────────────
a0 = s.index("/* ══ s03 · POMELLI")
a1 = s.index("/* ══ s07 · CTA.")
s = s[:a0] + '''/* ══ s03 · POMELLI.  The real tool runs; the rocket carries its mark up. ══ */
launch("s03", T.one1, 230, T.s04, "pf3_");
pop("#lab3", T.brands, O.lab3);
tl.fromTo("#lab3m", {scale:0.3, opacity:0, transformOrigin:"50% 50%"},
  {scale:1, opacity:1, duration:0.34, ease:"back.out(2.4)"}, T.brands);
tl.fromTo("#postring", {opacity:0, scale:0.7, svgOrigin:O.postring},
  {opacity:1, scale:1, svgOrigin:O.postring, duration:0.34, ease:"power3.out"}, T.social);
tl.fromTo("#urlf", {y:-30, opacity:0}, {y:0, opacity:1, duration:0.26, ease:"power3.out"},
  T.fromw-0.14);
typeIn("#urlTx", T.fromw, 0.035);
tl.fromTo("#urlarrow", {opacity:0, scale:0.5, svgOrigin:O.urlarrow},
  {opacity:1, scale:1, svgOrigin:O.urlarrow, duration:0.26, ease:"back.out(2)"}, T.website);
flash(T.link, 0.18);

/* ══ s04 · STITCH.  A sentence is typed, the real tool draws the screen. ══ */
launch("s04", T.one2, 230, T.s05, "pf4_");
tl.fromTo("#promptf", {y:-30, opacity:0}, {y:0, opacity:1, duration:0.24, ease:"power3.out"},
  T.turns);
typeIn("#promptTx", T.sentence-0.34, 0.026);
tl.fromTo("#pharrow", {opacity:0, scale:0.5, svgOrigin:O.pharrow},
  {opacity:1, scale:1, svgOrigin:O.pharrow, duration:0.24, ease:"back.out(2)"}, T.into);
pop("#lab4", T.finished, O.lab4);
tl.fromTo("#scrring", {opacity:0, scale:0.7, svgOrigin:O.scrring},
  {opacity:1, scale:1, svgOrigin:O.scrring, duration:0.32, ease:"power3.out"}, T.design);
flash(T.design, 0.20);

/* ══ s05 · OPAL.  The real canvas runs; the code is struck out. ══ */
launch("s05", T.one3, 230, T.s06, "pf5_");
pop("#lab5", T.automations, O.lab5);
tl.fromTo("#codechip", {scale:0.5, opacity:0, svgOrigin:O.codechip},
  {scale:1, opacity:1, svgOrigin:O.codechip, duration:0.26, ease:"back.out(2.2)"}, T.withw);
tl.fromTo("#codestrike", {opacity:0, scaleX:0, svgOrigin:O.codestrike},
  {opacity:1, scaleX:1, svgOrigin:O.codestrike, duration:0.22, ease:"power3.out"}, T.code);
tl.fromTo("#nohand", {scale:0.4, opacity:0, svgOrigin:O.nohand},
  {scale:1, opacity:1, svgOrigin:O.nohand, duration:0.30, ease:"back.out(2.6)"}, T.atall);
flash(T.code, 0.22);

/* ══ s06 · ANTIGRAVITY.  The real editor runs; the price is stamped. ══ */
launch("s06", T.there, 230, T.s07, "pf6_");
tl.fromTo("#freehand", {scale:2.2, opacity:0, rotation:-30, svgOrigin:O.freehand},
  {scale:1, opacity:1, rotation:0, svgOrigin:O.freehand, duration:0.30, ease:"power4.out"},
  T.free);
tl.from("#zerochip", {y:-22, duration:0.28, ease:"power3.out"}, T.s06+0.01);
tl.fromTo("#idering", {opacity:0, scale:0.7, svgOrigin:O.idering},
  {opacity:1, scale:1, svgOrigin:O.idering, duration:0.32, ease:"power3.out"}, T.code2);
pop("#lab6", T.editor, O.lab6);
flash(T.free, 0.24);

''' + s[a1:]

# ── 5. the typed fields move with the field rect ────────────────────────
sub('data-track-index="120" style="left:130px;top:280px">__URLTYPE__</div>',
    'data-track-index="120" style="left:102px;top:258px">__URLTYPE__</div>')
sub('data-track-index="121" style="left:130px;top:280px">__PROMPTTYPE__</div>',
    'data-track-index="121" style="left:102px;top:258px">__PROMPTTYPE__</div>')
open(p,'w').write(s); print("patched build_index.py")
