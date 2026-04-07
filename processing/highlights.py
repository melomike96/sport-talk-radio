from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class HighlightGenerationError(Exception):
    """Raised when highlight generation fails."""


INTERESTING_KEYWORDS = {
    "touchdown",
    "interception",
    "trade",
    "injury",
    "upset",
    "playoffs",
    "championship",
    "buzzer",
    "crazy",
    "wild",
    "insane",
    "unbelievable",
    "clutch",
    "breaking",
    "fired",
    "suspended",
}


@dataclass(frozen=True)
class Highlight:
    rank: int
    start: float
    end: float
    score: float
    text: str


WORD_PATTERN = re.compile(r"[a-zA-Z']+")


def _segment_score(text: str) -> float:
    words = [w.lower() for w in WORD_PATTERN.findall(text)]
    if not words:
        return 0.0

    keyword_hits = sum(1 for w in words if w in INTERESTING_KEYWORDS)
    punctuation_boost = text.count("!") * 0.5 + text.count("?") * 0.2
    uppercase_words = sum(1 for w in text.split() if len(w) > 2 and w.isupper())

    return keyword_hits * 2.0 + punctuation_boost + uppercase_words * 0.25


def _load_transcript_segments(transcript_file: Path) -> tuple[list[dict[str, Any]], str]:
    if not transcript_file.exists():
        raise HighlightGenerationError(f"Transcript file not found: {transcript_file}")

    payload = json.loads(transcript_file.read_text(encoding="utf-8"))
    segments = payload.get("segments")
    if not isinstance(segments, list):
        raise HighlightGenerationError("Transcript JSON missing valid 'segments' list.")

    source_audio = payload.get("source_audio")
    if not isinstance(source_audio, str) or not source_audio.strip():
        raise HighlightGenerationError("Transcript JSON missing 'source_audio'.")

    return segments, source_audio


def generate_highlights(
    transcript_file: Path | str,
    output_dir: Path | str = Path("data/highlights"),
    top_n: int = 5,
    clip_padding: float = 4.0,
    max_clip_duration: float = 45.0,
    source_video: Path | str | None = None,
) -> Path:
    transcript_path = Path(transcript_file)
    segments, source_audio = _load_transcript_segments(transcript_path)

    scored: list[dict[str, Any]] = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", 0.0))
        score = _segment_score(text)
        if score <= 0:
            continue
        scored.append({"start": start, "end": end, "text": text, "score": score})

    scored.sort(key=lambda s: s["score"], reverse=True)

    chosen: list[Highlight] = []
    for item in scored:
        if len(chosen) >= top_n:
            break

        raw_start = max(0.0, item["start"] - clip_padding)
        raw_end = item["end"] + clip_padding

        if raw_end - raw_start > max_clip_duration:
            raw_end = raw_start + max_clip_duration

        overlaps = any(not (raw_end <= h.start or raw_start >= h.end) for h in chosen)
        if overlaps:
            continue

        chosen.append(
            Highlight(
                rank=len(chosen) + 1,
                start=raw_start,
                end=raw_end,
                score=round(float(item["score"]), 3),
                text=item["text"],
            )
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    result = {
        "source_transcript": str(transcript_path),
        "source_audio": source_audio,
        "source_video": str(source_video) if source_video else None,
        "highlights": [h.__dict__ for h in chosen],
    }

    output_file = output_path / f"{transcript_path.stem}.highlights.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return output_file
