#!/usr/bin/env python3
"""Between renders (holds the fleet's local lock briefly), clear HyperFrames' extract cache, which otherwise grows
~1 GB per render, and log free disk. Exits when no fleet run is alive."""
import fcntl, os, shutil, subprocess, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(tempfile.gettempdir(), f"hyperframes-extract-cache-{os.getuid()}")   # any Mac (was this Mac's TMPDIR)
def size(p):
    try: return int(subprocess.run(["du", "-sk", p], capture_output=True, text=True).stdout.split()[0]) * 1024
    except Exception: return 0
while subprocess.run(["pgrep", "-f", "gta2.py|gta1.py|hwy.py"], capture_output=True).returncode == 0:
    if os.path.exists(CACHE) and size(CACHE) > 500 * 1024 ** 2:
        with open(os.path.join(HERE, ".local.lock"), "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            shutil.rmtree(CACHE, ignore_errors=True)
            fcntl.flock(f, fcntl.LOCK_UN)
        free = shutil.disk_usage(os.path.expanduser("~")).free / 1024 ** 3
        open(os.path.join(HERE, "fleet.log"), "a").write(f"{time.strftime('%H:%M:%S')} [janitor] cleared extract cache, free {free:.1f} GB\n")
    time.sleep(180)
