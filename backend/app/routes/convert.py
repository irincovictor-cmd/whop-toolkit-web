"""
POST /convert

Web successor to modules/converter.py. Same fixed set of known-good ffmpeg
recipes as the CLI -- deliberately not "arbitrary ffmpeg args from the
client," since accepting free-form ffmpeg flags from a public API is a
command-injection-adjacent risk the CLI never had to think about (single
local user) but a public web service absolutely does.
"""

import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

router = APIRouter()

RECIPES = {
    "mp4": (["-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-vf", "format=yuv420p"], ".mp4"),
    "mkv": (["-c", "copy"], ".mkv"),
    "webm": (["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus"], ".webm"),
    "mp3": (["-vn", "-acodec", "libmp3lame", "-q:a", "2"], ".mp3"),
    "wav": (["-vn", "-acodec", "pcm_s16le"], ".wav"),
}


@router.post("")
async def convert_file(file: UploadFile = File(...), target: str = Form(...)):
    if target not in RECIPES:
        raise HTTPException(status_code=400, detail=f"Unsupported target format: {target}")

    work_dir = Path(tempfile.mkdtemp(prefix="convert_"))
    input_path = work_dir / file.filename
    with open(input_path, "wb") as f:
        f.write(await file.read())

    ffmpeg_args, ext = RECIPES[target]
    output_path = work_dir / f"{input_path.stem}_converted{ext}"

    cmd = ["ffmpeg", "-y", "-i", str(input_path), *ffmpeg_args, str(output_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0 or not output_path.exists():
        raise HTTPException(status_code=500, detail=f"Conversion failed: {result.stderr[-800:]}")

    return FileResponse(path=str(output_path), filename=output_path.name)
