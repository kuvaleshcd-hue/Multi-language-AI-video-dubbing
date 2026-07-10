import os
import sys
import json
import time
import subprocess
import tempfile
import datetime
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.transcriber import transcribe
from pipeline.translator import translate_segments, generate_srt, LANGUAGES
from pipeline.synthesizer import synthesize_segments
from pipeline.merger import merge_audio_video
from auth import init_db, register_user, login_user

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="VideoDubber — AI Dubbing",
    page_icon="🎬",
    layout="centered"
)

HISTORY_FILE = "dub_history.json"

# ── Session state defaults ────────────────────────────────────────────────────
defaults = {
    "logged_in":       False,
    "user_name":       "",
    "auth_page":       "login",
    "adv_speed":       1.0,
    "adv_pitch_extra": 0,
    "adv_volume":      0,
    "adv_bitrate":     "192k",
    "adv_noise":       False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGES
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    st.markdown("<h2 style='text-align:center'>🎬 VideoDubber</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#666'>AI-powered multilingual video dubbing</p>", unsafe_allow_html=True)
    st.divider()

    with st.form("login_form"):
        st.subheader("Login")
        email    = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submit   = st.form_submit_button("Login", use_container_width=True, type="primary")

    if submit:
        if not email or not password:
            st.error("Please fill in both fields.")
        else:
            success, name, msg = login_user(email, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.user_name = name
                st.success(f"Welcome back, {name}! 🎉")
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")
    st.markdown("<p style='text-align:center'>Don't have an account?</p>", unsafe_allow_html=True)
    if st.button("Create an account →", use_container_width=True):
        st.session_state.auth_page = "register"
        st.rerun()


def show_register():
    st.markdown("<h2 style='text-align:center'>🎬 VideoDubber</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#666'>Create your free account</p>", unsafe_allow_html=True)
    st.divider()

    with st.form("register_form"):
        st.subheader("Register")
        full_name = st.text_input("Full Name", placeholder="Kuvalesh")
        email     = st.text_input("Email", placeholder="you@example.com")
        password  = st.text_input("Password", type="password", placeholder="Min 6 characters")
        confirm   = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
        submit    = st.form_submit_button("Create Account", use_container_width=True, type="primary")

    if submit:
        if not full_name or not email or not password or not confirm:
            st.error("All fields are required.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            success, msg = register_user(full_name, email, password)
            if success:
                st.success("Account created! Please log in.")
                st.session_state.auth_page = "login"
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")
    st.markdown("<p style='text-align:center'>Already have an account?</p>", unsafe_allow_html=True)
    if st.button("← Back to Login", use_container_width=True):
        st.session_state.auth_page = "login"
        st.rerun()


# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    if st.session_state.auth_page == "login":
        show_login()
    else:
        show_register()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(entry: dict):
    history = load_history()
    history.insert(0, entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[:50], f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# SHARED DUBBING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
def run_dubbing_pipeline(video_path: str, source_label: str = "upload"):
    """Transcribe → Translate → Synthesize → Merge. Uses sidebar + advanced settings."""
    lang_info    = LANGUAGES[target_language]
    voice_male   = lang_info["voices_male"][0]
    voice_female = lang_info["voices_female"][0]

    progress   = st.progress(0, text="Starting...")
    status     = st.empty()
    start_time = time.time()

    try:
        status.info("🎙️ Transcribing audio with Whisper...")
        progress.progress(10, text="Transcribing...")
        segments = transcribe(video_path)
        st.success(f"✅ Transcribed {len(segments)} segments")

        status.info(f"🌐 Translating to {target_language}...")
        progress.progress(30, text="Translating...")
        translated = translate_segments(segments, target_lang=lang_info["code"])
        st.success(f"✅ Translated to {target_language}")

        active_voice_label = voice_female if voice_gender == "female" else voice_male
        status.info(f"🔊 Synthesizing {voice_gender} voice ({active_voice_label})...")
        progress.progress(50, text="Synthesizing audio...")
        synthesized = synthesize_segments(
            translated,
            voice_gender=voice_gender,
            voice_male=voice_male,
            voice_female=voice_female,
            language=target_language.lower()
        )
        st.success("✅ Audio synthesized with gender pitch shift")

        if generate_subtitles:
            status.info("📝 Generating subtitles...")
            progress.progress(65, text="Generating subtitles...")
            os.makedirs("output", exist_ok=True)
            generate_srt(translated, "output/subtitles.srt")
            st.success("✅ Subtitles generated")

        status.info("🎞️ Merging audio and video...")
        progress.progress(75, text="Merging...")
        output_path = merge_audio_video(video_path, synthesized)
        st.success("✅ Audio merged with video")

        if enable_lipsync:
            status.info("💋 Running lip sync via D-ID...")
            progress.progress(85, text="Lip syncing...")
            try:
                from pipeline.lipsync import lipsync_video
                lipsync_out = "output/lipsync_final.mp4"
                output_path = lipsync_video(output_path, output_path, lipsync_out)
                st.success("✅ Lip sync complete")
            except Exception as e:
                st.warning(f"⚠️ Lip sync failed: {e}. Using dubbed video without lip sync.")

        elapsed = round(time.time() - start_time, 1)
        progress.progress(100, text="Done!")
        status.success(f"🎉 Dubbing complete in {elapsed}s!")

        save_history({
            "timestamp":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source":     source_label,
            "language":   target_language,
            "gender":     voice_gender,
            "segments":   len(segments),
            "elapsed_s":  elapsed,
            "output":     output_path,
        })

        st.divider()
        st.subheader("🎬 Dubbed Video")
        st.video(output_path)

        with open(output_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Dubbed Video",
                data=f,
                file_name=f"dubbed_{target_language.lower()}_{voice_gender}.mp4",
                mime="video/mp4",
                use_container_width=True
            )

        if generate_subtitles and os.path.exists("output/subtitles.srt"):
            with open("output/subtitles.srt", "r") as f:
                st.download_button(
                    label="⬇️ Download Subtitles (.srt)",
                    data=f,
                    file_name=f"subtitles_{target_language.lower()}.srt",
                    mime="text/plain",
                    use_container_width=True
                )

    except Exception as e:
        status.error(f"❌ Error: {e}")
        st.exception(e)

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


# ══════════════════════════════════════════════════════════════════════════════
# YOUTUBE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def download_youtube_video(url: str) -> str:
    tmp_path   = tempfile.mktemp(suffix=".mp4")
    base_flags = [
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", tmp_path,
        "--no-playlist", "--no-warnings",
        "--extractor-retries", "3",
    ]

    def _run(extra):
        return subprocess.run(["yt-dlp"] + extra + base_flags + [url],
                              capture_output=True, text=True)

    result = _run(["--cookies-from-browser", "chrome"])
    if result.returncode != 0:
        result = _run([])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "yt-dlp failed.")

    if not os.path.exists(tmp_path):
        alt = tmp_path + ".mp4"
        if os.path.exists(alt):
            return alt
        raise FileNotFoundError("Downloaded file not found. URL may be private or age-restricted.")
    return tmp_path


def extract_video_id(url: str):
    import re
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
st.title("🎬 VideoDubber")
st.caption("AI-powered video dubbing — Kannada · Hindi · Tamil · Telugu · Malayalam · Bhojpuri · Gujarati")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"👤 **{st.session_state.user_name}**")
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_name = ""
        st.rerun()

    st.divider()
    st.header("⚙️ Settings")

    target_language = st.selectbox("Target Language", list(LANGUAGES.keys()), index=0)

    voice_gender = st.radio(
        "Voice Gender", ["female", "male", "neutral"], index=0,
        help="Uses pitch shifting for gender effect"
    )

    enable_lipsync = st.checkbox(
        "Enable Lip Sync (D-ID)", value=False,
        help="Requires DID_API_KEY in .env — costs credits"
    )

    generate_subtitles = st.checkbox("Generate Subtitles (.srt)", value=True)

    st.divider()
    lang_info    = LANGUAGES[target_language]
    active_voice = lang_info["voices_female"][0] if voice_gender == "female" else lang_info["voices_male"][0]
    st.markdown(f"**Voice:** `{active_voice}`")
    st.markdown("**Pitch shift:** `-4` semitones (male) / `+4` (female)")

    # Show active advanced overrides
    adv = st.session_state
    if adv.adv_speed != 1.0 or adv.adv_pitch_extra != 0 or adv.adv_volume != 0 or adv.adv_noise:
        st.divider()
        st.caption("🔧 **Advanced overrides active**")
        if adv.adv_speed != 1.0:       st.caption(f"Speed: {adv.adv_speed}x")
        if adv.adv_pitch_extra != 0:   st.caption(f"Extra pitch: {adv.adv_pitch_extra:+d} st")
        if adv.adv_volume != 0:        st.caption(f"Volume: {adv.adv_volume:+d} dB")
        if adv.adv_noise:              st.caption("Noise reduction: On")


# ── Five Tabs ─────────────────────────────────────────────────────────────────
tab_upload, tab_youtube, tab_batch, tab_history, tab_advanced = st.tabs([
    "📁 Upload Video",
    "▶️ YouTube URL",
    "📂 Batch Dub",
    "📊 History",
    "⚙️ Advanced",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — FILE UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload a video file",
        type=["mp4", "mov", "avi", "mkv"],
        help="Upload the video you want to dub"
    )

    if uploaded_file:
        st.video(uploaded_file)
        if st.button("🚀 Start Dubbing", key="btn_upload", type="primary", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(uploaded_file.read())
                video_path = tmp.name
            run_dubbing_pipeline(video_path, source_label=f"upload:{uploaded_file.name}")
    else:
        st.info("👆 Upload a video file to get started")
        st.markdown("""
**How it works:**
1. Upload your video
2. Choose target language & voice gender in the sidebar
3. Click **Start Dubbing**
4. Download the dubbed video

**Supported formats:** MP4 · MOV · AVI · MKV
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — YOUTUBE URL
# ══════════════════════════════════════════════════════════════════════════════
with tab_youtube:
    st.markdown("### 🎥 Dub a YouTube Video")
    st.markdown("Paste any **public** YouTube URL — downloaded and dubbed automatically.")

    yt_url    = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Supports youtube.com/watch, youtu.be, and /shorts/"
    )
    is_valid  = yt_url and ("youtube.com" in yt_url or "youtu.be" in yt_url)

    if is_valid:
        vid_id = extract_video_id(yt_url)
        if vid_id:
            col_thumb, col_info = st.columns([1, 2])
            with col_thumb:
                st.image(f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg",
                         use_container_width=True)
            with col_info:
                st.markdown("**✅ Valid YouTube URL detected**")
                st.caption(f"Video ID: `{vid_id}`")
                st.caption("⚠️ Long videos take more time to process.")
                st.caption("🔒 Private / age-restricted videos not supported.")
        else:
            st.warning("⚠️ Could not parse video ID. Please check the URL.")

        st.divider()
        if st.button("⬇️ Download & Dub", key="btn_youtube", type="primary", use_container_width=True):
            with st.spinner("Downloading from YouTube…"):
                try:
                    video_path = download_youtube_video(yt_url)
                except Exception as e:
                    st.error(f"❌ Download failed: {e}")
                    st.stop()
            st.success("✅ Downloaded! Starting pipeline…")
            run_dubbing_pipeline(video_path, source_label=f"youtube:{yt_url}")
    else:
        st.info("👆 Paste a YouTube URL above to get started")
        st.markdown("""
**Supported URL formats:**
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`

**Tips:**
- Keep videos under 10 minutes for faster processing
- Only public / unlisted videos are supported
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — BATCH DUB
# ══════════════════════════════════════════════════════════════════════════════
with tab_batch:
    st.markdown("### 📂 Batch Dub Multiple Videos")
    st.markdown("Upload up to **5 videos** — each will be dubbed with the same language and voice settings.")

    batch_files = st.file_uploader(
        "Upload multiple videos",
        type=["mp4", "mov", "avi", "mkv"],
        accept_multiple_files=True,
        help="Hold Cmd / Ctrl to select multiple files",
        key="batch_uploader"
    )

    if batch_files:
        if len(batch_files) > 5:
            st.warning("⚠️ Max 5 videos at a time. Only the first 5 will be processed.")
            batch_files = batch_files[:5]

        st.markdown(f"**{len(batch_files)} video(s) queued:**")
        for i, f in enumerate(batch_files, 1):
            st.caption(f"{i}. {f.name}  ({round(f.size/1024/1024, 1)} MB)")

        if st.button(f"🚀 Dub All {len(batch_files)} Videos", key="btn_batch",
                     type="primary", use_container_width=True):

            overall  = st.progress(0, text="Starting batch…")
            results  = []

            for idx, upload in enumerate(batch_files):
                st.markdown(f"---\n**[{idx+1}/{len(batch_files)}] `{upload.name}`**")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp.write(upload.read())
                    video_path = tmp.name

                lang_info    = LANGUAGES[target_language]
                voice_male   = lang_info["voices_male"][0]
                voice_female = lang_info["voices_female"][0]
                bar          = st.progress(0, text=f"Processing {upload.name}…")
                stat         = st.empty()

                try:
                    stat.info("🎙️ Transcribing…"); bar.progress(20)
                    segments   = transcribe(video_path)

                    stat.info("🌐 Translating…"); bar.progress(40)
                    translated = translate_segments(segments, target_lang=lang_info["code"])

                    stat.info("🔊 Synthesizing…"); bar.progress(60)
                    synthesized = synthesize_segments(
                        translated,
                        voice_gender=voice_gender,
                        voice_male=voice_male,
                        voice_female=voice_female,
                        language=target_language.lower()
                    )

                    stat.info("🎞️ Merging…"); bar.progress(80)
                    output_path = merge_audio_video(video_path, synthesized)

                    bar.progress(100, text="Done!")
                    stat.success(f"✅ {upload.name} complete!")
                    results.append((upload.name, output_path, None))

                    save_history({
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source":    f"batch:{upload.name}",
                        "language":  target_language,
                        "gender":    voice_gender,
                        "segments":  len(segments),
                        "elapsed_s": 0,
                        "output":    output_path,
                    })

                except Exception as e:
                    stat.error(f"❌ {upload.name} failed: {e}")
                    results.append((upload.name, None, str(e)))

                finally:
                    if os.path.exists(video_path):
                        os.remove(video_path)

                overall.progress(
                    int((idx + 1) / len(batch_files) * 100),
                    text=f"Completed {idx+1}/{len(batch_files)}"
                )

            # Download results
            st.divider()
            st.subheader("📦 Batch Results")
            for name, out_path, err in results:
                if out_path and os.path.exists(out_path):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.success(f"✅ {name}")
                    with col_b:
                        with open(out_path, "rb") as f:
                            st.download_button(
                                "⬇️ Download", data=f,
                                file_name=f"dubbed_{name}",
                                mime="video/mp4",
                                key=f"dl_batch_{name}"
                            )
                else:
                    st.error(f"❌ {name}: {err}")
    else:
        st.info("👆 Upload multiple video files above to get started")
        st.markdown("""
**Tips:**
- Hold **Cmd** (Mac) or **Ctrl** (Windows) to select multiple files
- All videos use the same language & voice from the sidebar
- Results appear one by one as each finishes
- Max 5 videos per batch to avoid timeouts
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown("### 📊 Dubbing History")

    history = load_history()

    if history:
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.caption(f"{len(history)} job(s) recorded")
        with col_b:
            if st.button("🗑️ Clear All", key="clear_history"):
                if os.path.exists(HISTORY_FILE):
                    os.remove(HISTORY_FILE)
                st.rerun()

        st.divider()

        for i, entry in enumerate(history):
            source_short = entry.get("source", "—").split(":")[0]
            label = (
                f"🎬  {entry.get('timestamp', '—')}  —  "
                f"{entry.get('language', '?')} · "
                f"{entry.get('gender', '?')} · "
                f"{source_short}"
            )
            with st.expander(label, expanded=(i == 0)):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Language",  entry.get("language", "—"))
                c2.metric("Voice",     entry.get("gender", "—").capitalize())
                c3.metric("Segments",  entry.get("segments", "—"))
                c4.metric("Time",      f"{entry.get('elapsed_s', '—')}s")

                src_full = entry.get("source", "—")
                if ":" in src_full:
                    st.caption(f"Source detail: `{src_full.split(':',1)[1]}`")

                out = entry.get("output", "")
                if out and os.path.exists(out):
                    with open(out, "rb") as f:
                        st.download_button(
                            "⬇️ Re-download output",
                            data=f,
                            file_name=f"dubbed_{entry.get('language','')}.mp4",
                            mime="video/mp4",
                            key=f"hist_dl_{i}"
                        )
                else:
                    st.caption("⚠️ Output file no longer on disk (temp files are deleted on restart)")
    else:
        st.info("No dubbing jobs yet. Run a dub from any tab and it will appear here automatically.")
        st.markdown("""
**What gets tracked:**
- Timestamp of each job
- Source (upload / YouTube / batch)
- Target language & voice gender
- Number of segments transcribed
- Total processing time
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — ADVANCED SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_advanced:
    st.markdown("### ⚙️ Advanced Audio Settings")
    st.markdown("Fine-tune the dubbed output. **Save** to apply changes to all future dubs.")

    st.subheader("🔊 Voice")

    adv_speed = st.slider(
        "Speech Speed",
        min_value=0.5, max_value=2.0,
        value=float(st.session_state.adv_speed),
        step=0.05,
        help="1.0 = normal. < 1.0 slows down, > 1.0 speeds up the dubbed voice."
    )

    adv_pitch_extra = st.slider(
        "Extra Pitch Shift (semitones)",
        min_value=-12, max_value=12,
        value=int(st.session_state.adv_pitch_extra),
        step=1,
        help="Added on top of the base gender pitch shift (±4 st). 0 = no extra shift."
    )

    adv_volume = st.slider(
        "Volume Boost (dB)",
        min_value=-10, max_value=10,
        value=int(st.session_state.adv_volume),
        step=1,
        help="0 = unchanged. Positive = louder, negative = quieter."
    )

    st.subheader("🎚️ Export Quality")

    bitrate_options = ["96k", "128k", "192k", "256k", "320k"]
    adv_bitrate = st.selectbox(
        "Audio Bitrate",
        bitrate_options,
        index=bitrate_options.index(st.session_state.adv_bitrate),
        help="Higher bitrate = better quality, larger file size. 192k is a good default."
    )

    st.subheader("🧹 Noise Reduction")

    adv_noise = st.checkbox(
        "Enable Noise Reduction (ffmpeg `afftdn` filter)",
        value=bool(st.session_state.adv_noise),
        help="Removes background hiss/noise from the dubbed audio during merge."
    )

    st.divider()

    col_save, col_reset = st.columns(2)

    with col_save:
        if st.button("💾 Save Settings", key="adv_save", type="primary", use_container_width=True):
            st.session_state.adv_speed       = adv_speed
            st.session_state.adv_pitch_extra = adv_pitch_extra
            st.session_state.adv_volume      = adv_volume
            st.session_state.adv_bitrate     = adv_bitrate
            st.session_state.adv_noise       = adv_noise
            st.success("✅ Settings saved! Applied to all future dubs.")

    with col_reset:
        if st.button("🔄 Reset to Defaults", key="adv_reset", use_container_width=True):
            st.session_state.adv_speed       = 1.0
            st.session_state.adv_pitch_extra = 0
            st.session_state.adv_volume      = 0
            st.session_state.adv_bitrate     = "192k"
            st.session_state.adv_noise       = False
            st.success("✅ Reset to defaults.")
            st.rerun()

    st.divider()
    st.subheader("📋 Current Settings")
    st.markdown(f"""
| Setting | Value |
|---|---|
| Speech Speed | `{adv_speed}x` |
| Extra Pitch Shift | `{adv_pitch_extra:+d} semitones` |
| Volume Boost | `{adv_volume:+d} dB` |
| Audio Bitrate | `{adv_bitrate}` |
| Noise Reduction | `{"On ✅" if adv_noise else "Off"}` |
    """)

    st.caption(
        "ℹ️ Speed and extra pitch are passed to the synthesizer. "
        "Volume boost and noise reduction are applied at the ffmpeg merge stage via audio filters."
    )
