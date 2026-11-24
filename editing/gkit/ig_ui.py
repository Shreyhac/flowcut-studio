#!/usr/bin/env python3
"""Instagram's profile page, rebuilt as live DOM (light theme), for a creator's real public account.
Numbers and text come from the caller (read from the public profile); nothing private is shown."""
from .core import ab, esc

FONT = "font-family:'Helvetica Neue',Helvetica,Arial,sans-serif"
VERIFIED = ('<svg viewBox="0 0 40 40" width="%d" height="%d" style="display:inline-block;vertical-align:-3px"><path fill="#0095F6" '
            'd="M19.998 3.094 14.638 0l-2.972 5.15H5.432v6.354L0 14.64 3.094 20 0 25.359l5.432 3.137v5.905h5.975L14.638 40l5.36-3.094L25.358 40l3.232-5.6h6.162v-6.01L40 25.359 36.905 20 40 14.641l-5.248-3.03v-6.46h-6.419L25.358 0l-5.36 3.094Z"/>'
            '<path fill="#fff" d="m17.2 28.3-6.4-6.4 2.3-2.3 4.1 4.1 9.6-9.6 2.3 2.3z"/></svg>')


def profile(eid, w, handle, name, posts, followers, following, bio, avatar, thumbs, u=1.0, grid_rows=2, ids=True):
    """header + bio + a 3-up reel grid; `thumbs` = [(img_src, badge_html_or_None)]"""
    px = lambda v: int(round(v * u))
    av = px(150)
    head = (ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:50%%;padding:%dpx;background:conic-gradient(#feda75,#fa7e1e,#d62976,#962fbf,#4f5bd5,#feda75)"
               % (px(28), px(24), av, av, px(5)),
               '<div style="position:relative;width:100%%;height:100%%;border-radius:50%%;border:%dpx solid #fff;overflow:hidden">'
               '<img src="%s" style="position:absolute;left:0;top:0;width:100%%;height:100%%;object-fit:cover"></div>' % (px(4), avatar), eid + "Av")
            + ab("left:%dpx;top:%dpx;%s;font-weight:700;font-size:%dpx;color:#000;white-space:nowrap" % (px(210), px(30), FONT, px(36)),
                 esc(handle) + " " + VERIFIED % (px(28), px(28)), eid + "Hd"))
    stats = ""
    for k, (n, lab) in enumerate(((posts, "posts"), (followers, "followers"), (following, "following"))):
        stats += ab("left:%dpx;top:%dpx;%s;color:#000;white-space:nowrap" % (px(210 + k * 170), px(86), FONT),
                    '<span style="font-weight:700;font-size:%dpx">%s</span><br><span style="font-size:%dpx;color:#444">%s</span>' % (px(32), n, px(25), lab),
                    "%sSt%d" % (eid, k) if ids else None)
    biob = ab("left:%dpx;top:%dpx;width:%dpx;%s;color:#111;font-size:%dpx;line-height:1.35" % (px(28), px(196), w - px(56), FONT, px(26)),
              '<div style="font-weight:700">%s</div>%s' % (esc(name), "".join("<div>%s</div>" % esc(b) for b in bio)), eid + "Bio")
    gy = px(196) + px(26) * 1.35 * (len(bio) + 1) + px(26)
    tabs = ab("left:0;top:%dpx;width:%dpx;height:%dpx;border-top:1px solid #DBDBDB" % (gy, w, px(4)))
    cw = (w - 4) // 3
    ch = int(cw * 16 / 9 * 0.75)
    cells = ""
    for k, (src, badge) in enumerate(thumbs[:3 * grid_rows]):
        cells += ('<div id="%sG%d" style="position:relative;width:%dpx;height:%dpx;overflow:hidden;background:#EEE">'
                  '<img src="%s" style="position:absolute;left:0;top:0;width:100%%;height:100%%;object-fit:cover">%s</div>'
                  % (eid, k, cw, ch, src, badge or ""))
    grid = ab("left:0;top:%dpx;width:%dpx;display:flex;flex-wrap:wrap;gap:2px" % (gy + px(10), w), cells, eid + "Grid")
    return head + stats + biob + tabs + grid, gy + px(10) + (ch + 2) * grid_rows


def badge(text, bg="rgba(0,0,0,.66)", col="#fff", size=24, pos="left:10px;bottom:10px"):
    return ('<div style="position:absolute;%s;background:%s;color:%s;border-radius:10px;padding:4px 10px;%s;font-weight:700;'
            'font-size:%dpx;white-space:nowrap">%s</div>' % (pos, bg, col, FONT, size, text))
