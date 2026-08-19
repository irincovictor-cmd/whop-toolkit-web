# Whop Toolkit — Sharing Guide

How to hand this folder to someone else and get them running from zero.

## What to Send

Zip up the whole `Whop Toolkit` folder **except** these, which are either
personal, huge, or regenerable:

- `projects/` — your own downloaded videos, transcripts, and clips.
  Unless you specifically want to hand over your library too, leave this
  out (or send it separately if it's the point of the share).
- `cache/`, `logs/`, `models/` — regenerated automatically on first run.
- `activity_log.json`, `settings.json` — your personal session history
  and preferences.
- Any `__pycache__` folders.

A clean share should basically be: the `.py` files, `config.py`,
`requirements.txt`, and `docs/`.

Quick way to zip a clean copy (run from one level above the folder):

**Windows (PowerShell):**
```powershell
Compress-Archive -Path "Whop Toolkit" -DestinationPath "Whop-Toolkit-Share.zip" -Force
```
Then manually remove `projects/`, `cache/`, `logs/`, `activity_log.json`,
and `settings.json` from inside the zip before sending, or delete them
from a copy of the folder first.

**macOS (Terminal):**
```bash
cp -R "Whop Toolkit" "Whop-Toolkit-Share"
rm -rf "Whop-Toolkit-Share/projects" "Whop-Toolkit-Share/cache" "Whop-Toolkit-Share/logs"
rm -f "Whop-Toolkit-Share/activity_log.json" "Whop-Toolkit-Share/settings.json"
zip -r "Whop-Toolkit-Share.zip" "Whop-Toolkit-Share"
```

## Getting the Other Person Set Up

Send them the zip plus this one instruction:

> Unzip this anywhere, then follow `docs/USER_GUIDE.md` — it has full
> install steps for both Windows and Mac.

That's genuinely all they need. The User Guide walks through installing
Python, FFmpeg, and the Python packages (`pip install -r requirements.txt`),
and how to run `whop.py`.

## What Happens Automatically on Their First Run

- `config.py` creates `projects/`, `cache/`, `logs/`, and `models/` inside
  wherever they put the folder — no manual setup needed, and no hardcoded
  paths to edit (this used to be a problem in early versions where the
  root path was hardcoded to one specific machine; that's fixed now).
- `activity_log.json` and `settings.json` are created fresh the first
  time an action runs, defaulting Auto-Clean to OFF.

## If They Hit Install Problems

Point them at the **Troubleshooting** section at the bottom of
`docs/USER_GUIDE.md` first — it covers the two most common issues
(Python/FFmpeg not being recognized as commands, which almost always
means the PATH step was skipped or the terminal wasn't reopened
afterward).

## Version Control (Optional, for Developers)

If you're sharing this via Git instead of a zip, add a `.gitignore` with:

```
projects/
cache/
logs/
models/
activity_log.json
settings.json
__pycache__/
*.pyc
```

This keeps every collaborator's personal video library and local state
out of the shared repo, while all the actual code stays tracked.
