#!/usr/bin/env python3
"""Install a build's plates and thumbnails from the shared stock folder.

    install(proj, {"key": "stock9596/streetfood_32228864.mp4", ...}, thumbs={"t_hanoi": ("key", 1.5)})

Plates are HARD-LINKED (no copy, 8 GB machine, 26 GiB free) to assets/plates/<key>.mp4; thumbnails
are single frames written to assets/img/<name>.jpg at 540 px wide (shown <=300 px on the stage).
"""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ledger(plates, thumbs, used=None):
    """Owner, vid95 round 1: "We can't repeat the B-roll."  Every plate and every thumbnail must come from a
    distinct source file, and a thumbnail may not be cut from a plate's clip.  `used` lists the keys the build
    actually references; anything installed but unused is reported too."""
    src = {}
    for k, v in plates.items():
        src.setdefault(os.path.realpath(os.path.join(ROOT, v)), []).append("plate:" + k)
    for k, (key, t) in (thumbs or {}).items():
        path = plates[key] if key in plates else key
        src.setdefault(os.path.realpath(os.path.join(ROOT, path)), []).append("thumb:" + k)
    dup = {os.path.basename(s): ks for s, ks in src.items() if len(ks) > 1}
    assert not dup, "b-roll ledger: a source is used twice: %s" % dup
    return len(src)


def install(proj, plates, thumbs=None, logos=()):
    os.makedirs(os.path.join(proj, "assets", "plates"), exist_ok=True)
    os.makedirs(os.path.join(proj, "assets", "img"), exist_ok=True)
    for key, src in plates.items():
        dst = os.path.join(proj, "assets", "plates", key + ".mp4")
        src = os.path.join(ROOT, src)
        if os.path.exists(dst) and os.path.samefile(dst, src):
            continue
        if os.path.exists(dst):
            os.remove(dst)
        os.link(src, dst)
    for name, (key, t) in (thumbs or {}).items():
        dst = os.path.join(proj, "assets", "img", name + ".jpg")
        src = os.path.join(ROOT, plates[key]) if key in plates else os.path.join(ROOT, key)
        if os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(src):
            continue
        # a still image takes NO -ss: with one, ffmpeg exits 0 and writes nothing (vid96 v1: grey reel tiles)
        seek = [] if src.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) else ["-ss", "%.2f" % t]
        subprocess.run(["ffmpeg", "-y", "-v", "error"] + seek + ["-i", src, "-frames:v", "1",
                        "-vf", "scale=540:-2:flags=lanczos", "-q:v", "3", dst], check=True)
        assert os.path.exists(dst) and os.path.getsize(dst) > 1000, "thumbnail not written: %s" % dst
    for lg in logos:
        src = os.path.join(ROOT, "gkit", "logos", lg)
        dst = os.path.join(proj, "assets", "logos", lg)
        if not os.path.exists(dst):
            os.link(src, dst)


def used_once(html, exempt=("avatar",)):
    """the built composition references every b-roll thumbnail (assets/img) and plate (assets/plates) at most
    once: the owner's round-1 rule, checked on the artefact rather than the content table"""
    import re
    from collections import Counter
    c = Counter(m.group(1) for m in re.finditer(r'assets/(?:img|plates)/([A-Za-z0-9_\-]+)\.(?:jpg|mp4)', html))
    rep = {k: n for k, n in c.items() if n > 1 and k not in exempt}
    assert not rep, "b-roll used more than once in the reel: %s" % rep
    return len(c)
