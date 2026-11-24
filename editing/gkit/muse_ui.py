#!/usr/bin/env python3
r"""Meta's Muse app, rebuilt as live DOM (owner, 2026-10-06: "rebuild as live DOM").

Measured from Meta's own launch clips (vid95/web/Muse_Shopping.mp4 at 1920x1672, Muse_Japan.mp4,
the sizzle), and muse.ai's own CSS tokens and fonts (Optimistic AI / Optimistic Text, captured
2026-10-06 from muse.ai/_next/static):
  * ground off-white #FAFAFA (--off-white #fcfcfc; the clip samples 249-250)
  * header: round menu button left, the Muse mascot in a white disc with a "Muse" name pill
    under it (+ a grey status line while working: "is working", "Adding to cart"), an
    "Invite" pill right
  * assistant bubbles grey #EDEDED (sampled 236-237), radius ~30 at a 745 px phone,
    left-aligned; the user's bubbles pale blue #D6E9FF, right-aligned
  * tool chips: a rounded grey card, a round app glyph, "Browser" over a grey status line
  * the composer: "+  Message  (mic)" pill; a five-icon tab bar under it on the phone
Everything is scaled from that 745 px phone: `u` = px per reference px.

Every element carries an id so the reel can type, pop, fill and scroll it.
"""
from .core import esc, ab

BG, BUB, ME, INK, GREY, GREY2, LINE, BLUE = "#FAFAFA", "#EDEDED", "#D6E9FF", "#111112", "#6B6E73", "#9A9DA2", "#E3E4E6", "#0064D4"
FAM = "optimisticAI"
TXT = "optimisticText"

FONT_CSS = r"""
@font-face{font-family:optimisticAI;src:url('assets/fonts/muse-optimistic-ai-vf.woff2') format('woff2');font-weight:400 600;font-display:block}
@font-face{font-family:optimisticText;src:url('assets/fonts/muse-optimistic-text-rg.woff2') format('woff2');font-weight:400;font-display:block}
@font-face{font-family:optimisticText;src:url('assets/fonts/muse-optimistic-text-bd.woff2') format('woff2');font-weight:700;font-display:block}
@font-face{font-family:optimisticMono;src:url('assets/fonts/muse-optimistic-mono-vf.woff2') format('woff2');font-weight:300 800;font-display:block}
.mu{font-family:optimisticAI,optimisticText,Inter,sans-serif;color:#111112}
.mu .bub{position:relative;max-width:82%;border-radius:var(--br);padding:var(--bp);font-size:var(--fs);line-height:1.32;letter-spacing:-.005em}
.mu .bub.m{align-self:flex-start;background:#EDEDED}
.mu .bub.u{align-self:flex-end;background:#D6E9FF}
"""

# lucide-ish strokes for the chrome (drawn, never glyphs)
_I = {
    "menu": '<path d="M5 9h14M5 15h14"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    "chat": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "doc": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "bulb": '<path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7V16h8v-1.3A7 7 0 0 0 12 2z"/>',
    "check": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 3 3 5-6"/>',
    "apps": '<circle cx="7" cy="7" r="3"/><circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/><circle cx="17" cy="17" r="3"/>',
    "send": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "tick": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "bookmark": '<path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "pin": '<path d="M12 22s7-6.1 7-12a7 7 0 0 0-14 0c0 5.9 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
    "play": '<path d="M7 4v16l13-8z"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "share": '<path d="M14.5 21.7a.5.5 0 0 0 .9 0l6.5-19a.5.5 0 0 0-.6-.6l-19 6.5a.5.5 0 0 0 0 .9l7.9 3.2a2 2 0 0 1 1.1 1.1z"/><path d="m21.9 2.1-10.9 11"/>',
    "spark": '<path d="M12 2l2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z"/>',
    "mem": '<path d="M12 3a9 9 0 1 0 9 9"/><path d="M12 7v5l3 2"/><path d="M17 3h4v4"/>',
}


