#!/usr/bin/env python3
"""Switch the LAVA's Proton VPN to a country (12 Nov). vpn.set_country() hangs on the Lava (no curl in its shell), so
this drives Proton directly: Countries -> search -> tap the result -> verify Proton's home shows <country> + Disconnect.
usage: lava_vpn.py <Country name>        importable: switch(name) -> bool"""
import os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "insta")); import vpn
D = "android-device:LAVA_SERIAL"

def _home(dev):
    """Proton's home, with promo sheets closed (14 Nov: a "Try the Proton VPN widget" sheet hid the home, so every
    switch failed from 19:48)."""
    t = vpn._proton_home(dev)
    for _ in range(3):
        c = vpn.coords(t, r'TextView "(?:No thanks|Not now|Maybe later|Skip)"') or vpn.coords(t, r'label="Close sheet"')
        if not c: break
        vpn.pd("tap", dev, *c); time.sleep(2); t = vpn._proton_home(dev)
    return t

def switch(name, dev=D):
    for _ in range(2):
        t = _home(dev)
        if re.search(rf'TextView "{re.escape(name)}"', t) and '"Disconnect"' in t:
            vpn.pd("key", dev, "home"); return True
        c = vpn.coords(t, r'TextView "Countries"')
        if not c: continue
        vpn.pd("tap", dev, *c); time.sleep(3)
        t = vpn.pd("ui", dev, "--no-ocr"); c = vpn.coords(t, r'label="search"')
        if c: vpn.pd("tap", dev, *c); time.sleep(2)
        for _ in range(3):
            t = vpn.pd("ui", dev, "--no-ocr")
            if not re.search(r'EditText "[^"]+" id=searchInput', t): break
            c = vpn.coords(t, r'label="Clear"')
            if not c: break
            vpn.pd("tap", dev, *c); time.sleep(1)
        vpn.pd("type", dev, name); time.sleep(3)
        c = vpn.coords(vpn.pd("ui", dev, "--no-ocr"), rf'TextView "{re.escape(name)}" id=searchResult')
        if not c: vpn.pd("key", dev, "back"); continue
        vpn.pd("tap", dev, *c); time.sleep(3)
        t = vpn.pd("ui", dev, "--no-ocr"); c = vpn.coords(t, r'Button "OK" id=button1')   # first-time VPN permission
        if c: vpn.pd("tap", dev, *c)
        for _ in range(6):
            time.sleep(4)
            t = _home(dev)
            if re.search(rf'TextView "{re.escape(name)}"', t) and '"Disconnect"' in t:
                vpn.pd("key", dev, "home"); return True
    vpn.pd("key", dev, "home"); return False

def patch_tiktok(w):
    """15 Nov: warmup.switch_to() now reconnects the VPN on TikTok's "Services not available in your region" through
    insta/vpn.set_country(), which hangs on the Lava (no curl) -> do the reconnect with switch() instead."""
    def _region_blocked():
        t = w.pd("ui", w.DEV, "--no-ocr")
        if "Services not available" not in t and "not available in your country" not in t: return False
        w.log("  TikTok says 'Services not available in your region' -> reconnecting the US VPN (lava_vpn)")
        switch("United States")
        w.shell("am", "force-stop", "com.zhiliaoapp.musically"); w.sleep(2, 3)
        w.shell("monkey", "-p", "com.zhiliaoapp.musically", "-c", "android.intent.category.LAUNCHER", "1"); w.sleep(8, 10)
        return True
    w._region_blocked = _region_blocked

if __name__ == "__main__":
    ok = switch(sys.argv[1]); print("OK" if ok else "FAILED"); sys.exit(0 if ok else 1)
