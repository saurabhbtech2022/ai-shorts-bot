# AI Shorts Bot

**श्री रामचरित मानस** (गोस्वामी तुलसीदास) ke kram se **roz 3 YouTube Shorts** — **subah, dopahar, sham** (default **08:00, 13:00, 18:00** IST).

Har run = **1 scene (kram se)**, **1 image**, **15 second** Short. **`data/prompts.txt`** poori **Ramcharitmanas** book se (~**6087** verses → **~2030 din** @ 3 Shorts/day). Banane ke liye:

```bash
python scripts/build_prompts_from_manas.py              # 1 stanza = 1 Short (~2k days)
python scripts/build_prompts_from_manas.py --granularity pair  # ~10.8k Shorts (~3.6k days)
```

JSON source: `data/ramcharitmanas/` (auto-download). Purani chhoti list: `scripts/seed_ramcharitmanas_prompts.py`.

Image priority: **Cloudflare Workers AI** (`@cf/black-forest-labs/flux-1-schnell`) → `data/fallback_images/` → Pillow gradient. **Pollinations band** (default); chahiye to `ENABLE_POLLINATIONS=true`.

Pipeline do tarah chalega:

- **CLI:** `python run_daily.py` (GitHub Actions ke liye best)
- **FastAPI:** manual control / dashboard (`uvicorn app.main:app`)

Dono same function call karte hain: `app.pipeline.run_pipeline()`.

---

## Zero-cost stack

| Step | Tool |
|------|------|
| Image (primary) | [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) Flux Schnell |
| Image (fallback) | Local JPG/PNG in `data/fallback_images/`, then gradient |
| Video | FFmpeg 5s Ken Burns + caption (slideshow sirf jab `SCENES_PER_RUN` > 1) |
| Voice (optional) | Edge neural Hindi (`hi-IN-MadhurNeural`, natural) |
| Upload | YouTube Data API v3 (free quota) |
| Cron | GitHub Actions |

---

## Quick start (local)

