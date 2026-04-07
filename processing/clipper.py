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


def _extract_clips(
    source_file: Path,
    highlights: list[dict],
    output_dir: Path,
    suffix: str,
    ffmpeg_args: list[str],
) -> list[Path]:
    created: list[Path] = []
    stem = source_file.stem

    for item in highlights:
        rank = int(item.get("rank", len(created) + 1))
        start = float(item.get("start", 0.0))
        end = float(item.get("end", 0.0))
        if end <= start:
            continue

        clip_path = output_dir / f"{stem}_highlight_{rank:02d}.{suffix}"

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-i",
            str(source_file),
            *ffmpeg_args,
            str(clip_path),
        ]

        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            raise ClipExtractionError(
                f"ffmpeg failed creating {clip_path.name}: {completed.stderr.strip()}"
            )

        created.append(clip_path)

    return created


def _load_highlights(highlights_file: Path | str) -> tuple[Path, Path | None, list[dict]]:
    highlights_path = Path(highlights_file)
    if not highlights_path.exists():
        raise ClipExtractionError(f"Highlights file not found: {highlights_path}")

    payload = json.loads(highlights_path.read_text(encoding="utf-8"))
    source_audio = Path(payload.get("source_audio", ""))
    source_video_raw = payload.get("source_video")
    source_video = Path(source_video_raw) if isinstance(source_video_raw, str) and source_video_raw else None
    highlights = payload.get("highlights", [])

    if not source_audio.exists():
        raise ClipExtractionError(f"Source audio missing: {source_audio}")
    if source_video is not None and not source_video.exists():
        raise ClipExtractionError(f"Source video missing: {source_video}")
    if not isinstance(highlights, list):
        raise ClipExtractionError("Highlights JSON missing valid 'highlights' list.")

    return source_audio, source_video, highlights


def extract_audio_clips(
    highlights_file: Path | str,
    output_dir: Path | str = Path("data/clips"),
) -> list[Path]:
    _ensure_ffmpeg_available()
    source_audio, _, highlights = _load_highlights(highlights_file)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    return _extract_clips(
        source_file=source_audio,
        highlights=highlights,
        output_dir=out_dir,
        suffix="mp3",
        ffmpeg_args=["-vn", "-acodec", "libmp3lame", "-q:a", "2"],
    )


def extract_video_clips(
    highlights_file: Path | str,
    output_dir: Path | str = Path("data/video_clips"),
) -> list[Path]:
    _ensure_ffmpeg_available()
    _, source_video, highlights = _load_highlights(highlights_file)
    if source_video is None:
        raise ClipExtractionError(
            "Highlights JSON does not include source_video. Run with --with-video-clips to download video first."
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    return _extract_clips(
        source_file=source_video,
        highlights=highlights,
        output_dir=out_dir,
        suffix="mp4",
        ffmpeg_args=["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart"],
    )
