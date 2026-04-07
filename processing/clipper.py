from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class ClipExtractionError(Exception):
    """Raised when clip extraction fails."""


def _ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise ClipExtractionError("ffmpeg is required for clip extraction but was not found on PATH.")


def extract_audio_clips(
    highlights_file: Path | str,
    output_dir: Path | str = Path("data/clips"),
) -> list[Path]:
    _ensure_ffmpeg_available()

    highlights_path = Path(highlights_file)
    if not highlights_path.exists():
        raise ClipExtractionError(f"Highlights file not found: {highlights_path}")

    payload = json.loads(highlights_path.read_text(encoding="utf-8"))
    source_audio = Path(payload.get("source_audio", ""))
    highlights = payload.get("highlights", [])

    if not source_audio.exists():
        raise ClipExtractionError(f"Source audio missing: {source_audio}")
    if not isinstance(highlights, list):
        raise ClipExtractionError("Highlights JSON missing valid 'highlights' list.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    stem = source_audio.stem

    for item in highlights:
        rank = int(item.get("rank", len(created) + 1))
        start = float(item.get("start", 0.0))
        end = float(item.get("end", 0.0))
        if end <= start:
            continue

        clip_path = out_dir / f"{stem}_highlight_{rank:02d}.mp3"

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-i",
            str(source_audio),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            str(clip_path),
        ]

        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            raise ClipExtractionError(
                f"ffmpeg failed creating {clip_path.name}: {completed.stderr.strip()}"
            )

        created.append(clip_path)

    return created
