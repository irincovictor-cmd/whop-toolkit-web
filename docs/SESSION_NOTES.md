# Session notes (pinned handoff)

**Last updated:** 2026-08-24  
**Purpose:** Everything learned while bringing local web testing online and debugging YouTube quality. Read this + `REVIEW_AND_ROADMAP.md` before changing download/clip code.

Related:
- `docs/REVIEW_AND_ROADMAP.md` — bugs, priorities, product requirements
- `docs/legacy_cli_docs/cli_source/modules/downloader.py` — original CLI stream-crop
- Figma: https://www.figma.com/design/NNmXpsosmbC3fPIZICfZOs

---

## Documentation rule (standing)

**Every code or behavior change must be documented in this file in the same session as the push.**

Applies to Grok, Claude, and anyone else touching the repo.

| Change type | What to write |
|-------------|---------------|
| Bug fix | New **T#** test-log entry: where, symptom, cause, fix, verify, files |
| Behavior change (yt-dlp, formats, clients, timeouts) | Update **Current backend strategy** + test log if needed |
| New wiring (API route, UI↔backend) | Update **Frontend ↔ backend wiring** |
| Ops / run commands | Update **Local testing** or recovery checklist |
| Scope / priority shift | Update **Current focus** |

Also:
- Bump **Last updated** date
- Add a row to **Quick recovery checklist** when the symptom is user-visible
- Mention the fix under **Fixed in session** when relevant
- Do **not** ship code-only commits for behavioral changes without a docs update

Handoff: if you only pushed code, the next agent should treat missing docs as incomplete work.

---

## What “done” looks like for product

- **Pass-through toolkit:** server fetches/processes briefly; user downloads to their device. **Not** a permanent media host.
- **Multi-platform:** YouTube, TikTok, Instagram, X, Vimeo; Facebook planned. Watermark-free = **best-effort** via yt-dlp.
- **Export controls (product):** aspect (original / 9:16 / 16:9), fit (letterbox / cover zoom-fill), quality cap, optional max MB. Portrait+Cover must not silent side-slice.

---

## Local testing (Windows — Victor’s machine)

| Item | Value |
|------|--------|
| Repo | `C:\Users\Victorjames\Documents\Codex\2026-08-23\are-you-codex\whop-toolkit-web` (also Desktop clone) |
| Clip output folder | `C:\Users\Victorjames\Desktop\whop clips` |
| Env | `LOCAL_OUTPUT_DIR` in `backend/.env` (see `.env.example`) |
| Auth skip | `DEV_SKIP_AUTH=true` in `frontend/.env.local` |
| Backend | **Must** `cd backend` then `uvicorn app.main:app --reload --port 8000` |
| Frontend | `cd frontend` → `npm run dev` → http://localhost:3000 |

There is **no** `docker compose up` yet. Two processes (or a local `start-dev.bat`).

**Common footgun:** running `uvicorn app.main:app` from the **repo root** → `ModuleNotFoundError: No module named 'app'`. Always run from `backend/`.

Successful clips/downloads are **also copied** into `LOCAL_OUTPUT_DIR` via `app/core/local_output.py`, and still streamed to the browser.

---

## Frontend ↔ backend wiring

### Connected

| Feature | Path |
|---------|------|
| Metadata | UI → `/api/metadata` → `GET /metadata` |
| Full download | UI → `/api/download` → `POST /download` |
| Clip extract | UI → `/api/clips` → `POST /clips/extract` |
| Transcript | UI → `/api/transcript` → `POST /transcript` |
| Local transcript | UI → `/api/transcript/local` → `POST /transcript/local` |
| Gemini | UI → `/api/ai/analyze` (Next.js only; not FastAPI) |
| Auth | Whop OAuth / `DEV_SKIP_AUTH` |

### UI only / not applied by backend yet

- Aspect, fit mode, quality picker, max MB (sent in JSON; **ignored** until export P2)
- Sidebar Projects / History / Settings (placeholders)

### Backend only / no UI

- `POST /convert` — exists; no Next proxy or UI

### Fixed in session (code)

