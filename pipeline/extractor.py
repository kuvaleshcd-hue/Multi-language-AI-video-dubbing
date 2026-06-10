"""
extractor.py — Clarity-improved audio extraction
Fixes:
  1. Raised sample rate to 48000Hz (broadcast standard, cleaner Whisper input)
  2. Replaced basic highpass/lowpass with a proper clarity filter chain:
     - afftdn: AI-based noise reduction
     - equalizer: boosts voice presence (2kHz–4kHz range)
     - compand: dynamic compression for consistent loudness
  3. Kept mono output for Whisper accuracy
"""

import subprocess
import tempfile
import os


def extract_audio(video_path: str) -> str:
    """
    Extract audio from video as a clean 48000Hz mono WAV with clarity filters.
    Returns path to the WAV file.
    """
    out_path = tempfile.mktemp(suffix="_extracted.wav")

    # Clarity filter chain:
    # 1. afftdn       — AI noise reduction (removes hiss, hum, background)
    # 2. highpass     — removes low-frequency rumble below 80Hz
    # 3. equalizer    — boosts voice clarity band (2500Hz, +3dB, wide Q)
    # 4. compand      — compressor to even out loud/quiet parts
    # 5. loudnorm     — normalize to broadcast loudness (EBU R128, -16 LUFS)
    clarity_filter = (
        "afftdn=nf=-25,"
        "highpass=f=80,"
        "equalizer=f=2500:t=q:w=1.5:g=3,"
        "compand=attacks=0.02:decays=0.15:points=-80/-80|-45/-35|-27/-25|0/-10:gain=3,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                      # no video
        "-acodec", "pcm_s16le",     # uncompressed PCM
        "-ar", "48000",             # 48kHz — broadcast standard
        "-ac", "1",                 # mono (best for Whisper)
        "-af", clarity_filter,
        out_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed:\n{result.stderr[-1000:]}")

    print(f"[extractor] Audio extracted → {out_path}")
    return out_path
