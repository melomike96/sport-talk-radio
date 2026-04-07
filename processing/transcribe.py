from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import whisper


class TranscriptionError(Exception):
    """Raised when transcription fails."""


def _normalize_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for segment in segments:
        normalized.append(
            {
                "start": float(segment.get("start", 0.0)),
                "end": float(segment.get("end", 0.0)),
                "text": str(segment.get("text", "")).strip(),
            }
        )
    return normalized


def transcribe_audio(
    audio_file: Path | str,
    output_dir: Path | str = Path("data/transcripts"),
    model_name: str = "base",
) -> Path:
    """
    Transcribe an audio file with Whisper and save JSON segments.

    Args:
        audio_file: Path to the MP3 file.
        output_dir: Directory where transcript JSON is written.
        model_name: Whisper model size.

    Returns:
        Path to generated transcript JSON.
    """
    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file does not exist: {audio_path}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        model = whisper.load_model(model_name)
        result = model.transcribe(str(audio_path))
    except Exception as exc:  # noqa: BLE001 - surface clean domain error
        raise TranscriptionError(f"Whisper transcription failed: {exc}") from exc

    segments = _normalize_segments(result.get("segments", []))

    transcript_payload = {
        "source_audio": str(audio_path),
        "model": model_name,
        "segments": segments,
    }

    output_file = output_path / f"{audio_path.stem}.json"
    output_file.write_text(json.dumps(transcript_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return output_file