- **B1** transcript.py IndentationError (import crash)
- Dark UI matching Figma (sidebar, extract panel, login)
- Facebook hosts in `detect_platform`
- Convert path uses uuid filename (B4 direction)
- YouTube client/format cascade (see below)
- **T11** Silent full-video downloads — audio probe + cascade (2026-08-24)

---

## YouTube quality crisis (root cause — not “FastAPI broke UA”)

### Evidence from local CMD (same PC as the web backend)

1. `player_client=default,android` + DASH `401+251` → **403 mid-download** (SABR).
2. `player_client=android,web` + progressive (format **18**) → **100% success** (~126MB).
3. Incomplete URL `https://youtu.be` alone → homepage “recommended” playlist (operator error).
4. Some client sets report **DRM protected** when only DRM/SABR formats remain visible; other clients still get progressive.

### What is *not* the primary cause (when testing localhost)

- FastAPI async “changing headers” vs CLI (both shell out to yt-dlp on a home IP).
- Missing FFmpeg on PATH (failure was CDN 403 before a good merge).

### CLI vs web pipeline difference

| | Legacy CLI | Web backend |
|--|------------|-------------|
| Clip method | Resolve CDN URLs → ffmpeg `-ss` before `-i` | `yt-dlp --download-sections` |
| Clients | `default`, `android` | **`android`, `web`** + cascade |
| 9:16 | Letterbox filter in ffmpeg | UI only until P2 |

### Current backend strategy (`ytdlp_client` + download/clips)

1. **Try HQ:** `bestvideo[height<=1080]+bestaudio/...` (prefer mp4 mux when possible).
2. **On 403 / SABR / forbidden-like stderr:** clear partials, **retry progressive-safe** formats.
3. **On exit 0 but no audio stream** (ffprobe): clear partials, **retry next format** — see **T11**.
4. Optional `YTDLP_COOKIES=/path/to/cookies.txt` for tougher sessions.
5. Keep yt-dlp updated: `pip install -U --pre "yt-dlp[default]"`.
6. Optional: Node.js/LTS for yt-dlp EJS / n-challenge solver (more formats).
7. Default cascade timeout **600s** (long full videos).

**Quality ceiling:** 1080p is **best-effort**. When YouTube blocks DASH, users get lower progressive quality rather than a hard fail. Do not market guaranteed 4K.

**Audio:** Full downloads must ship with an audio track. Clips via `--download-sections` often remux and kept audio even when full HQ path did not — do not assume clip success means full download is fine.

### PO tokens / proxies

- PO tokens: real for some web/mweb GVS flows; brittle; cascade first.
- Proxies: matter on **cloud** deploy IPs; not the local SABR issue.

---

## Test log / errors seen (Aug 2026 local session)

Chronological diary of failures and what fixed them. Use this when the same symptoms come back.

### T1 — Backend will not start (IndentationError)

**Where:** `uvicorn app.main:app --reload --port 8000`  
**Symptom:** Process starts reloader, then crashes on import.

```text
File "...\backend\app\routes\transcript.py", line 98
    if info.get("video_id") and ("youtube.com" in req.url or "youtu.be" in req.url):
                                                                                    ^
IndentationError: unindent does not match any outer indentation level
```

**Cause:** Mis-indented `if` under `get_transcript` (roadmap **B1**).  
**Fix:** Align `if` with function body (4 spaces). Shipped on `main`.  
**Verify:** Uvicorn stays up with `Application startup complete` / no traceback.

---

### T2 — Web UI clip extract: 403 + ffmpeg exit

**Where:** Dashboard → Download clip (via Next → FastAPI → yt-dlp).  
**Symptom (UI / API detail, abbreviated):**

```text
yt-dlp failed: ... googlevideo.com/...&c=ANDROID_VR&...
Error opening input files: Server returned 403 Forbidden (access denied)
ERROR: ffmpeg exited with code 3436169992
```

**Cause:** YouTube CDN refused the stream URL for that player client / format (SABR / client experiment). Not a missing `LOCAL_OUTPUT_DIR`.  
**Fix direction:** Change `player_client` away from VR defaults; prefer `android,web`; cascade formats (see T5–T7).

