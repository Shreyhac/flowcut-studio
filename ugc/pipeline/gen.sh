#!/bin/bash
# v1c recipe, paid generation for one video (owner GO 24 Nov 23:07 IST "generate now", ~1,670 extra approved, existing balance only).
# usage: gen.sh <key> frame   -> <key>/start.png (reference-style talking frame, ~2 cr)
#        gen.sh <key> faces   -> <key>/gen/face1-3.mp4 (HeyGen Avatar 6 Turbo on start.png + the 3 speech slices, ~72 cr)
#        gen.sh <key> react1  -> <key>/react1.mp4 (15 s 360p pixverse-v6 reaction from start.png, 45 cr)
#        gen.sh <key> chain   -> <key>/react2-4.mp4, each from the previous take's last frame (15+15+10 s, 120 cr)
# Stops (exit 3) on any failed submit, so a drained balance never retries; never buys credits.
k=$1; st=$2; cd $(dirname $0)
J() { python3 -c "import json,sys;print(json.load(open('looks.json'))['$k']['$1'])"; }
TOP=$(J top); HAIR=$(J hair); ROOM=$(J room); TS=$(J top_s); RS=$(J room_s); FACE=$(J face)
export MHOME=$HOME/.flowcut/masonry-home
M=../fleet/msub.sh
mkdir -p $k/gen; cd $k; [ -s face.jpg ] || cp "$FACE" face.jpg
ok() { [ -s "$1" ] || { echo "GENFAIL $k $1"; exit 3; }; }
case $k in yui_*) HAIRID="same long straight black hair with soft bangs";; *) HAIRID="same hair colour and fringe";; esac
NEGC="cleavage, low neckline, deep neckline, plunging neckline, v-neck, off-shoulder, bare shoulders, strapless, tank top, crop top"
if [ $st = frame ]; then
  [ -s start.png ] || $M start.png image "Genuine unedited frame from an iPhone video recorded with the phone PROPPED UP and static at face height, slightly below her face (slight low angle), nobody holding it: the same young Japanese woman as the reference photo (exactly the same face, same eyes, same nose, same lips, $HAIRID), $HAIR. Close head-and-shoulders framing: her face fills about half the frame width, eyes a little above the middle of the vertical frame, looking straight into the lens. She wears $TOP with a normal modest neckline. Plain indoor room behind her: $ROOM. In one hand, held up near her chin, a purple highlighter pen with its cap on. Neutral relaxed expression, lips gently closed, eyebrows slightly raised as if about to explain something. No arm reaching toward the camera, no selfie arm, no phone visible. Real skin texture, visible sensor noise and mild compression, no beauty filter, no retouching." -m gpt-image-2.5-sunburst -a 9:16 --ref face.jpg --negative-prompt "selfie, arm reaching to camera, holding phone, phone visible, outstretched arm, smiling with teeth, talking, open mouth, $NEGC, tattoo, beach, outdoors, cafe, text, watermark, extra fingers, deformed hands, different person, beauty filter, cartoon, logo"
  ok start.png; sips -Z 700 start.png -s format jpeg --out start_prev.jpg >/dev/null 2>&1
fi
if [ $st = faces ]; then
  PR="Animated and expressive young woman talking to a propped-up phone camera: she gestures with the purple highlighter while she speaks, points it at the camera, small waves, taps her chin with it, natural head movement and eyebrow raises. Camera completely static, no zoom."
  cd gen; for i in 1 2 3; do ok speech$i.mp3; [ -s face$i.mp4 ] || $M face$i.mp4 video "$PR" -m heygen-avatar-6-turbo -i ../start.png --speech speech$i.mp3; ok face$i.mp4; done
fi
NEG="talking, speaking, smiling with teeth, laughing, camera movement, zoom, handheld shake, selfie arm, phone visible, different person, different outfit, cuts, text, watermark, extra fingers, deformed hands, tattoo, $NEGC"
if [ $st = react1 ]; then
  [ -s react1.mp4 ] || $M react1.mp4 video "iPhone video recorded with the phone propped up and completely static, no camera movement. The young woman silently watches a video on a screen just below the camera and reacts, skeptical and unimpressed, never smiling: she chews the capped end of the purple highlighter in her mouth, takes it out, points it at the screen, rubs the side of her nose with it, puts it back between her teeth; she pulls big skeptical faces: a grimace, a deep frown, squinting, a one-eye squint, a raised eyebrow, a doubtful head tilt, glancing between the screen and the camera. She never talks. Same woman, same $TS, same $RS and daylight throughout. Realistic, one continuous take, no cuts, no zoom." -m pixverse-v6 -i start.png --duration 15 --no-audio --set '{"resolution":"360p"}' --negative-prompt "smiling, $NEG"
  ok react1.mp4
fi
if [ $st = chain ]; then
  A=("" "She keeps chewing the capped end of the purple highlighter, then takes it out and points it at the screen with a deep skeptical frown, then a one-eye squint." "She rubs the side of her nose with the purple highlighter, grimaces, squints at the screen in disbelief, then puts the highlighter back between her teeth." "She taps the purple highlighter against her lips, raises one eyebrow, makes a doubtful grimace, glances at the camera unimpressed, chews the highlighter again.")
  D=(0 15 15 15 10)
  for n in 2 3 4; do
    p=$((n-1)); ok react$p.mp4; [ -s react$n.mp4 ] && continue
    ffmpeg -v error -y -sseof -0.05 -i react$p.mp4 -frames:v 1 -vf "scale=720:1280:flags=lanczos" react${p}_last.png
    $M react$n.mp4 video "iPhone video recorded with the phone propped up and completely static, no camera movement. The young woman silently watches a video on a screen just below the camera and reacts, skeptical and unimpressed, never smiling, never talking. ${A[$((n-1))]} Big expressive skeptical faces. Same woman, same $TS, same $RS and daylight throughout. Realistic, one continuous take, no cuts, no zoom." -m pixverse-v6 -i react${p}_last.png --duration ${D[$n]} --no-audio --set '{"resolution":"360p"}' --negative-prompt "smiling, $NEG"
    ok react$n.mp4
  done
fi
echo "GENOK $k $st"
