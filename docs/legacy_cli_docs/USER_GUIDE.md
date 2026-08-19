# Whop Toolkit — User Guide

This guide assumes you've never used a command line before. Follow it top to
bottom once, and you'll have a working toolkit.

Whop Toolkit runs entirely on your own computer. There's no app to open, no
account to log into — you type commands into a terminal window and the
toolkit does the rest. Everything it downloads and creates is saved into
plain folders on your hard drive.

---

## Part 1 — Installing the Requirements

You need three things installed: **Python**, **FFmpeg**, and the Python
packages this toolkit uses (yt-dlp, etc.). Pick your operating system below.

### Windows

**1. Install Python**
- Go to https://www.python.org/downloads/
- Download the latest Python 3 installer.
- Run it. **Important:** on the first install screen, check the box that
  says **"Add python.exe to PATH"** before clicking Install. If you miss
  this, Windows won't recognize the `python` command later.
- To check it worked, open the **Start Menu**, type `cmd`, press Enter to
  open Command Prompt, and type:
  ```
  python --version
  ```
  You should see something like `Python 3.12.x`.

**2. Install FFmpeg**
- Go to https://www.gyan.dev/ffmpeg/builds/ and download the
  "release essentials" build (a `.zip` file).
- Extract the zip somewhere permanent, e.g. `C:\ffmpeg`.
- Add it to your PATH so Windows can find it:
  1. Press Start, search "Environment Variables", open
     **"Edit the system environment variables"**.
  2. Click **Environment Variables**.
  3. Under "System variables", find `Path`, click **Edit**, click **New**,
     and add `C:\ffmpeg\bin` (or wherever you extracted it, with `\bin` at
     the end).
  4. Click OK on everything, then **close and reopen** Command Prompt.
- Check it worked:
  ```
  ffmpeg -version
  ```

**3. Install the Python packages**
- In Command Prompt, navigate to the Whop Toolkit folder, e.g.:
  ```
  cd Desktop\Whop Toolkit
  ```
- Install everything the toolkit needs:
  ```
  pip install -r requirements.txt
  ```

### macOS

**1. Install Homebrew** (a package manager — skip if you already have it)
- Open **Terminal** (Cmd+Space, type "Terminal", press Enter).
- Paste this and press Enter:
  ```
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
- Follow the on-screen instructions (it may ask for your Mac password).

**2. Install Python and FFmpeg with Homebrew**
```
brew install python ffmpeg
```
- Check both worked:
  ```
  python3 --version
  ffmpeg -version
  ```

**3. Install the Python packages**
- In Terminal, navigate to the Whop Toolkit folder, e.g.:
  ```
  cd ~/Desktop/"Whop Toolkit"
  ```
- Install everything the toolkit needs:
  ```
  pip3 install -r requirements.txt
  ```

---

## Part 2 — Running the Toolkit

From inside the `Whop Toolkit` folder in your terminal:

- **Windows:** `python whop.py`
- **macOS:** `python3 whop.py`

The first time you run it, you'll see a welcome message (it'll say this
looks like your first run). After that, it'll greet you with a short recap
of what you did last session.

You'll then see the main menu:

```
=== Whop Toolkit ===
  1. Extract Transcript (Get clean text to copy-paste into AI)
  2. Direct YouTube Video Clipper (Fast clip download by URL + Timestamps)
  3. Quick Stream-Crop (Crop via manual timestamps or Drag-and-Drop file)
  4. Smart Media Converter (Convert video/audio formats)
  5. Exit