---

### T3 — CMD: “DRM protected” (misleading dead end for some clients)

**Command pattern:**

```cmd
yt-dlp --extractor-args "youtube:player_client=mweb,tv,web" -f "bv*+ba/b" -o "...\test.%(ext)s" "https://youtu.be/rKaiTQyaijI"
```

**Symptom:**

```text
WARNING: ... n challenge solving failed: ... JavaScript runtime ... EJS
WARNING: ... mweb client https formats require a GVS PO Token ...
WARNING: ... Some tv client https formats have been skipped as they are DRM protected
ERROR: [youtube] rKaiTQyaijI: This video is DRM protected
```

**Cause:** With that client set, yt-dlp only saw DRM/unavailable formats. Same video later downloaded with other clients (not true “impossible forever”).  
**Fix direction:** Try `android,web`; install Node for EJS; do not treat one client’s DRM error as final for all clients.

---

### T4 — CMD: truncated URL (operator error)

**Command mistake:** URL ended at `https://youtu.be` with **no video id**.

**Symptom:**

```text
[generic] Extracting URL: https://youtu.be
[redirect] Following redirect to https://www.youtube.com/?feature=youtu.be
[youtube:tab] Playlist recommended: Downloading 0 items
[download] Finished downloading playlist: recommended
```

**Cause:** Incomplete paste.  
**Fix:** Always use full URL, e.g. `https://youtu.be/rKaiTQyaijI` or `https://www.youtube.com/watch?v=rKaiTQyaijI`.

---

### T5 — CMD: high DASH 403 mid-download

**Command:**

```cmd
yt-dlp --extractor-args "youtube:player_client=default,android" -f "bv*+ba/b" -o "%USERPROFILE%\Desktop\whop clips\test2.%(ext)s" "https://youtu.be/rKaiTQyaijI"
```

**Symptom:**

```text
[youtube] rKaiTQyaijI: Downloading android vr player API JSON
WARNING: ... Some android client https formats have been skipped ... SABR-only streaming experiment
[info] rKaiTQyaijI: Downloading 1 format(s): 401+251
[download] Destination: ...
[download] 1.8% of 1.06GiB ...
ERROR: unable to download video data: HTTP Error 403: Forbidden
```

**Cause:** SABR / blocked high-quality DASH (`401+251`).  
**Lesson:** “Started downloading” ≠ will finish; 403 can hit mid-file.

---

### T6 — CMD: progressive success (proof of life)

**Command:**

```cmd
yt-dlp --extractor-args "youtube:player_client=android,web" -f "bv*+ba/b" -o "%USERPROFILE%\Desktop\whop clips\test.%(ext)s" "https://youtu.be/rKaiTQyaijI"
```

**Result:**

```text
[info] rKaiTQyaijI: Downloading 1 format(s): 18
[download] 100% of 126.16MiB in 00:00:18 at 6.71MiB/s
```

**Lesson:** Format **18** (progressive) worked on the same machine/network where `401+251` 403’d. Backend cascade exists to try HQ first, then safe formats.

---

### T7 — Output template typo on Windows CMD

**Mistake:** `-o "...\test.%%(ext)s"` (doubled `%` from batch escaping habits).

**Symptom:** File saved with a literal `%(ext)s` in the name instead of `.mp4`.  
**Fix:** In interactive CMD use a single `%`: `-o "%USERPROFILE%\Desktop\whop clips\test.%(ext)s"`.

---

### T8 — `pip install -U --pre "yt-dlp[default]"` cancelled

**Symptom:** `ERROR: Operation cancelled by user`  
**Note:** Upgrade was recommended for fresher extractors; not required to explain T6 success, but still recommended periodically.

---

### T9 — Quality “works but looks bad”

**Symptom:** After cascade/safe path, download succeeds but resolution is low (progressive ceiling).  
**Cause:** Intentional tradeoff when DASH HQ 403s.  
**Fix direction:** Keep HQ-first cascade; optional cookies, EJS/Node, yt-dlp nightly; do not promise permanent 1080p/4K.

---

### T10 — Pasting chat text into CMD

