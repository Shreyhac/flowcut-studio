#!/bin/bash
# Start the JP experiment emulator (vw_ig_01) the right way (20 Nov 2026):
# Tokyo time zone forced (the emulator copies the Mac's India zone otherwise), no snapshot, clipboard sharing OFF
# (defaults com.android.Emulator set.clipboardSharing=0), crash dialog OFF (set.crashReportPreference=2).
# Proxy: v2rayNG HTTP -> residential proxy JP sticky session (see ~/.flowcut/proxies proxy-jp), always-on + lockdown, local DNS ON.
export ADB_MDNS=0
defaults write com.android.Emulator set.clipboardSharing -int 0; defaults write com.android.Emulator set.crashReportPreference -int 2
rm -f ~/.android/avd/vw_ig_01.avd/*.lock
nohup ~/Library/Android/sdk/emulator/emulator -avd vw_ig_01 -no-boot-anim -no-snapshot-save -timezone Asia/Tokyo >/tmp/vw_ig_01.log 2>&1 &