```

Type a number and press Enter to pick an option.

### Option 1 — Extract Transcript
First you'll be asked where the video is coming from:
- **YouTube URL** — paste a link.
- **A file I already have** — type or drag-and-drop the path to a video
  file already sitting on your computer. It gets copied into its own
  project folder (converted to `.mp4` first if it isn't already one).
  Since there's no YouTube captions to check for a local file, it goes
  straight to local Whisper transcription.

The toolkit will:
- Try to grab YouTube's own captions first (instant, no setup needed).
- If the video has no captions (or it's a local file), it transcribes
  locally using Whisper. You'll be asked to pick a model:
  - **base** — fastest, good enough for finding highlights.
  - **small** — a balance of speed and accuracy.
  - **medium** — most accurate, but slowest on an average laptop.
- The result is saved as `transcript.txt` (clean text -- copy-paste it
  straight into ChatGPT/Claude to find highlights) and `transcript.srt`.

Whichever video you use here becomes this session's "active video" —
Option 3 can jump straight to cropping it without asking again.

### Option 2 — Direct YouTube Video Clipper
The fast path when you already know the timestamps you want and don't
need a transcript at all. Paste a URL, the toolkit checks the video's
length, you enter start/end timestamps (validated against the actual
video length so you can't accidentally ask for more than exists), pick
a format, and it crops **directly from YouTube's stream** — no full
video download first. The clip lands in the `quick_clips/` folder.

### Option 3 — Quick Stream-Crop
- If you just ran Option 1 this session, it reuses that same video
  automatically and jumps straight to asking for timestamps.
- Otherwise, it asks you to drag-and-drop a local file (or paste its
  path) — quotes around a dragged path are handled automatically.

Either way, you'll then pick:
- **Format:** Vertical 9:16 (letterboxed with black bars top/bottom, so
  faces never get cropped out — good for Reels/TikTok/Shorts) or
  Landscape 16:9 (original layout, untouched).
- **Target file size cap (optional):** e.g. type `50` to keep the clip
  under 50MB for a platform's upload limit. Skip it and the clip is
  encoded at the highest practical quality instead.

The finished clip is saved into `quick_clips/`.

### Option 4 — Smart Media Converter
Drag-and-drop (or paste the path to) any local video or audio file. The
toolkit looks at the file extension and automatically shows the right
menu:

**Video files** (.mov, .mkv, .avi, .flv, .webm, .wmv, .mp4):
1. Convert to Universal Web MP4 (H.264 / AAC) — the safest, most
   compatible format for uploading almost anywhere.
2. Convert to Matroska (.mkv) — fast, no re-encoding (a straight
   container repackage).
3. Convert to WebM (.webm) — smaller file size, VP9/Opus.
4. Extract Audio Track Only (.mp3)
5. Extract High-Res Audio Track Only (.wav) — uncompressed, largest file.

**Audio files** (.wav, .aac, .m4a, .flac, .ogg, .mp3):
1. Convert to Compressed MP3
2. Convert to Standard AAC/M4A
3. Convert to High-Res Lossless WAV

The converted file is always saved as `<original name>_converted.<ext>`
inside a `converted_media/` folder — your original file is never
touched or overwritten.

---

## Part 3 — Where Everything Is Saved

Everything the toolkit *generates* lives under one `data/` folder,
kept separate from the app's own code -- so the project root stays
easy to scan, and you always know `data/` is the only thing that's
safe to delete/back up/move without touching the app itself.

```
Whop Toolkit/
  whop.py, config.py, core/, modules/, docs/   <- the app itself
  data/
    projects/                    <- the folder for all projects
      <video title>/               <- one subfolder per project
        info.json                    <- video metadata
        transcripts/
          transcript.txt
          transcript.srt
        source.mp4                   <- cached full download (Option 1 only)
    quick_clips/
      <title>_<timestamp>.mp4   <- output from Options 2 and 3
    converted_media/
      <name>_converted.<ext>    <- output from Option 4
    cache/, logs/, models/      <- internal, safe to ignore
    activity_log.json           <- your recent session history
```

Nothing is stored in the cloud. If you delete the `Whop Toolkit` folder,
everything is gone -- so back it up if you care about keeping old clips.
`data/` is the only folder you ever need to back up; everything else is
just the app.

---

## Troubleshooting

- **"python is not recognized"** (Windows) — Python wasn't added to PATH.
  Re-run the installer and check the "Add to PATH" box, or search
  "Add Python to PATH Windows" for a fix without reinstalling.
- **"ffmpeg is not recognized" / "command not found"** — FFmpeg isn't on
  your PATH. Re-check the PATH steps above, and make sure you opened a
  *new* terminal window after changing it.
- **Whisper transcription is very slow** — try the `base` model instead
  of `small`/`medium`, especially on an older laptop.
- **Drag-and-drop doesn't seem to do anything** — this is your terminal
  app's job, not the toolkit's; the terminal has to actually be the
  focused window (click it first) and you have to drop right at a
  "Where's the file?" prompt, not at the main menu. If it still doesn't
  cooperate, every one of those prompts also offers **"Open a file
  browser window instead"** — a normal Browse dialog, same as any other
  app, no drag-and-drop needed at all.
- Errors are always saved to `logs/whop.log` — check there for details if
  something fails silently.
