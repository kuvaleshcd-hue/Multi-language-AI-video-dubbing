import os
from deep_translator import GoogleTranslator

# ElevenLabs Voice IDs
ELEVENLABS_MALE_VOICE   = "RwXLkVKnRloV1UPh3Ccx"
ELEVENLABS_FEMALE_VOICE = "RwXLkVKnRloV1UPh3Ccx"

LANGUAGES = {
    "Kannada": {
        "code": "kn",
        "voices_male":   ["kn-IN-GaganNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["kn-IN-SapnaNeural",     f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Hindi": {
        "code": "hi",
        "voices_male":   ["hi-IN-MadhurNeural",   f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["hi-IN-SwaraNeural",     f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Tamil": {
        "code": "ta",
        "voices_male":   ["ta-IN-ValluvarNeural",  f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["ta-IN-PallaviNeural",   f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Telugu": {
        "code": "te",
        "voices_male":   ["te-IN-MohanNeural",     f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["te-IN-ShrutiNeural",    f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Malayalam": {
        "code": "ml",
        "voices_male":   ["ml-IN-MidhunNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["ml-IN-SobhanaNeural",   f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Bhojpuri": {
        "code": "bho",
        "voices_male":   ["hi-IN-MadhurNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["hi-IN-SwaraNeural",     f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Gujarati": {
        "code": "gu",
        "voices_male":   ["gu-IN-NiranjanNeural",  f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["gu-IN-DhwaniNeural",    f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    # ── NEW INDIAN LANGUAGES ──────────────────────────────────────────────
    "Bengali": {
        "code": "bn",
        "voices_male":   ["bn-IN-BashkarNeural",   f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["bn-IN-TanishaaNeural",  f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Marathi": {
        "code": "mr",
        "voices_male":   ["mr-IN-ManoharNeural",   f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["mr-IN-AarohiNeural",    f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Punjabi": {
        "code": "pa",
        # No native Punjabi in Edge-TTS — Hindi fallback
        "voices_male":   ["hi-IN-MadhurNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["hi-IN-SwaraNeural",     f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Odia": {
        "code": "or",
        # No native Odia in Edge-TTS — Hindi fallback
        "voices_male":   ["hi-IN-MadhurNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["hi-IN-SwaraNeural",     f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Assamese": {
        "code": "as",
        # No native Assamese in Edge-TTS — Bengali fallback
        "voices_male":   ["bn-IN-BashkarNeural",   f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["bn-IN-TanishaaNeural",  f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Urdu": {
        "code": "ur",
        "voices_male":   ["ur-IN-SalmanNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["ur-IN-GulNeural",       f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Sanskrit": {
        "code": "sa",
        # No Edge-TTS Sanskrit voice — Hindi fallback
        "voices_male":   ["hi-IN-MadhurNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["hi-IN-SwaraNeural",     f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Maithili": {
        "code": "mai",
        # No Edge-TTS Maithili voice — Hindi fallback
        "voices_male":   ["hi-IN-MadhurNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["hi-IN-SwaraNeural",     f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Sindhi": {
        "code": "sd",
        # No Edge-TTS Sindhi voice — Urdu fallback
        "voices_male":   ["ur-IN-SalmanNeural",    f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["ur-IN-GulNeural",       f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
}

# Flat lookup: language name → Google Translate code (used by new tab)
ALL_INDIAN_LANGUAGES = {name: info["code"] for name, info in LANGUAGES.items()}


def translate_segments(segments, target_lang="kn", source_lang="auto"):
    """Translate segments. source_lang defaults to auto-detect."""
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    translated = []
    for seg in segments:
        try:
            translated_text = translator.translate(seg["text"])
        except Exception as e:
            print(f"Translation failed: {e}")
            translated_text = seg["text"]
        translated.append({
            "start":    seg["start"],
            "end":      seg["end"],
            "text":     translated_text,
            "original": seg["text"],
        })
    return translated


def generate_srt(segments, output_path="output/subtitles.srt"):
    def format_time(seconds):
        h  = int(seconds // 3600)
        m  = int((seconds % 3600) // 60)
        s  = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            f.write(f"{i+1}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(f"{seg['text']}\n\n")
    return output_path
