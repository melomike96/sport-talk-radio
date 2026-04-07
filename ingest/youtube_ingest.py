from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Final

import yt_dlp


YOUTUBE_URL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/).+"
)


class YouTubeIngestError(Exception):
    """Raised when YouTube media ingestion fails."""


def _validate_youtube_url(url: str) -> None:
    if not url or not YOUTUBE_URL_PATTERN.match(url.strip()):
        raise YouTubeIngestError(
            "Invalid YouTube URL. Expected formats like "
            "https://www.youtube.com/watch?v=... or https://youtu.be/..."
        )


def _ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise YouTubeIngestError(
            "ffmpeg is not installed or not available on PATH. "
            "Please install ffmpeg before running this pipeline."
        )


def _latest_file(path: Path, pattern: str) -> Path:
    candidates = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise YouTubeIngestError(f"No output file found with pattern {pattern!r} in {path}")
    return candidates[-1]


def download_audio(url: str, output_dir: Path | str = Path("data/raw_audio")) -> Path:
    _validate_youtube_url(url)
    _ensure_ffmpeg_available()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_path / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio")
            expected_file = output_path / f"{title}.mp3"

        return expected_file if expected_file.exists() else _latest_file(output_path, "*.mp3")
    except yt_dlp.utils.DownloadError as exc:
        raise YouTubeIngestError(f"Failed to download audio from YouTube: {exc}") from exc


def download_video(url: str, output_dir: Path | str = Path("data/raw_video")) -> Path:
    _validate_youtube_url(url)
    _ensure_ffmpeg_available()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": str(output_path / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")
            expected_file = output_path / f"{title}.mp4"

        return expected_file if expected_file.exists() else _latest_file(output_path, "*.mp4")
    except yt_dlp.utils.DownloadError as exc:
        raise YouTubeIngestError(f"Failed to download video from YouTube: {exc}") from exc
