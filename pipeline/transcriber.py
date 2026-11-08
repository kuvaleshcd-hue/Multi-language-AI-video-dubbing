"""
transcriber.py — Restored to base Whisper model
The 'small' model was creating too many segment boundaries causing 17 silence gaps.
Base model creates fewer, cleaner segments = less silence gaps.
"""

import whisper
from typing import Callable, Optional

_model = None


def _get_model():
    global _model
    if _model is None:
        print("[transcriber] Loading Whisper base model...")
        _model = whisper.load_model("base")
    return _model


def transcribe(audio_path: str) -> list:
    """
    Transcribe audio and return all segments at once.
    Use transcribe_streaming() if you want a per-segment callback.
    """
    model = _get_model()
    print(f"[transcriber] Transcribing {audio_path}...")
    result = model.transcribe(
        audio_path,
        task="transcribe",
        verbose=False,
        condition_on_previous_text=True,
        no_speech_threshold=0.6,
    )

    segments = []
    for seg in result.get("segments", []):
        text  = seg.get("text", "").strip()
        start = float(seg.get("start", 0))
        end   = float(seg.get("end", 0))

        if not text or (end - start) < 0.3:
            continue
        if end <= start:
            end = start + 1.0

        segments.append({
            "start": round(start, 3),
            "end":   round(end, 3),
            "text":  text,
        })

    print(f"[transcriber] Got {len(segments)} segments")
    return segments


def transcribe_streaming(
    audio_path: str,
    on_segment: Optional[Callable[[dict, int, int], None]] = None,
) -> list:
    """
    Transcribe audio, then fire on_segment(segment, index, total) for each
    accepted segment in order. This gives callers a rolling-reveal effect even
    though Whisper processes the full file internally.

    Args:
        audio_path:  Path to the audio / video file.
        on_segment:  Callback(segment_dict, index, total).
                     Called once per segment after the full transcription
                     result is available; index is 0-based.

    Returns:
        List of segment dicts (same format as transcribe()).
    """
    segments = transcribe(audio_path)   # run Whisper once, get everything
    total    = len(segments)

    if on_segment:
        for idx, seg in enumerate(segments):
            on_segment(seg, idx, total)

    return segments
