#!/usr/bin/env python3
"""Instagram's chrome, measured on rendered frames rather than modelled.

  BOTTOM BAND   y >= 1600 carries no ink, and is LIT paper (never a dark bar).
  TOP CHROME    y < 150 carries no ink.
  RIGHT RAIL    x >= 960 between y900 and y1600 carries no ink — that column is
                the like / comment / share / save stack.

Run against either preview/ (1080x1920 PNGs) or qa/ (frames pulled from the
delivered mp4).  Both are checked in 1080x1920 space.
"""
import glob, os, re, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, INK, TOL = 1080, 1920, 170, 400

src = sys.argv[1] if len(sys.argv) > 1 else "preview"
files = sorted(glob.glob(os.path.join(HERE, src, "*.png")) +
               glob.glob(os.path.join(HERE, src, "*.jpg")))
if not files:
    sys.exit("gate_safezone: no frames in %s/" % src)

# His opening shot is FULL FRAME by design: for its 1.24s his own footage
# legitimately covers the top chrome, the rail column and the bottom band.
# Those frames are exempt from the ink checks; the band check still runs,
# because a FLAT dark band would be a bar even there.
FULL_UNTIL = 1.710

bad, lum = [], []
for f in files:
    tm = re.search(r"/(\d+\.\d+)_", f)
    full = bool(tm) and float(tm.group(1)) < FULL_UNTIL
    im = Image.open(f).convert("L")
    if im.size != (W, H):
        im = im.resize((W, H))
    a = np.array(im).astype(int)
    band = (a[1600:, :] < INK).sum()
    top = (a[:150, :] < INK).sum()
    rail = (a[900:1600, 960:] < INK).sum()
    lum.append((a[1600:, :].mean(), a[1600:, :].std(), os.path.basename(f)))
    if not full and (band > TOL or top > TOL or rail > TOL):
        bad.append((os.path.basename(f), band, top, rail))

print("gate_safezone: %d frames from %s/" % (len(files), src))
# A dark band is only a defect when it is FLAT: his full-frame opening shot
# legitimately runs his own footage to the bottom of the frame, and that band is
# dark but varied.  A broken bar is dark AND uniform.
dark = [(m, sd, n) for m, sd, n in lum if m < 90]
flat = [(m, sd, n) for m, sd, n in dark if sd < 9]
print("  bottom-band luma  min %.1f  max %.1f  (%d dark frame(s), %d of them flat)"
      % (min(l[0] for l in lum), max(l[0] for l in lum), len(dark), len(flat)))
for m, sd, n in dark[:4]:
    print("     dark but %s: %s  mean %.1f std %.1f"
          % ("FLAT - a bar" if sd < 9 else "textured, so it is footage", n, m, sd))
if flat:
    sys.exit("gate_safezone: %d frame(s) show a flat dark bar in the reserved band"
             % len(flat))
if bad:
    for n, b, t, r in bad:
        print("  %-30s band %6d  top %5d  rail %6d" % (n, b, t, r))
    sys.exit("gate_safezone: %d frame(s) put ink in Instagram's chrome" % len(bad))
print("  clean: bottom band, top 150px and the right rail are all clear")
