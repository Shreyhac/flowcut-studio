#!/bin/bash
# 23 Nov: Doraemon (himitsu) emulator vw_ig_02 - same rules as start_emulator.sh (Tokyo time, no snapshot save, no clipboard share).
# Own proxy provider JP sticky session (different IP from sakura's vw_ig_01). AVD lives in PhoneDock's avd folder.
export ADB_MDNS=0 ANDROID_AVD_HOME="$HOME/Library/Application Support/PhoneDock/avd"
defaults write com.android.Emulator set.clipboardSharing -int 0; defaults write com.android.Emulator set.crashReportPreference -int 2
rm -f "$ANDROID_AVD_HOME"/vw_ig_02.avd/*.lock
nohup ~/Library/Android/sdk/emulator/emulator -avd vw_ig_02 -port 5558 -no-boot-anim -no-snapshot-save -timezone Asia/Tokyo >/tmp/vw_ig_02.log 2>&1 &
# The emulator's own network only lets ports 80/443 out, so v2rayNG (HTTP 127.0.0.1:8898, always-on + lockdown) reaches the
# Mac's dora_fwd_proxy.py (adds proxy provider auth, JP sticky session) through `adb reverse`. UDP can't go through -> no IP leak.
pgrep -f dora_fwd_proxy.py >/dev/null || (cd ~/masonry-tools/lava && nohup python3 dora_fwd_proxy.py > dora_fwd_proxy.log 2>&1 &)
for i in $(seq 1 60); do [ "$(adb -s emulator-5558 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ] && break; sleep 5; done
adb -s emulator-5558 reverse tcp:8898 tcp:8898
