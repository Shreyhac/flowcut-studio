#!/usr/bin/env python3
"""The eight Gamma Sky colourways (owner, 2026-10-17: one per video in Gaurav's 8-video batch).

Same carrier as vid97a/vid98 (radial sky gradient + white grid + the ink card kit); each colourway moves the
gradient and swaps the template's accent constants.  Approved off live hf98 frames (scratchpad boards 4-6).

    from gkit import palettes
    palettes.write_bg("dusk", "hfgb1/assets/img/bg-dusk.png")       # the ground png the PAPER css points at
    html = palettes.apply(html, "dusk")                               # accent swap + extra css, last step of build

apply() swaps ONLY the template's own constants (tmpl_a INK/ORANGE/LIME/PINK/CREAM/CAPRED hexes), so a rebuilt
product UI must not reuse those exact hexes for its own colours.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vid97", "bg"))
from make_bg import ground  # noqa: E402

ORANGE, LIME, PINK, CREAM, CAPRED = "#F05A22", "#89FC2C", "#FBDED7", "#FCF3E5", "#FD4930"


def _g(base, top, topa, bot, bota, grid=.14):
    return dict(base=base, glows=[(top, 540, -300, 1350, topa), (bot, 540, 2250, 1300, bota)], grid="#FFFFFF", grid_a=grid)


PAL = {
    "gsky": dict(bg=dict(base="#CDDAFA", glows=[("#84C1FA", 540, -260, 1500, .95), ("#E8EEFC", 540, 2150, 1250, .9)],
                         grid="#FFFFFF", grid_a=.14), sw={}),
    "noon": dict(bg=dict(base="#9CC6F8", glows=[("#F2F6FE", 540, -150, 1250, 1.0), ("#1862D4", 540, 2350, 1300, .85)],
                         grid="#FFFFFF", grid_a=.12),
                 sw={LIME: "#FFFFFF", CAPRED: "#151515"}),
    "golden": dict(bg=_g("#F3E6DA", "#84C1FA", 1.0, "#FFC9A6", .95),
                   sw={ORANGE: "#FF5000", LIME: "#FFFFFF", CAPRED: "#151515"}),
    "dusk": dict(bg=_g("#E2D2F6", "#9CC4FA", 1.0, "#F7A3E6", .9),
                 sw={ORANGE: "#1862D4", LIME: "#FFFFFF", CAPRED: "#002253", PINK: "#FDE6F8"}),
    "bold": dict(bg=dict(base="#1E6BDE", glows=[("#84C1FA", 540, -350, 1300, .75), ("#0B3F9E", 540, 2300, 1300, .8)],
                         grid="#FFFFFF", grid_a=.08),
                 sw={CAPRED: "#151515"},
                 # headlines sit on the blue: white line 1, lime line 2; the outline star goes white so it reads
                 css='.hl1{color:#fff!important}[id$="_l2"]{color:#B8FF3D!important}'
                     '#dStar path{stroke:#fff!important}'),
    "spring": dict(bg=_g("#E8F5F3", "#84C1FA", 1.0, "#7FE3B8", .9),
                   sw={LIME: "#FFFFFF", CAPRED: "#151515"}),
    "lemon": dict(bg=_g("#FBF7E6", "#9FCDFB", .85, "#FFE94D", 1.0),
                  sw={ORANGE: "#1862D4", CAPRED: "#151515", PINK: "#FFF3C2"}),
    # gb9 (DareAISearch, 2026-10-22): the sky pulled to DareAI's teal; accents to their dark teal
    "lagoon": dict(bg=_g("#E6F5F3", "#84C1FA", .95, "#4FD1C3", .8),
                   sw={ORANGE: "#08695F", LIME: "#FFFFFF", CAPRED: "#151515", PINK: "#DDF5F1"}),
    "lilac": dict(bg=_g("#F1ECFE", "#A48CF5", .85, "#FFD3EA", .75),
                  sw={ORANGE: "#FF5000", LIME: "#FFFFFF", CAPRED: "#2E1A6B", PINK: "#EDE6FF"}),
}

# owner-approved assignment by topic (2026-10-17); gbN = /Users/.../new gsb vids/g_N.mp4
BATCH = {1: "dusk", 2: "spring", 3: "gsky", 4: "golden", 5: "lilac", 6: "noon", 7: "bold", 8: "lemon"}


def write_bg(name, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ground(**PAL[name]["bg"]).save(path, optimize=True)
    return path


def accent(name, hexcol):
    """the colour a template constant becomes in this colourway (for code that needs it before apply())"""
    return PAL[name]["sw"].get(hexcol, hexcol)


def apply(html, name):
    p = PAL[name]
    n0 = len(html)
    for a, z in p["sw"].items():
        html = re.sub(re.escape(a), z, html, flags=re.I)
    if p.get("css"):
        assert "</head>" in html, "no </head> to carry the palette css"
        html = html.replace("</head>", "<style>/* palette %s */%s</style></head>" % (name, p["css"]), 1)
    assert len(html) >= n0
    return html


def apply_file(path, name):
    """build.py's last step, right after T.build() wrote index.html (before sfx / chunks / render)"""
    html = open(path).read()
    if "/* palette " in html or name == "gsky":
        return
    open(path, "w").write(apply(html, name))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for k in PAL:
        print(write_bg(k, os.path.join(out, "bg-%s.png" % k)))
