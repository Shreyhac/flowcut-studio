#!/usr/bin/env python3
"""Conform one b-roll plate for a card: cut [ss, ss+dur], crop to the card's aspect, scale to at most the card's
2x size (never up), 30 fps, -g 15, no audio, SDR bt709 (an HLG Pexels clip is tonemapped: HDR flips the whole render).
  plate.py <src> <out.mp4> <ss> <dur> <card_w> <card_h> [cx=0.5] [cy=0.5] [zoom=1.0] [crop=x,y,w,h in source px]"""
import json, subprocess, sys
src, out, ss, dur, cw, ch = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
cx = float(sys.argv[7]) if len(sys.argv) > 7 else .5
cy = float(sys.argv[8]) if len(sys.argv) > 8 else .5
zoom = float(sys.argv[9]) if len(sys.argv) > 9 else 1.0
pre = sys.argv[10] if len(sys.argv) > 10 else None
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,color_transfer",
                                "-of", "json", src], capture_output=True, text=True).stdout)["streams"][0]
sw, sh = pr["width"], pr["height"]
vf = []
if pr.get("color_transfer") in ("arib-std-b67", "smpte2084"):
    vf.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
if pre:
    x, y, w, h = [int(v) for v in pre.split(",")]
    vf.append("crop=%d:%d:%d:%d" % (w, h, x, y)); sw, sh = w, h
ar = cw / float(ch)
w = min(sw, sh * ar) / zoom
h = w / ar
x = max(0, min(sw - w, cx * sw - w / 2)); y = max(0, min(sh - h, cy * sh - h / 2))
ow = int(min(w, cw * 2)) // 2 * 2; oh = int(round(ow / ar)) // 2 * 2
vf.append("crop=%d:%d:%d:%d,scale=%d:%d:flags=lanczos,fps=30,setsar=1" % (int(w) // 2 * 2, int(h) // 2 * 2, int(x), int(y), ow, oh))
cmd = ["nice", "-n", "19", "ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "%.3f" % ss, "-i", src, "-t", "%.3f" % dur, "-an", "-vf", ",".join(vf),
       "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-g", "15", "-keyint_min", "15",
       "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True)
print("%s  %dx%d  %.2fs  (src %dx%d)" % (out.split("/")[-1], ow, oh, dur, pr["width"], pr["height"]))
