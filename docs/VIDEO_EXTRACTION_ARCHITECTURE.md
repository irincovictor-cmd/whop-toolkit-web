# System Architecture Specification: Video Extraction Subsystem

**Document title:** Technical Architecture Shift & Architectural Guidelines  
**Project:** Whop Web Toolkit  
**Audience:** AI Engineering Assistant / Lead Developer  
**Status:** Canonical direction for production video extraction (2026-08-24)  
**Related:** `docs/SESSION_NOTES.md`, `docs/REVIEW_AND_ROADMAP.md`, `docs/MIGRATION_PLAN.md`

---

## 1. Executive summary

This document outlines the architectural refactoring of the video extraction subsystem within the Whop Web Toolkit.

The **initial implementation relying on server-side yt-dlp execution** has been deemed **unsustainable for production** due to:

- Rapid upstream platform security updates
- IP blocking and edge anti-bot controls
- High maintenance overhead

This spec details the technical limitations of the current implementation and defines **approved alternative engineering strategies** for downstream development.

> **Note for local/dev:** yt-dlp may still be used on the developer’s machine for YouTube-first hardening and demos. This document governs **production / shareable product architecture**, not day-to-day local experiments.

---

## 2. Problem statement & technical constraints

### Maintainability & upstream lag

Target media platforms regularly update:

- Signature generation algorithms (e.g. X-Bogus, n-sig)
- Request headers
- CDN validation rules

Reverse-engineered extraction libraries (yt-dlp) suffer from inevitable **update latency**, causing regular service disruptions (examples already seen: TikTok rehydration failures, YouTube SABR/403, silent or low-quality merges).

### Network & edge security infrastructure

Server-side execution triggers automated anti-bot protections, including:

- TLS fingerprinting
- IP address blacklisting / datacenter reputation
- Rate limiting

CDN URLs generated via backend servers frequently fail with **403 Forbidden** due to IP and header mismatches relative to a real browser session.

### Platform compliance

System architecture must align with **Whop Developer Guidelines** regarding unauthorized data extraction and automated access. Production design should prefer approaches that do not depend on sustained reverse-engineering of third-party platforms on Whop-hosted infrastructure.

---

## 3. Targeted architectural strategy

To improve availability and reduce extraction failure rates, **future development will transition away from server-hosted reverse-engineering tools** toward one of the following validated approaches:

### Option A: Client-side network interception (**recommended**)

**Mechanism:** Companion browser extension intercepts media network requests (`.m3u8` playlists, segmented MP4 / transport streams) in the user’s local browser context via `chrome.declarativeNetRequest` or `webRequest` APIs.

**Advantage:** Uses valid, authenticated client sessions; avoids server IP blocks and continuous signature reverse-engineering on our backend.

### Option B: Managed extraction infrastructure

**Mechanism:** Offload stream extraction to specialized third-party scraping infrastructure (headless browser fleets, proxy-rotated actor networks via managed APIs) rather than maintaining local yt-dlp binaries on our servers.

**Advantage:** Signature updates and proxy rotation are handled by the vendor; we pay for reliability instead of owning extractor breakage.

**Tradeoff:** Cost per job; vendor lock-in; still must evaluate ToS/compliance.

### Option C: Pivot to native platform APIs

**Mechanism:** Deprioritize unauthenticated third-party video downloading in favor of **official Whop API integrations** (membership management, course dashboards, webhooks, Discord user sync, etc.).

**Advantage:** Sustainable product surface aligned with Whop’s ecosystem; lower legal and ops risk.

---

## 4. Implications for the current codebase

| Layer | Current state | Direction |
|-------|---------------|-----------|
| `backend/app/core/ytdlp_client.py` | Local/dev extraction | Not the long-term production core |
| `backend/app/routes/download.py`, `clips.py` | Server yt-dlp | Replace or gate behind non-prod / self-hosted-only |
| Transcript / Whisper | Can stay server-side on **user-provided files** or audio already obtained client-side | Prefer “user uploads file → process” over “server fetches URL” |
| Frontend tabs (Download / Clip / …) | Built around URL → server fetch | Evolve toward extension-assisted capture or upload-first |

**Do not** invest major new effort in productionizing multi-platform server-side yt-dlp (TikTok fallbacks, Apify as primary path, etc.) without revisiting this spec.

---

## 5. Developer directive / Claude (and Grok) prompt

Copy-paste for AI assistants:

> Review `docs/VIDEO_EXTRACTION_ARCHITECTURE.md` for the Whop Web Toolkit video extraction subsystem. **Server-side yt-dlp execution is deprecated for the production path** due to high maintenance cost, edge blocking, and upstream security changes. Use the constraints and alternative strategies in that specification (Option A preferred, then B, then C) to guide all technical recommendations, refactoring tasks, and feature designs. Local yt-dlp for developer YouTube testing is allowed; do not treat it as the long-term cloud architecture.

---

## 6. Decision log

| Date | Decision |
|------|----------|
| 2026-08-24 | Spec adopted by project owner; document added to repo for Grok/Claude handoff |