def ic(name, size, col=INK, sw=2.0, fill="none"):
    return ('<svg viewBox="0 0 24 24" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="%.1f" '
            'stroke-linecap="round" stroke-linejoin="round" style="display:block;overflow:visible">%s</svg>'
            % (size, size, fill, col, sw, _I[name]))


IG_GLYPH = ('<svg viewBox="0 0 24 24" width="%d" height="%d" style="display:block"><defs><radialGradient id="igg%s" cx="30%%" cy="107%%" r="150%%">'
            '<stop offset="0" stop-color="#fdf497"/><stop offset=".05" stop-color="#fdf497"/><stop offset=".45" stop-color="#fd5949"/>'
            '<stop offset=".6" stop-color="#d6249f"/><stop offset=".9" stop-color="#285AEB"/></radialGradient></defs>'
            '<rect x="1" y="1" width="22" height="22" rx="6.5" fill="url(#igg%s)"/>'
            '<rect x="6" y="6" width="12" height="12" rx="3.8" fill="none" stroke="#fff" stroke-width="1.9"/>'
            '<circle cx="12" cy="12" r="3" fill="none" stroke="#fff" stroke-width="1.9"/><circle cx="16.3" cy="7.7" r="1" fill="#fff"/></svg>')


def ig_glyph(size, key):
    return IG_GLYPH % (size, size, key, key)


