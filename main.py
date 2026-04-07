from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ingest.youtube_ingest import YouTubeIngestError, download_audio
from processing.transcribe import TranscriptionError, transcribe_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download YouTube audio and generate Whisper transcript JSON."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("data/raw_audio"),
        help="Directory to store downloaded MP3 files",
    )
    parser.add_argument(
        "--transcript-dir",
        type=Path,
        default=Path("data/transcripts"),
        help="Directory to store transcript JSON files",
    )
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model size (e.g. tiny, base, small, medium, large)",
    )
    return parser.parse_args()


def run(url: str, audio_dir: Path, transcript_dir: Path, model_name: str) -> Path:
    audio_file = download_audio(url=url, output_dir=audio_dir)
    print(f"[1/2] Audio downloaded: {audio_file}")

    transcript_file = transcribe_audio(
        audio_file=audio_file,
        output_dir=transcript_dir,
        model_name=model_name,
    )
    print(f"[2/2] Transcript saved: {transcript_file}")

    return transcript_file


def main() -> int:
    args = parse_args()

    try:
        run(
            url=args.url,
            audio_dir=args.audio_dir,
            transcript_dir=args.transcript_dir,
            model_name=args.model,
        )
        return 0
    except (YouTubeIngestError, TranscriptionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
