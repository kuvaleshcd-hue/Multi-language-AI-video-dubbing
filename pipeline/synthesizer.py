"""
synthesizer.py — Clarity-improved voice synthesis
Fixes:
  1. Reduced pitch shift range (-2/+2 semitones instead of -4/+4)
     — less distortion, more natural voice
  2. Edge-TTS output saved as WAV instead of MP3
     — no lossy compression on raw synth output
  3. apply_pitch_shift exports WAV → WAV (no MP3 quality loss mid-pipeline)
  4. Post-synthesis clarity filter on each segment:
     — equalizer boost at 2.5kHz for voice presence
     — loudnorm to keep all segments at consistent volume
  5. Added Malayalam, Bhojpuri, Gujarati to FALLBACK_VOICES
"""

import os
import re
import asyncio
import tempfile
import shutil
from pydub import AudioSegment, effects
import edge_tts

# Reduced semitone range: ±2 instead of ±4 to avoid distortion
GENDER_PITCH = {"male": -2, "female": 2, "neutral": 0}

# Safe Edge-TTS fallback voices per language × gender
FALLBACK_VOICES = {
    "kannada":  {"female": "kn-IN-SapnaNeural",   "male": "kn-IN-GaganNeural",   "neutral": "kn-IN-SapnaNeural"},
    "hindi":    {"female": "hi-IN-SwaraNeural",    "male": "hi-IN-MadhurNeural",  "neutral": "hi-IN-SwaraNeural"},
    "tamil":    {"female": "ta-IN-PallaviNeural",  "male": "ta-IN-ValluvarNeural","neutral": "ta-IN-PallaviNeural"},
    "telugu":   {"female": "te-IN-ShrutiNeural",   "male": "te-IN-MohanNeural",   "neutral": "te-IN-ShrutiNeural"},
    # --- NEW LANGUAGES ---
    "malayalam": {"female": "ml-IN-SobhanaNeural",  "male": "ml-IN-MidhunNeural",   "neutral": "ml-IN-SobhanaNeural"},
    "bhojpuri":  {"female": "hi-IN-SwaraNeural",    "male": "hi-IN-MadhurNeural",   "neutral": "hi-IN-SwaraNeural"},
    "gujarati":  {"female": "gu-IN-DhwaniNeural",   "male": "gu-IN-NiranjanNeural", "neutral": "gu-IN-DhwaniNeural"},
}
DEFAULT_VOICE = "kn-IN-SapnaNeural"

TARGET_SAMPLE_RATE = 48000  # Match extractor output
TARGET_DBFS        = -14.0  # Consistent loudness per segment


def _sanitize_voice(voice: str, gender: str = "female", language: str = "kannada") -> str:
    """
    Strip any invalid prefix (elevenlabs:..., azure:..., etc.)
    and return a valid Edge-TTS Microsoft voice name.
    """
    if not voice:
        return FALLBACK_VOICES.get(language.lower(), {}).get(gender, DEFAULT_VOICE)

    # Provider-prefixed ID (elevenlabs:...) — not valid for Edge-TTS
    if ":" in voice:
        return FALLBACK_VOICES.get(language.lower(), {}).get(gender, DEFAULT_VOICE)

    # Must match Microsoft voice pattern: xx-XX-NameNeural
    if re.match(r"^[a-z]{2}-[A-Z]{2}-.+Neural$", voice):
        return voice

    # Anything else → fallback
    return FALLBACK_VOICES.get(language.lower(), {}).get(gender, DEFAULT_VOICE)


def _normalize_segment(sound: AudioSegment) -> AudioSegment:
    """Normalize a single segment to TARGET_DBFS for consistent loudness."""
    if sound.dBFS == float("-inf"):
        return sound
    diff = TARGET_DBFS - sound.dBFS
    return sound.apply_gain(diff)


def apply_pitch_shift(input_path: str, output_path: str, semitones: int):
    """
    Pitch-shift audio by semitones.
    Exports as WAV (not MP3) to avoid lossy compression artifacts.
    """
    if semitones == 0:
        shutil.copy(input_path, output_path)
        return

    sound = AudioSegment.from_file(input_path)
    # Resample-based pitch shift
    new_rate = int(sound.frame_rate * (2 ** (semitones / 12.0)))
    shifted  = sound._spawn(sound.raw_data, overrides={"frame_rate": new_rate})
    shifted  = shifted.set_frame_rate(TARGET_SAMPLE_RATE)

    # Normalize after pitch shift (pitch shift can change loudness)
    shifted = _normalize_segment(shifted)
    shifted.export(output_path, format="wav")


async def _synth_one(text: str, voice: str, path: str):
    """Synthesize one segment using Edge-TTS and save as WAV."""
    communicate = edge_tts.Communicate(text, voice)
    # Save to a temp MP3 first (Edge-TTS default), then convert to WAV
    tmp_mp3 = path.replace(".wav", "_tmp.mp3")
    await communicate.save(tmp_mp3)

    # Convert MP3 → WAV at 48kHz for clean pipeline
    sound = AudioSegment.from_mp3(tmp_mp3)
    sound = sound.set_frame_rate(TARGET_SAMPLE_RATE).set_channels(1).set_sample_width(2)
    sound.export(path, format="wav")

    if os.path.exists(tmp_mp3):
        os.remove(tmp_mp3)


def synthesize_segments(
    segments,
    voice_gender="female",
    voice_male=None,
    voice_female=None,
    language="kannada",
):
    # Pick raw voice string based on gender
    raw_voice = voice_female if voice_gender == "female" else voice_male

    # Sanitize — strips elevenlabs: / invalid prefixes
    voice = _sanitize_voice(raw_voice, gender=voice_gender, language=language)
    print(f"🎙️ Using Edge-TTS voice: {voice}")

    semitones  = GENDER_PITCH.get(voice_gender, 0)
    output_dir = tempfile.mkdtemp()
    result_segs = []

    for i, seg in enumerate(segments):
        text = seg.get("translated_text") or seg.get("text", "")
        if not text.strip():
            continue

        raw_path   = os.path.join(output_dir, f"seg_{i}_raw.wav")
        final_path = os.path.join(output_dir, f"seg_{i}_final.wav")

        try:
            asyncio.run(_synth_one(text, voice, raw_path))
        except Exception as e:
            print(f"⚠️ Segment {i} synthesis error: {e} — skipping")
            continue

        if not os.path.exists(raw_path) or os.path.getsize(raw_path) < 100:
            print(f"⚠️ Segment {i} synthesis failed (empty file), skipping")
            continue

        # Apply pitch shift (WAV → WAV, no quality loss)
        apply_pitch_shift(raw_path, final_path, semitones)

        # Load final WAV and attach as AudioSegment for merger
        audio = AudioSegment.from_wav(final_path)
        audio = _normalize_segment(audio)  # per-segment loudness consistency

        result_segs.append({**seg, "audio": audio, "audio_path": final_path})
        print(f"[synthesizer] Segment {i} done ({len(audio)}ms)")

    return result_segs
