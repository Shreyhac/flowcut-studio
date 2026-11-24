# Reel Safe Zones — 1080×1920 (Instagram Reels, 2026)

Researched 2026-07-10 (Kreatli / Outfy / TryMyPost / CampaignSwift 2026 guides) merged with this
repo's own hard-learned rules (vid2 full re-edit, vid5 y76 chip violation). **These are hard
gates, audited on EVERY render, not once per project.**

## The zones (absolute px on the 1080×1920 canvas)

| Zone | Pixels | What lives there |
|---|---|---|
| TOP | y 0–150 | status bar, "Reels" wordmark, camera icon. NO text above y150. |
| BOTTOM | y 1600–1920 | username, caption (3 lines), audio row, nav bar. NO faces/captions/UI below y1600. |
| RIGHT RAIL | x 960–1080, y 900–1600 | like / comment / share / save stack. No text may cross x960 in this y-band. |
| LEFT | x 0–60 | crop/curvature buffer. No critical TEXT starts left of x60 (imagery may bleed). |

## Placement guidance
- **Hook/title text: y200–600** — safe across notches and Dynamic Island devices.
- **Central safe area ≈ 1080×1420 centered** (y250–1670 minus the bottom band) — keep all
  load-bearing content here.
- **Feed preview crops to 4:5** (≈ y285–1635): a frame-0 cover should still make sense inside
  that crop; in-scene text may exceed it knowingly.
- Talking-head chin at/above y1600. Captions: face scenes y1268, seam captions ≥y812, chart
  captions y1442 — all end above y1600 and stay left of x960.

## vid9/hf8 as-built reference (post-audit values)
- Eyebrow chip y152. Hook type y206. Band headers y130. Tier cards y204–804.
- Mode cards y200–760. Recap rows y224–872. Rollout tiles y646–916.
- Meter `<½` stamps end x930; % counters end x950; turn pill x130–950.

Sources: kreatli.com/guides/instagram-reels-safe-zone · outfy.com/blog/instagram-safe-zone ·
trymypost.com/blog/instagram-reels-safe-zones-text-placement-2026 ·
campaignswift.com/blog/instagram-safe-zone-sizes
