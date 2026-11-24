#!/usr/bin/env python3
"""Dense sweep of the hook window — every 0.1s from 0.00 to 2.48.

The beat sheet samples word onsets; the hook is where a half-entered element,
a bare frame under a wipe, or a plate that has not decoded yet actually lives,
and those sit BETWEEN onsets.  Same clip-runtime simulation as
preview_frames.py: this page is loaded without the HyperFrames runtime, so the
windows are honoured by hand or every timed element paints at once.
"""
import asyncio, os, re, sys
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "hook")
A, B, STEP = 0.0, 2.48, 0.10


async def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    marks = [round(A + i * STEP, 3) for i in range(int((B - A) / STEP) + 1)]
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--force-color-profile=srgb",
                                          "--autoplay-policy=no-user-gesture-required"])
        ctx = await b.new_context(viewport={"width": 1080, "height": 1920},
                                  device_scale_factor=1)
        pg = await ctx.new_page()
        await pg.goto("file://" + os.path.join(HERE, "index.html"),
                      wait_until="domcontentloaded", timeout=90000)
        await pg.add_style_tag(content="html,body{width:1080px;height:1920px}"
                                       "#stage{transform:none!important}")
        await pg.wait_for_function("() => !!(window.__timelines && window.__timelines.root)",
                                   timeout=30000)
        await pg.wait_for_function("() => document.fonts.status === 'loaded'", timeout=30000)
        await pg.wait_for_function(
            "() => [...document.querySelectorAll('video')].every(v => v.readyState >= 2)",
            timeout=90000)
        for t in marks:
            await pg.evaluate("""async (t) => {
                const tl = window.__timelines.root; tl.pause(); tl.seek(t, false);
                document.querySelectorAll("[data-start][data-duration]").forEach(el => {
                    if (el.tagName === "AUDIO") return;
                    const s = parseFloat(el.dataset.start), d = parseFloat(el.dataset.duration);
                    el.style.setProperty("display",
                        (t >= s - 0.0005 && t < s + d) ? "" : "none", "important");
                });
                await Promise.all([...document.querySelectorAll('video')].map(v =>
                  new Promise(res => {
                    const s = parseFloat(v.dataset.start || 0), d = parseFloat(v.dataset.duration || 0);
                    const ms = parseFloat(v.dataset.mediaStart || 0);
                    if (t < s - 0.001 || t > s + d + 0.001) return res();
                    const want = Math.min(Math.max(ms + (t - s), 0), v.duration - 0.02);
                    if (Math.abs(v.currentTime - want) < 0.008) return res();
                    let done = false; const cb = () => { if (!done) { done = true; res(); } };
                    if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(cb);
                    v.currentTime = want; setTimeout(cb, 1500);
                  })));
            }""", t)
            await pg.wait_for_timeout(80)
            await pg.screenshot(path=os.path.join(OUT, "h%05.2f.png" % t),
                                clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
        await b.close()
    print("wrote %d hook frames" % len(marks))


asyncio.run(main())
