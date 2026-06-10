# 🎬 video-dubber-v4

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![OpenAI Whisper](https://img.shields.io/badge/Whisper-412991?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> **AI-powered video dubbing system that transcribes, translates, and re-voices video content into Kannada using Whisper, gTTS, and MoviePy.**

## ✨ Features
- 🎙️ **Auto Transcription** — Extracts speech from any video using OpenAI Whisper
- 🌐 **AI Translation** — Translates English audio to Kannada using deep-translator
- 🔊 **Voice Synthesis** — Generates natural Kannada speech using gTTS
- 🎞️ **Video Merging** — Merges dubbed audio back into the original video with MoviePy
- 🔐 **User Authentication** — Secure login system with session management
- 🖥️ **Streamlit UI** — Clean web interface, no CLI required

## 🏗️ Architecture
```
Video Input → [extractor] → [transcriber] → [translator] → [synthesizer] → [merger] → Dubbed Video 🎬
```

## ⚙️ Installation
```bash
git clone https://github.com/kuvaleshcd-hue/video-dubber-v4-.git
cd video-dubber-v4-
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🚀 Usage
```bash
streamlit run app.py
```

## 🛠️ Tech Stack
| Component | Technology |
|---|---|
| Speech Recognition | OpenAI Whisper |
| Translation | deep-translator |
| Text-to-Speech | gTTS |
| Video Processing | MoviePy |
| Web Interface | Streamlit |

## 👨‍💻 Author
**Kuvalesh** — [@kuvaleshcd-hue](https://github.com/kuvaleshcd-hue)

## 📄 License
MIT License