**Symptom:**

```text
cd redo, heres the path for the folder C:\Users\...
The filename, directory name, or volume label syntax is incorrect.
```

**Cause:** Whole chat sentence pasted as a command.  
**Fix:** Only paste pure commands / paths.

---

### T11 — Full video download has no sound; clips from same URL have sound (2026-08-24)

**Where:** Dashboard → full **Download** (POST `/download`) vs **Clip** extract.  
**Symptom:** ~19 min YouTube full download plays with **no audio**. Clipping a section of the **same** URL produces a file **with** audio.

**Cause:**
- Full download uses format cascade; HQ DASH (`bestvideo+bestaudio`) can exit **0** with a **video-only** file when merge is incomplete or a video-only format is selected.
- Cascade previously only retried on **403/SABR-style stderr**, not on “success but silent.”
- Clip path uses `--download-sections` and remuxes a short segment, which more often keeps an audio track — so clips looked fine while full downloads did not.

**Fix (shipped `main`, commit message: Fix silent full-video downloads…):**
- `probe_has_audio()` via ffprobe after each successful yt-dlp run.
- If the output has **no audio stream** and the caller wanted video+audio → delete partials and **try the next format** (safe progressive).
- YouTube `player_client` set to **`android,web`**.
- Cascade default timeout **600s** for longer full videos.

**Verify:**

```cmd
ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "path\to\file.mp4"
```

Expect both `video` and `audio`. Re-download the same full URL after `git pull` + backend restart.

**File:** `backend/app/core/ytdlp_client.py` (`run_with_format_cascade`, `probe_has_audio`).

---

### T12 — Uvicorn from repo root: No module named 'app'

**Symptom:**

```text
ModuleNotFoundError: No module named 'app'
```

**Cause:** `uvicorn app.main:app` run from `whop-toolkit-web\` instead of `whop-toolkit-web\backend\`.  
**Fix:**

```cmd
cd backend
uvicorn app.main:app --reload --port 8000
```

---

### Quick recovery checklist

| Symptom | First check |
|---------|-------------|
| Uvicorn import crash / no module `app` | `cd backend`; T1 indentation; T12 cwd |
| 403 / ANDROID_VR / ffmpeg exit | Client + format cascade; update yt-dlp |
| DRM protected | Try `android,web`; other formats may still exist |
| 0-item recommended playlist | Full video URL with id |
| Low quality but success | Expected under SABR; HQ try still runs first |
| **Full download silent; clip has sound** | **T11** — pull latest `ytdlp_client`; re-download; ffprobe audio |
| No file in `whop clips` | Set `LOCAL_OUTPUT_DIR`; only copies on **success** |

---

## Current focus (2026-08-24)

- **YouTube path solid** before other platforms or deploy.
- TikTok rehydration / paid scraper APIs = **out of scope** until YouTube checklist is green.
- Smoke: metadata → full download (with audio) → clip → transcript → analyze.

---

## Deploy & cost (short)

- Frontend free tiers (Vercel/Pages) OK for UI.
- Backend (yt-dlp + ffmpeg + Whisper) needs a **real** always-on box eventually; free tiers sleep/throttle.
- Gemini free tier is for demos; production needs billing + per-user limits.
- Capacity is limited by **concurrent extract/transcribe jobs**, not registered Whop users.

---

## AI handoff prompt (copy-paste)

> Read `docs/SESSION_NOTES.md` and `docs/REVIEW_AND_ROADMAP.md`.  
> **Documentation rule:** every code/behavior change must update SESSION_NOTES in the same session (test log T#, strategy, recovery checklist as needed).  
> Pay attention to **Test log / errors seen** before changing yt-dlp options.  
> YouTube: quality cascade (HQ DASH → progressive on 403); **also cascade when ffprobe finds no audio (T11)**; clients android+web.  
> Local output: respect `LOCAL_OUTPUT_DIR`.  
> Export aspect/fit/quality are UI-ready but backend must apply ffmpeg recipes (P2).  
> Do not claim FastAPI UA as root cause of 403 on localhost. Update these docs when you change download behavior.
