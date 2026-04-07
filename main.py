from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ingest.youtube_ingest import YouTubeIngestError, download_audio, download_video
from processing.clipper import ClipExtractionError, extract_audio_clips, extract_video_clips
from processing.highlights import HighlightGenerationError, generate_highlights
from processing.transcribe import TranscriptionError, transcribe_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download YouTube audio, transcribe with Whisper, and optionally create highlight clips."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--audio-dir", type=Path, default=Path("data/raw_audio"), help="Directory to store downloaded MP3 files")
    parser.add_argument("--transcript-dir", type=Path, default=Path("data/transcripts"), help="Directory to store transcript JSON files")
    parser.add_argument("--model", default="base", help="Whisper model size (e.g. tiny, base, small, medium, large)")
    parser.add_argument("--with-highlights", action="store_true", help="Generate highlight candidates and extract audio clips")
    parser.add_argument("--with-video-clips", action="store_true", help="Also export matching MP4 clips from downloaded source video")
    parser.add_argument("--highlights-dir", type=Path, default=Path("data/highlights"), help="Directory to write highlight JSON")
    parser.add_argument("--clips-dir", type=Path, default=Path("data/clips"), help="Directory to write extracted audio clip MP3 files")
    parser.add_argument("--video-dir", type=Path, default=Path("data/raw_video"), help="Directory to store downloaded source video")
    parser.add_argument("--video-clips-dir", type=Path, default=Path("data/video_clips"), help="Directory to write extracted video clip MP4 files")
    parser.add_argument("--top-n", type=int, default=5, help="Number of highlights to select")
    parser.add_argument("--clip-padding", type=float, default=8.0, help="Seconds to pad around highlight segments")
    parser.add_argument("--max-clip-duration", type=float, default=60.0, help="Maximum clip duration in seconds")
    return parser.parse_args()


def run(args: argparse.Namespace) -> Path:
    audio_file = download_audio(url=args.url, output_dir=args.audio_dir)
    print(f"[1/4] Audio downloaded: {audio_file}")

    transcript_file = transcribe_audio(
        audio_file=audio_file,
        output_dir=args.transcript_dir,
        model_name=args.model,
    )
    print(f"[2/4] Transcript saved: {transcript_file}")

    if not args.with_highlights:
        return transcript_file

    source_video = None
    if args.with_video_clips:
        source_video = download_video(url=args.url, output_dir=args.video_dir)
        print(f"[3/6] Source video downloaded: {source_video}")

    highlights_file = generate_highlights(
        transcript_file=transcript_file,
        output_dir=args.highlights_dir,
        top_n=max(1, args.top_n),
        clip_padding=max(0.0, args.clip_padding),
        max_clip_duration=max(5.0, args.max_clip_duration),
        source_video=source_video,
    )
    step = "[4/6]" if args.with_video_clips else "[3/4]"
    print(f"{step} Highlights saved: {highlights_file}")

    audio_clips = extract_audio_clips(highlights_file=highlights_file, output_dir=args.clips_dir)
    step = "[5/6]" if args.with_video_clips else "[4/4]"
    print(f"{step} Audio clips exported: {len(audio_clips)} file(s) -> {args.clips_dir}")

    if args.with_video_clips:
        video_clips = extract_video_clips(highlights_file=highlights_file, output_dir=args.video_clips_dir)
        print(f"[6/6] Video clips exported: {len(video_clips)} file(s) -> {args.video_clips_dir}")

    return transcript_file


def main() -> int:
    args = parse_args()

    try:
        run(args)
        return 0
    except (
        YouTubeIngestError,
        TranscriptionError,
        HighlightGenerationError,
        ClipExtractionError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
