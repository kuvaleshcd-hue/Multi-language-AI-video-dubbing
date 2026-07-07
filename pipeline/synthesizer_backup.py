import os
import subprocess
import shutil
from elevenlabs.client import ElevenLabs
from pedalboard import Pedalboard, PitchShift
from pedalboard.io import AudioFile
from pydub import AudioSegment

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

ELEVENLABS_VOICES = {
    "ELEVENLABS_MALE_VOICE":   "pNInz6obpgDQGcFmaJgB",
    "ELEVENLABS_FEMALE_VOICE": "21m00Tcm4TlvDq8ikWAM",
}

GENDER_PITCH = {"male": -4, "female": +4, "neutral": 0}


def apply_pitch_shift(input_path, output_path, semitones):
    if semitones == 0:
        shutil.copy(input_path, output_path)
        return
    board = Pedalboard([PitchShift(semitones=semitones)])
    with AudioFile(input_path) as f:
        audio = f.read(f.frames)
        sr = f.samplerate
    effected = board(audio, sr)
    with AudioFile(output_path, 'w', sr, effected.shape[0]) as f:
        f.write(effected)


def synthesize_segments(segments, voice_gender, voice_male, voice_female):
    selected_voice = voice_male if voice_gender == "male" else voice_female
    pitch_shift = GENDER_PITCH.get(voice_gender, 0)

    for i, seg in enumerate(segments):
        raw_filename    = f"/tmp/raw_{i}.mp3"
        output_filename = f"/tmp/out_{i}.mp3"
        tts_ok = False

        if selected_voice in ELEVENLABS_VOICES:
            try:
                gen = client.text_to_speech.convert(
                    text=seg['text'],
                    voice_id=ELEVENLABS_VOICES[selected_voice],
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )
                with open(raw_filename, "wb") as f_out:
                    for chunk in gen:
                        if chunk:
                            f_out.write(chunk)
                tts_ok = os.path.exists(raw_filename) and os.path.getsize(raw_filename) > 0
            except Exception as e:
                print(f"[synth] ElevenLabs error seg {i}: {e}")
        else:
            try:
                subprocess.run(
                    ["edge-tts", "--text", seg['text'], "--voice", selected_voice, "--write-media", raw_filename],
                    check=True, capture_output=True
                )
                tts_ok = os.path.exists(raw_filename) and os.path.getsize(raw_filename) > 0
            except Exception as e:
                print(f"[synth] Edge-TTS error seg {i}: {e}")

        if not tts_ok:
            dur = int((seg.get("end", seg["start"] + 1) - seg["start"]) * 1000)
            seg["audio"] = AudioSegment.silent(duration=max(dur, 100))
            print(f"[synth] Seg {i}: TTS failed → silence")
            continue

        try:
            apply_pitch_shift(raw_filename, output_filename, pitch_shift)
            audio_file = output_filename
        except Exception as e:
            print(f"[synth] Pitch shift failed seg {i}: {e}")
            audio_file = raw_filename

        try:
            seg["audio"] = AudioSegment.from_file(audio_file)
            print(f"[synth] Seg {i}: {len(seg['audio'])}ms loaded ✅")
        except Exception as e:
            dur = int((seg.get("end", seg["start"] + 1) - seg["start"]) * 1000)
            seg["audio"] = AudioSegment.silent(duration=max(dur, 100))
            print(f"[synth] Seg {i}: load failed → silence ({e})")

        for f in [raw_filename, output_filename]:
            if os.path.exists(f):
                os.remove(f)

    return segments