```bash
cd ai-shorts-bot
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**System deps:** FFmpeg + Devanagari font.

- **macOS:** `brew install ffmpeg` — font: download [Noto Sans Devanagari](https://fonts.google.com/noto/specimen/Noto+Sans+Devanagari) into `assets/fonts/NotoSansDevanagari-Regular.ttf`
- **Ubuntu/Debian:** `sudo apt install ffmpeg fonts-noto`
- **Windows:** FFmpeg PATH mein; `assets/fonts/` mein Noto ya Nirmala/Mangal use hota hai

```bash
cp .env.example .env
# .env edit karo (CF_ACCOUNT_ID, CF_API_TOKEN, YouTube, API_KEY)
python run_daily.py --dry-run --slot morning
python run_daily.py --dry-run --slot afternoon
python run_daily.py --dry-run --slot evening
```

Dry-run: image + video banega, YouTube upload **nahi** hoga.

---

## Google Cloud / YouTube OAuth (important)

1. [Google Cloud Console](https://console.cloud.google.com/) → naya project.
2. **YouTube Data API v3** enable karo.
3. **OAuth consent screen** → **Publishing status: In production** rakho.  
   Testing mode mein refresh token ~7 din mein expire ho sakta hai; production se long-lived refresh token milta hai (jab tak revoke na ho).
4. **Credentials → OAuth client ID → Desktop app** banao.
5. JSON download karke project root mein `client_secret....json` rakho.

Refresh token lo:

```bash
python scripts/get_refresh_token.py
```

Output ko `.env` aur GitHub Secrets mein daalo:

- `YT_CLIENT_ID`
- `YT_CLIENT_SECRET`
- `YT_REFRESH_TOKEN`

**Kabhi bhi refresh token commit mat karna.**

---

## Cloudflare Workers AI (images)

1. [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers AI** enable.
2. **Account ID** copy karo (Overview sidebar).
3. **API Token** banao with **Workers AI Read** (ya Edit) permission.
4. `.env` mein set karo:

```env
CF_ACCOUNT_ID=...
CF_API_TOKEN=...
```

Offline backup: `data/fallback_images/*.jpg` rakho (Cloudflare fail par use hoga).

**Account ID kaise milegi:** Browser mein [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages** → URL mein `https://dash.cloudflare.com/`**`ACCOUNT_ID`**`/workers/...` ya Overview page ke right side. Helper: `python scripts/get_cf_account_id.py`

Pollinations **default off**. Sirf zarurat ho to:

```env
ENABLE_POLLINATIONS=true
POLLINATIONS_API_KEY=...
```

Har generated image **center-crop 9:16** → **1080×1920** save hoti hai (`output/<date>/image_01.jpg` …).

---

## GitHub Actions secrets

Repo → **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|--------|
| `YT_CLIENT_ID` | OAuth client ID |
| `YT_CLIENT_SECRET` | OAuth client secret |
| `YT_REFRESH_TOKEN` | `get_refresh_token.py` output |
| `CF_ACCOUNT_ID` | Cloudflare account ID |
| `CF_API_TOKEN` | Cloudflare API token (Workers AI) |

Workflow `.github/workflows/daily.yml` **teen cron** chalata hai (08:00 / 13:00 / 18:00 IST) — har baar `python run_daily.py --slot …` aur `data/state.json` commit. Har successful slot ke baad prompt index **+1** (din mein 3 scenes consume).

---

## FastAPI server

```bash
export API_KEY=your-secret
export RUN_SCHEDULER=true   # optional: daily job server par
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger: `http://localhost:8000/docs`

Protected routes ke liye header: `X-API-Key: <API_KEY>`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/status` | Index, next scene, history |
| GET | `/prompts` | Saari scenes |
| POST | `/run?dry_run=&force=` | Background pipeline |
| GET | `/jobs/{id}` | Job status |
| POST | `/preview` | Image + video, no upload |
| GET | `/download/latest` | Latest MP4 |
| POST | `/skip` | Agli scene par jump |
| POST | `/reset` | Index 0 |

---

## Docker

```bash
docker build -t ai-shorts-bot .
docker run -p 8000:8000 --env-file .env ai-shorts-bot
```

---

## Data files

- `data/prompts.txt` — Ramcharitmanas book kram (~6087 scenes); `python scripts/build_prompts_from_manas.py`
- `data/state.json` — index, `daily_slots` (aaj kaunse slot ho chuke), history
- `data/fallback_images/` — optional JPG/PNG jab AI providers fail hon
- `data/music/*.mp3` — optional background music (volume ~0.2)

Daily schedule env (defaults):

- `UPLOAD_TIME_MORNING=08:00`, `UPLOAD_TIME_AFTERNOON=13:00`, `UPLOAD_TIME_EVENING=18:00`
- `VIDEO_DURATION=15`, `SCENES_PER_RUN=1`
- CLI: `--slot morning|afternoon|evening` (ya `subah` / `dopahar` / `sham`)

---

## Troubleshooting

**Cloudflare 401/403**  
`CF_API_TOKEN` permissions aur `CF_ACCOUNT_ID` check karo. **4xx par retry nahi hota** — turant next fallback try hota hai.

**Gradient image aa rahi hai**  
Cloudflare fail — `.env` mein `CF_ACCOUNT_ID` + `CF_API_TOKEN` set karo, ya `data/fallback_images/` mein JPG daalo.

**YouTube `quotaExceeded`**  
Default quota kam hai; next day retry ya Google Cloud quota increase request.

**Upload ho gaya par video private / locked**  
Unverified OAuth project par restrictions ho sakti hain. Consent screen **In production** karo, channel verify karo, Studio mein visibility check karo.

**Synthetic / AI disclosure**  
Code `containsSyntheticMedia` set karta hai jahan API allow kare. Agar Studio mein warning aaye to manually **Altered content** disclosure enable karo.

**Hindi text video par nahi dikh raha**  
Font missing — `assets/fonts/NotoSansDevanagari-Regular.ttf` add karo ya Linux par `fonts-noto`.

**GitHub Action fail exit code 1**  
Logs mein `run_daily.py` JSON error dekho; aksar YouTube auth ya FFmpeg.

---

## Monetization tip (Hinglish)

Sirf AI image + same style music se YouTube **repetitive content** flag kar sakta hai. Har Short ke liye **unique Hindi narration script** (thodi alag detail, ek moral line) add karo — `data/prompts.txt` ki caption badlo ya alag narration file rakho. Isse watch time aur monetization chances better rehte hain.

---

## Tests

```bash
pytest tests/ -q
```

---

## License

Apne channel ke liye use karo; epic stories ka respectful depiction maintain karo.
