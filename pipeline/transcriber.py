"""
transcriber.py — Restored to base Whisper model
The 'small' model was creating too many segment boundaries causing 17 silence gaps.
Base model creates fewer, cleaner segments = less silence gaps.
"""

import whisper

_model = None


def _get_model():
    global _model
    if _model is None:
        print("[transcriber] Loading Whisper base model...")
        _model = whisper.load_model("base")
    return _model


def transcribe(audio_path: str) -> list:
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
