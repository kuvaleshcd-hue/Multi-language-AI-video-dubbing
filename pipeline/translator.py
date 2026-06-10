import os  # Added to handle directory creation
from deep_translator import GoogleTranslator

# ElevenLabs Voice IDs
ELEVENLABS_MALE_VOICE   = "RwXLkVKnRloV1UPh3Ccx"
ELEVENLABS_FEMALE_VOICE = "RwXLkVKnRloV1UPh3Ccx"

LANGUAGES = {
    "Kannada": {
        "code": "kn",
        "voices_male":   ["kn-IN-GaganNeural", f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["kn-IN-SapnaNeural",  f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Hindi": {
        "code": "hi",
        "voices_male":   ["hi-IN-MadhurNeural", f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["hi-IN-SwaraNeural",   f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Tamil": {
        "code": "ta",
        "voices_male":   ["ta-IN-ValluvarNeural", f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["ta-IN-PallaviNeural",  f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Telugu": {
        "code": "te",
        "voices_male":   ["te-IN-MohanNeural", f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["te-IN-ShrutiNeural", f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    # --- NEW LANGUAGES ADDED ---
    "Malayalam": {
        "code": "ml",
        "voices_male":   ["ml-IN-MidhunNeural",  f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["ml-IN-SobhanaNeural",  f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Bhojpuri": {
        "code": "bho",
        # No native Bhojpuri voices in Edge-TTS — Hindi voices used as fallback
        "voices_male":   ["hi-IN-MadhurNeural",  f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["hi-IN-SwaraNeural",    f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    "Gujarati": {
        "code": "gu",
        "voices_male":   ["gu-IN-NiranjanNeural", f"elevenlabs:{ELEVENLABS_MALE_VOICE}"],
        "voices_female": ["gu-IN-DhwaniNeural",   f"elevenlabs:{ELEVENLABS_FEMALE_VOICE}"],
    },
    # ---------------------------
}

def translate_segments(segments, target_lang="kn"):
    translator = GoogleTranslator(source="auto", target=target_lang)
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

    # --- FIX: Create output directory if it doesn't exist ---
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # --------------------------------------------------------

    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            f.write(f"{i+1}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(f"{seg['text']}\n\n")
    return output_path
