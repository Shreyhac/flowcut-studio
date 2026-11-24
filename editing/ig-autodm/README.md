# ig-autodm — keyword → auto-DM for your own Instagram

Someone comments **`SEND`** (or any keyword you pick) on your reel → they get a
DM with your link/content, automatically. This is the same mechanism ManyChat
uses (Instagram "private replies"), running locally on your machine. No monthly fee.

**Meta's rules baked in:** one DM per comment, only within 7 days of the comment.
DMs to people who don't follow you land in their *Message Requests* folder — that's
why `public_ack` (a public "check your DMs 📩" reply) is available as an option.

---

## One-time setup (~20 min)

### 1. Make the account a Professional account
Instagram app → **Settings → Account type and tools → Switch to professional account**
→ choose **Creator** or **Business**. (A personal account cannot use the API at all.)
You do **not** need a Facebook Page — we use the newer *Instagram Login* path.

### 2. Allow connected tools to message
Instagram app → **Settings → Messages and story replies → Message controls →
Connected tools → Allow access to messages: ON.**

### 3. Create a Meta app
Go to <https://developers.facebook.com/apps> → **Create app** → use case
**"Other" → Business** → name it anything (e.g. "my-autodm").
In the app dashboard → **Add product → Instagram → set up** (the box that says
"Instagram API with Instagram Login" / "API setup with Instagram login").

### 4. Add yourself + get a token
In that Instagram product panel:
- Under **roles / Instagram testers**, add your own IG account and **accept** the
  invite from the Instagram app (Settings → Apps and websites → Tester invites).
- Request these permissions/scopes: `instagram_business_basic`,
  `instagram_business_manage_comments`, `instagram_business_manage_messages`.
- Use the **"Generate access token"** button → log in with your IG account →
  copy the token. This is a short-lived token; the panel also lets you generate a
  **long-lived** one (valid ~60 days). Grab the long-lived token.

### 5. Get your IG user id
With that token, run any of these (or just paste in a browser):
```
curl "https://graph.instagram.com/v23.0/me?fields=id,username,account_type&access_token=YOUR_TOKEN"
```
The `id` field is your `ig_user_id`.

### 6. Fill in config
```
cd ig-autodm
cp config.example.json config.json
```
Edit `config.json`:
- `access_token` → your long-lived token
- `ig_user_id`   → the id from step 5
- `keywords`     → words that trigger the DM, e.g. `["send", "link"]` (case-insensitive)
- `reply_message`→ the DM they receive (put your link here)

`config.json` and `state.json` are git-ignored so your token never gets committed.

---

## Run it

```
python3 autodm.py whoami            # confirm the token works
python3 autodm.py list-comments     # see recent comments; keyword hits are flagged
python3 autodm.py run --dry-run     # match keywords, print who WOULD be DM'd, send nothing
python3 autodm.py run               # for real: send the DMs
```

Only Python 3 standard library is used — nothing to `pip install`.

### Keep it running automatically

**Option A — leave it looping in a terminal:**
```
python3 autodm.py run --loop --interval 300     # checks every 5 minutes
```

**Option B — cron (macOS), every 5 minutes:**
```
crontab -e
```
add:
```
*/5 * * * * cd "~/flowcut-studio/editing/ig-autodm" && /usr/bin/python3 autodm.py run >> autodm.log 2>&1
```

### Keep the token alive
Long-lived tokens expire after ~60 days. Refresh anytime (do it monthly):
```
python3 autodm.py refresh-token
```
Or add a monthly cron line calling `refresh-token`.

---

## How it avoids double-DMing
Every comment it replies to is recorded in `state.json`, so re-runs never DM the
same comment twice. Set `"once_per_user": true` to DM each **person** at most once
even if they comment the keyword on several posts.

## Notes / limits
- Works on posts, reels, ads, and live (during the broadcast). Not on old IGTV.
- Meta enforces the 7-day and one-per-comment rules server-side; comments older
  than 7 days are skipped automatically.
- Don't set the keyword to something extremely common, and keep `send_delay_seconds`
  ≥ 2 — aggressive blasting is how accounts get flagged.
