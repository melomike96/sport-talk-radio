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
    """Raised when YouTube audio ingestion fails."""


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


def download_audio(url: str, output_dir: Path | str = Path("data/raw_audio")) -> Path:
    """
    Download and convert YouTube audio to MP3.

    Args:
        url: YouTube URL.
        output_dir: Directory where MP3 audio will be stored.

    Returns:
        Path to the downloaded MP3 file.
    """
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

        if not expected_file.exists():
            mp3_candidates = sorted(output_path.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
            if not mp3_candidates:
                raise YouTubeIngestError("Download completed but no MP3 file was found.")
            return mp3_candidates[-1]

        return expected_file
    except yt_dlp.utils.DownloadError as exc:
        raise YouTubeIngestError(f"Failed to download audio from YouTube: {exc}") from exc