class Screen:
    """One Muse screen at width w.  u = scale vs the 745 px reference phone."""

    def __init__(self, pid, w, h, u=None, mascot="assets/logos/muse-mascot.png"):
        self.pid, self.w, self.h = pid, w, h
        self.u = u or w / 745.0
        self.mascot = mascot

    def px(self, v):
        return int(round(v * self.u))

    # ── chrome ──────────────────────────────────────────────────────────
    def header(self, status=None, invite_hi=False, top=0):
        u, p = self.px, self.pid
        btn = ("position:absolute;top:%dpx;height:%dpx;border-radius:%dpx;background:#fff;"
               "box-shadow:0 %dpx %dpx rgba(0,0,0,.07);display:flex;align-items:center;justify-content:center" % (top + u(132), u(84), u(42), u(2), u(14)))
        h = ab(btn + ";left:%dpx;width:%dpx" % (u(40), u(84)), ic("menu", u(40), INK, 2.2))
        h += ab(btn + ";right:%dpx;padding:0 %dpx;font-family:%s;font-weight:500;font-size:%dpx;color:%s"
                % (u(40), u(30), FAM, u(28), INK), "Invite", p + "Invite")
        cx = self.w // 2
        h += ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:50%%;background:#fff;overflow:hidden;"
                "box-shadow:0 %dpx %dpx rgba(0,0,0,.08)" % (cx - u(46), top + u(112), u(92), u(92), u(2), u(12)),
                '<img src="%s" style="position:absolute;left:0;top:0;width:100%%;height:100%%">' % self.mascot, p + "Mascot")
        h += ab("left:0;top:%dpx;width:%dpx;display:flex;flex-direction:column;align-items:center" % (top + u(208), self.w),
                '<span style="position:relative;background:#fff;border-radius:%dpx;padding:%dpx %dpx;font-family:%s;font-weight:600;'
                'font-size:%dpx;color:%s;box-shadow:0 %dpx %dpx rgba(0,0,0,.06)">Muse</span>' % (u(24), u(6), u(22), FAM, u(27), INK, u(2), u(10))
                + ('<span id="%sStatus" style="position:relative;margin-top:%dpx;font-family:%s;font-size:%dpx;color:%s">%s</span>'
                   % (p, u(4), FAM, u(20), GREY, esc(status)) if status else ""))
        return h

    def header_compact(self, status=None, h=None):
        """muse.ai on the web: mascot + name + status in one row, Invite right (for windows/cards)"""
        u, p = self.px, self.pid
        h = h or u(96)
        m = int(h * 0.66)
        return ab("left:0;top:0;width:%dpx;height:%dpx;border-bottom:%dpx solid %s;background:%s" % (self.w, h, max(1, u(2)), LINE, BG),
                  ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:50%%;overflow:hidden;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.08)"
                     % (u(26), (h - m) // 2, m, m), '<img src="%s" style="position:absolute;left:0;top:0;width:100%%;height:100%%">' % self.mascot, p + "Mascot")
                  + ab("left:%dpx;top:%dpx;font-family:%s;font-weight:600;font-size:%dpx;color:%s" % (u(26) + m + u(16), (h - m) // 2 - u(2), FAM, u(31), INK), "Muse")
                  + ab("left:%dpx;top:%dpx;font-family:%s;font-size:%dpx;color:%s;white-space:nowrap" % (u(26) + m + u(16), (h - m) // 2 + u(36), FAM, u(23), GREY),
                       esc(status or "Personal agent"), p + "Status")
                  + ab("right:%dpx;top:%dpx;height:%dpx;padding:0 %dpx;border-radius:%dpx;background:#fff;border:%dpx solid %s;display:flex;align-items:center;"
                       "font-family:%s;font-weight:500;font-size:%dpx;color:%s" % (u(24), (h - u(58)) // 2, u(58), u(26), u(29), max(1, u(2)), LINE, FAM, u(27), INK),
                       "Invite", p + "Invite"), p + "Head")

    def composer(self, text="", eid=None, bottom=None):
        u, p = self.px, self.pid
        b = u(36) if bottom is None else bottom
        return ab("left:%dpx;bottom:%dpx;width:%dpx;height:%dpx;border-radius:%dpx;background:#fff;border:%dpx solid %s;"
                  "display:flex;align-items:center;gap:%dpx;padding:0 %dpx"
                  % (u(28), b, self.w - 2 * u(28), u(92), u(46), max(1, u(2)), LINE, u(18), u(26)),
                  ic("plus", u(36), GREY, 2.2)
                  + '<span id="%s" style="position:relative;flex:1;font-family:%s;font-size:%dpx;color:%s;white-space:nowrap;overflow:hidden">%s</span>'
                  % (eid or p + "Comp", FAM, u(30), GREY2 if not text else INK, esc(text) if text else "Message")
                  + '<span id="%sSend" style="position:relative;width:%dpx;height:%dpx;border-radius:50%%;display:flex;align-items:center;justify-content:center">%s</span>'
                  % (p, u(56), u(56), ic("mic", u(34), GREY, 2.2)), p + "Composer")

    def typed_composer(self, text, eid):
        """a composer whose text is pre-split into characters for typing in"""
        u, p = self.px, self.pid
        chars = "".join('<i class="tc">%s</i>' % ("&nbsp;" if c == " " else esc(c)) for c in text)
        return ab("left:%dpx;bottom:%dpx;width:%dpx;height:%dpx;border-radius:%dpx;background:#fff;border:%dpx solid %s;"
                  "display:flex;align-items:center;gap:%dpx;padding:0 %dpx"
                  % (u(28), u(36), self.w - 2 * u(28), u(92), u(46), max(1, u(2)), LINE, u(18), u(26)),
                  ic("plus", u(36), GREY, 2.2)
                  + '<span style="position:relative;flex:1;height:%dpx;font-family:%s;font-size:%dpx;white-space:nowrap;overflow:hidden">'
                    '<span id="%sPh" style="position:absolute;left:0;top:0;color:%s">Message</span>'
                    '<span id="%s" style="position:absolute;left:0;top:0;color:%s">%s</span></span>'
                  % (u(40), FAM, u(30), eid, GREY2, eid, INK, chars)
                  + '<span id="%sSendB" style="position:relative;width:%dpx;height:%dpx;border-radius:50%%;background:%s;display:flex;'
                    'align-items:center;justify-content:center">%s</span>' % (eid, u(56), u(56), BLUE, ic("send", u(30), "#fff", 2.6)),
                  eid + "Box")

    # ── chat items ──────────────────────────────────────────────────────
    def bubble(self, eid, text, who="m", extra=""):
        u = self.px
        return ('<div id="%s" class="bub %s" style="--br:%dpx;--bp:%dpx %dpx;--fs:%dpx;%s">%s</div>'
                % (eid, who, u(32), u(22), u(28), u(31), extra, text))

    def chip(self, eid, glyph, title, sub, sub_id=None):
        """the tool chip ("Browser · Adding Glide Pro to cart")"""
        u = self.px
        return ('<div id="%s" style="position:relative;align-self:stretch;margin-right:%dpx;background:#EFEFF0;border-radius:%dpx;'
                'padding:%dpx %dpx;display:flex;align-items:center;gap:%dpx">'
                '<span style="position:relative;width:%dpx;height:%dpx;flex:none">%s</span>'
                '<span style="position:relative;display:flex;flex-direction:column">'
                '<span style="font-family:%s;font-weight:500;font-size:%dpx;color:%s">%s</span>'
                '<span%s style="font-family:%s;font-size:%dpx;color:%s;margin-top:%dpx">%s</span></span></div>'
                % (eid, u(60), u(28), u(18), u(24), u(18), u(48), u(48), glyph, FAM, u(27), INK, esc(title),
                   (' id="%s"' % sub_id) if sub_id else "", FAM, u(23), GREY, u(2), sub))

    def stack(self, items, top, bottom, eid=None, gap=16, anchor="end"):
        """the chat column, bottom-anchored like the real thread"""
        u = self.px
        return ab("left:%dpx;top:%dpx;width:%dpx;bottom:%dpx;display:flex;flex-direction:column;justify-content:flex-%s;gap:%dpx"
                  % (u(28), top, self.w - 2 * u(28), bottom, anchor, u(gap)), "".join(items), eid)

    def screen(self, inner, eid=None, extra=""):
        return ab("left:0;top:0;width:%dpx;height:%dpx;background:%s;overflow:hidden;%s" % (self.w, self.h, BG, extra),
                  '<div class="mu" style="position:absolute;inset:0">%s</div>' % inner, eid or self.pid)


def reel_card(eid, thumb, w, h, handle, line2="", tag=None, tag_col="#E8F8D8", tag_ink="#1F6B2A", radius=22, u=1.0,
              likes=None, dark_label=True):
    """an Instagram reel tile as Muse surfaces it: 9:16 thumbnail, play glyph, creator handle"""
    px = lambda v: int(round(v * u))
    body = ('<img src="%s" style="position:absolute;left:0;top:0;width:100%%;height:100%%;object-fit:cover">' % thumb
            + ab("left:0;bottom:0;width:100%%;height:55%%;background:linear-gradient(to top,rgba(0,0,0,.72),rgba(0,0,0,0))")
            + ab("left:%dpx;top:%dpx;width:%dpx;height:%dpx" % (px(14), px(14), px(30), px(30)), ic("play", px(30), "#fff", 2, "#fff"))
            + ab("left:%dpx;bottom:%dpx;right:%dpx;font-family:%s;color:#fff" % (px(16), px(14), px(12), FAM),
                 '<div style="font-weight:600;font-size:%dpx;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">%s</div>' % (px(26), esc(handle))
                 + ('<div style="font-size:%dpx;opacity:.9;margin-top:%dpx;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">%s</div>'
                    % (px(24), px(2), line2) if line2 else "")))
    if likes:
        body += ab("right:%dpx;top:%dpx;display:flex;align-items:center;gap:%dpx;font-family:%s;font-weight:600;font-size:%dpx;color:#fff"
                   % (px(14), px(14), px(6), FAM, px(25)), ic("heart", px(24), "#fff", 2, "#fff") + likes)
    if tag:
        body += ab("left:%dpx;top:%dpx;background:%s;color:%s;border-radius:%dpx;padding:%dpx %dpx;font-family:%s;font-weight:600;font-size:%dpx;white-space:nowrap"
                   % (px(12), px(54), tag_col, tag_ink, px(14), px(5), px(14), FAM, px(25)), tag, eid + "Tag")
    return ('<div id="%s" style="position:relative;flex:none;width:%dpx;height:%dpx;border-radius:%dpx;overflow:hidden;background:#222">%s</div>'
            % (eid, w, h, px(radius), body))
