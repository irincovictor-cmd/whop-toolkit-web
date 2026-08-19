# Migrating to the new data/ folder structure

As of v0.11, everything the toolkit generates lives under one `data/`
folder, separate from the app's code. If you're updating an existing
install (not a fresh download), run this **once**, before running the
updated `whop.py`, so your existing projects/clips/history aren't lost
or orphaned.

## Windows (PowerShell)

Open a terminal in your `Whop Toolkit` folder and run:

```powershell
New-Item -ItemType Directory -Force -Path data | Out-Null
foreach ($item in "projects","quick_clips","converted_media","cache","logs","models") {
    if (Test-Path $item) { Move-Item $item "data\$item" }
}
foreach ($item in "activity_log.json","settings.json") {
    if (Test-Path $item) { Move-Item $item "data\$item" }
}
```

## macOS / Linux

```bash
mkdir -p data
for item in projects quick_clips converted_media cache logs models; do
  [ -d "$item" ] && mv "$item" "data/$item"
done
for item in activity_log.json settings.json; do
  [ -f "$item" ] && mv "$item" "data/$item"
done
```

## After migrating

Replace `whop.py`, `config.py`, and the rest of the app files with the
updated versions, then run `python whop.py` as normal -- it'll read
straight from `data/projects/`, `data/activity_log.json`, etc.

## While you're in there

If your project root still has stray 0 KB files left over from pasting
transcript text directly into the terminal (files named things like
`a`, `Absolutely`, `[laughter]`), this is a good time to clean those up
too:

```powershell
Get-ChildItem -File | Where-Object { $_.Length -eq 0 } | Remove-Item
```
