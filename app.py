import os
import sys
import tempfile
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from pipeline.transcriber import transcribe
from pipeline.translator import translate_segments, generate_srt, LANGUAGES
from pipeline.synthesizer import synthesize_segments
from pipeline.merger import merge_audio_video
from auth import init_db, register_user, login_user

# ── Init DB ───────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="VideoDubber — AI Dubbing",
    page_icon="🎬",
    layout="centered"
)

# ── Session state defaults ────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"   # "login" | "register"

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


# ══════════════════════════════════════════════════════════════════════════════
# ROUTE: not logged in → show auth
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    if st.session_state.auth_page == "login":
        show_login()
    else:
        show_register()
    st.stop()   # ← nothing below renders until user is logged in


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP  (only reached when logged_in = True)
# ══════════════════════════════════════════════════════════════════════════════
st.title("🎬 VideoDubber")
st.caption("AI-powered video dubbing — Kannada · Hindi · Tamil · Telugu · Malayalam · Bhojpuri · Gujarati")

# Logout button in top-right via sidebar
with st.sidebar:
    st.markdown(f"👤 **{st.session_state.user_name}**")
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_name = ""
        st.rerun()

    st.divider()
    st.header("⚙️ Settings")

    target_language = st.selectbox(
        "Target Language",
        list(LANGUAGES.keys()),
        index=0
    )

    voice_gender = st.radio(
        "Voice Gender",
        ["female", "male", "neutral"],
        index=0,
        help="Uses pitch shifting for gender effect"
    )

    enable_lipsync = st.checkbox(
        "Enable Lip Sync (D-ID)",
        value=False,
        help="Requires DID_API_KEY in .env — costs credits"
    )

    generate_subtitles = st.checkbox("Generate Subtitles (.srt)", value=True)

    st.divider()
    lang_info    = LANGUAGES[target_language]
    active_voice = lang_info["voices_female"][0] if voice_gender == "female" else lang_info["voices_male"][0]
    st.markdown(f"**Voice:** `{active_voice}`")
    st.markdown("**Pitch shift:** `-4` semitones (male) / `+4` (female)")


# ── Main upload area ──────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload a video file",
    type=["mp4", "mov", "avi", "mkv"],
    help="Upload the video you want to dub"
)

if uploaded_file:
    st.video(uploaded_file)

    if st.button("🚀 Start Dubbing", type="primary", use_container_width=True):

        lang_info    = LANGUAGES[target_language]
        voice_male   = lang_info["voices_male"][0]
        voice_female = lang_info["voices_female"][0]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(uploaded_file.read())
            video_path = tmp.name

        progress = st.progress(0, text="Starting...")
        status   = st.empty()

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
                srt_path = generate_srt(translated, "output/subtitles.srt")
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

            progress.progress(100, text="Done!")
            status.success("🎉 Dubbing complete!")

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

else:
    st.info("👆 Upload a video file to get started")
    st.markdown("""
    **How it works:**
    1. Upload your video
    2. Choose target language and voice gender
    3. Click **Start Dubbing**
    4. Download the dubbed video

    **Supported languages:** Kannada · Hindi · Tamil · Telugu · Malayalam · Bhojpuri · Gujarati
    """)
