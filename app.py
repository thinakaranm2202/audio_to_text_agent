"""Streamlit user interface for a2t AI."""
from __future__ import annotations
import os
import json
import uuid
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import re
import streamlit as st
from dotenv import load_dotenv
from agents.coordinator import CoordinatorAgent

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)
HISTORY_FILE = OUTPUTS / "history.json"


def load_history() -> list[dict]:
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []
    except (OSError, json.JSONDecodeError):
        return []


def build_report_archive(records: list[dict]) -> bytes:
    """Bundle report files while keeping each recording's files in its own folder."""
    archive_buffer = io.BytesIO()
    output_root = OUTPUTS.resolve()
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, record in enumerate(records, 1):
            safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(record.get("filename", "recording")).stem).strip("._") or f"recording_{index}"
            for report_path in record.get("reports", {}).values():
                path = Path(report_path)
                try:
                    path.resolve().relative_to(output_root)
                except (OSError, ValueError):
                    continue
                if path.is_file():
                    archive.write(path, arcname=f"{index:02d}_{safe_stem}/{path.name}")
    return archive_buffer.getvalue()


def has_saved_reports(records: list[dict]) -> bool:
    output_root = OUTPUTS.resolve()
    for record in records:
        for report_path in record.get("reports", {}).values():
            path = Path(report_path)
            try:
                path.resolve().relative_to(output_root)
            except (OSError, ValueError):
                continue
            if path.is_file():
                return True
    return False


st.set_page_config(page_title="a2t AI | Audio to Text AI Agent", page_icon="🎙️", layout="wide")
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "selected_history_id" not in st.session_state:
    st.session_state.selected_history_id = None
animate_intro = not st.session_state.get("intro_animation_seen", False)
st.session_state.intro_animation_seen = True
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:#000000; color:#f4f0f4;}
[data-testid="stHeader"] {background:#000000;}
[data-testid="stSidebar"] {background:#090709; border-right:1px solid #34202a;}
[data-testid="stSidebar"] * {color:#f1eaf0;}
.hero {background:#0b090a; border:1px solid #38212b; border-radius:14px; padding:.8rem 1.1rem; margin:.15rem 0 1rem; color:white;}
.hero.hero-appear {animation: soft-appear 420ms cubic-bezier(.23,1,.32,1) both;}
.hero-top {display:flex; align-items:center; gap:1rem;}
.hero-icon {font-size:1.8rem; line-height:1;}
.hero h1 {font-size:1.35rem; letter-spacing:-.025em; margin:0; color:#fff; font-weight:700;}
.hero p {color:#c7bdc3; font-size:.88rem; font-style:italic; margin:.1rem 0 0;}
.ready {margin-left:auto; border:1px solid #4a303a; border-radius:20px; padding:.35rem .65rem; color:#eee; font-size:.8rem; white-space:nowrap;}
div.stButton > button, div.stDownloadButton > button {background:#aa13c2; color:white; border:1px solid #aa13c2; border-radius:10px; font-weight:700;}
div.stButton > button[kind="primary"] {min-height:2.8rem;}
div.stButton > button:hover, div.stDownloadButton > button:hover {background:#bd2bd0; border-color:#bd2bd0; color:white;}
div.stButton > button:active, div.stDownloadButton > button:active {animation: touch-bobble 260ms cubic-bezier(.34,1.56,.64,1);}
[data-testid="stFileUploader"] {background:#0d0b0c; border:1px solid #38212b; border-radius:12px; padding:.45rem;}
[data-testid="stFileUploader"] section {background:#0d0b0c;}
[data-testid="stPopover"] button {border-color:#49313b;}
.stAlert {background:#100d0f;}
.brand-small {font-size:1.05rem; font-weight:800; letter-spacing:-.03em; color:#f4eaf0; padding:.2rem 0 .7rem;}
@keyframes soft-appear {from {opacity:0; transform:translateY(8px);} to {opacity:1; transform:translateY(0);}}
@keyframes touch-bobble {0% {transform:scale(1);} 35% {transform:scale(1.06) rotate(-1deg);} 70% {transform:scale(.96) rotate(1deg);} 100% {transform:scale(1) rotate(0);}}
.a2t-tap-blink {position:fixed; width:24px; height:24px; margin:-12px 0 0 -12px; border:2px solid #aa13c2; border-radius:50%; background:rgba(170,19,194,.24); box-shadow:0 0 14px rgba(170,19,194,.55); pointer-events:none; z-index:2147483647; animation:tap-blink 520ms cubic-bezier(.22,.61,.36,1) forwards;}
@keyframes tap-blink {0% {opacity:.95; transform:scale(.4);} 42% {opacity:.75; transform:scale(1.05);} 100% {opacity:0; transform:scale(1.9);}}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {animation-duration:.01ms !important; animation-iteration-count:1 !important; transition-duration:.01ms !important; scroll-behavior:auto !important;}
}
</style>
""", unsafe_allow_html=True)
st.html("""
<script>
(() => {
  if (window.__a2tTapBlinkListenerInstalled) return;
  window.__a2tTapBlinkListenerInstalled = true;
  document.addEventListener("pointerdown", (event) => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    const blink = document.createElement("span");
    blink.className = "a2t-tap-blink";
    blink.setAttribute("aria-hidden", "true");
    blink.style.left = `${event.clientX}px`;
    blink.style.top = `${event.clientY}px`;
    document.body.appendChild(blink);
    blink.addEventListener("animationend", () => blink.remove(), { once: true });
  }, { capture: true, passive: true });
})();
</script>
""", unsafe_allow_javascript=True)

st.sidebar.markdown('<div class="brand-small">a2t AI</div>', unsafe_allow_html=True)
st.sidebar.title("⚙️ Transcription settings")
engine = st.sidebar.selectbox("Engine", ["Local Whisper.cpp", "Hugging Face Cloud API"])
if engine == "Local Whisper.cpp":
    model = st.sidebar.selectbox("Model", ["Whisper Small", "Whisper Large-v3"], help="Large-v3 requires about 3 GB disk and roughly 4 GB RAM for inference.")
else:
    model = st.sidebar.selectbox("Cloud model", ["openai/whisper-large-v3"])
language_mode = st.sidebar.radio("Language", ["Auto Detect", "Manual"])
language = "auto"
if language_mode == "Manual":
    language_options = {"English": "en", "Tamil": "ta", "Telugu": "te", "Malayalam": "ml", "Kannada": "kn", "Hindi": "hi", "Spanish": "es", "French": "fr", "German": "de", "Other / use code": "other"}
    label = st.sidebar.selectbox("Language", list(language_options))
    language = st.sidebar.text_input("Whisper language code", "en") if label == "Other / use code" else language_options[label]
    st.sidebar.caption("Manual language selection is passed to local whisper.cpp. Hugging Face provider models may ignore this setting.")
translate_to_english = st.sidebar.checkbox("Translate output to English", help="Uses Whisper speech translation when the selected engine/provider supports it.")
st.sidebar.caption("FFmpeg must be installed and available on PATH.")

if "results" not in st.session_state:
    st.session_state.results = []
if "coordinator" not in st.session_state:
    st.session_state.coordinator = CoordinatorAgent()


def clear_chat() -> None:
    st.session_state.results = []
    st.session_state.selected_history_id = None


def clear_history() -> None:
    st.session_state.history = []
    st.session_state.selected_history_id = None
    HISTORY_FILE.write_text("[]", encoding="utf-8")

hero_col, menu_col = st.columns([14, 1])
with hero_col:
    intro_class = " hero-appear" if animate_intro else ""
    st.markdown(f'<div class="hero{intro_class}"><div class="hero-top"><div class="hero-icon">🎙️</div><div><h1>a2t AI | Audio to Text AI Agent</h1><p>Upload an audio file and get text easily!</p></div><div class="ready">🟢 Ready to Use</div></div></div>', unsafe_allow_html=True)
with menu_col:
    with st.popover("⋯", help="Reports, save files, and chat controls"):
        st.markdown("**Reports to generate**")
        formats = [fmt for fmt in ("TXT", "PDF", "DOCX", "SRT") if st.checkbox(fmt, value=True, key=f"report_{fmt}")]
        st.divider()
        if has_saved_reports(st.session_state.history):
            st.download_button(
                "💾 Save files",
                data=build_report_archive(st.session_state.history),
                file_name="a2t_saved_reports.zip",
                mime="application/zip",
                help="Download saved reports. Each recording stays in its own folder in the ZIP.",
                use_container_width=True,
                key="save_history_reports",
            )
        else:
            st.button("💾 Save files", disabled=True, use_container_width=True, help="Reports will be available here after processing.")
        st.divider()
        st.markdown("**Chat controls**")
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("Clear chat", key="clear_chat", use_container_width=True):
                clear_chat()
                st.rerun()
        with action_col2:
            if st.button("Clear history", key="clear_history", use_container_width=True):
                clear_history()
                st.rerun()
with st.expander("Engine and privacy details", expanded=False):
    st.write("Local Whisper.cpp runs on this computer. Hugging Face Cloud sends audio to the selected inference provider; configure HF_TOKEN in .env to use it.")


def start_new_chat() -> None:
    st.session_state.results = []
    st.session_state.selected_history_id = None
    st.session_state.pop("audio_uploads", None)


st.sidebar.button("＋ New chat", key="new_chat", on_click=start_new_chat, use_container_width=True)
with st.sidebar.expander(f"🕘 Chat history · {len(st.session_state.history)} recordings", expanded=False):
    if st.session_state.history:
        for old in reversed(st.session_state.history[-12:]):
            stamp = old.get("processed_at", "")[:16].replace("T", " ")
            title = f"{old.get('filename', 'Recording')} · {stamp}"
            if st.button(title, key=f"history_{old.get('history_id')}", use_container_width=True):
                st.session_state.selected_history_id = old.get("history_id")
    else:
        st.caption("Completed and failed recordings will appear here.")


def process(files):
    if not files:
        st.warning("Upload at least one audio recording first.")
        return
    if not formats:
        st.warning("Choose at least one report format from the ⋯ menu.")
        return
    tracker = st.progress(0, text="Preparing recordings…")
    status = st.empty()
    def on_progress(index, total, filename):
        tracker.progress(int((index - 1) / total * 100), text=f"Processing {index} of {total}: {filename}")
        status.write(f"Recording **{index}/{total}** · `{filename}`")
    results = st.session_state.coordinator.process_batch(
        files, engine, model, language, OUTPUTS, formats, on_progress,
        translate_to_english=translate_to_english,
    )
    tracker.progress(100, text="Processing complete")
    st.session_state.results = results
    for record in results:
        st.session_state.history.append({
            **record,
            "history_id": uuid.uuid4().hex,
            "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    st.session_state.history = st.session_state.history[-50:]
    HISTORY_FILE.write_text(json.dumps(st.session_state.history, ensure_ascii=False, indent=2), encoding="utf-8")
    succeeded = sum(r["status"] == "Completed" for r in results)
    st.success(f"{succeeded} completed · {len(results) - succeeded} failed")


def single_paragraph(text: str) -> str:
    """Return transcript text as one paragraph with whitespace normalized."""
    return re.sub(r"\s+", " ", (text or "")).strip()


uploads = st.file_uploader("Upload one audio file or several", type=["wav", "mp3", "m4a", "flac", "ogg"], accept_multiple_files=True, key="audio_uploads")
if uploads:
    total_mb = sum(file.size for file in uploads) / (1024 * 1024)
    st.caption(f"{len(uploads)} recording{'s' if len(uploads) != 1 else ''} selected · {total_mb:.2f} MB total")
    for audio_file in uploads:
        st.caption(f"🎵 {audio_file.name} · {audio_file.size / 1048576:.2f} MB")
if st.button("Start Transcription", type="primary", key="run_transcription"):
    process(uploads)

if st.session_state.results:
    st.divider()
    st.markdown('<div class="result-title">✅ Transcription Results</div>', unsafe_allow_html=True)
    for i, record in enumerate(st.session_state.results, 1):
        with st.expander(f"{i}. {record['filename']} — {record['status']}", expanded=len(st.session_state.results) == 1):
            if record["status"] == "Failed":
                st.error(record.get("error", "Unknown processing error"))
                continue
            st.write(f"**Duration:** {record['duration']:.1f}s · **Engine:** {record['engine']} · **Model:** {record['model']}")
            st.write(f"**Detected language:** {record.get('detected_language', 'Unknown (review recommended)')}")
            if record.get("translated_to_english"):
                st.write("**Output language:** English translation")
            with st.container(border=True):
                st.markdown("**Transcript**")
                st.write(single_paragraph(record.get("text", "")) or "Transcript text is not available.")
            quality = record.get("quality", {})
            st.write(f"**Review recommendation:** {quality.get('recommendation', 'Not available')}")
            st.caption(quality.get("confidence_note", ""))
            for flag in quality.get("review_sections", []):
                st.warning(flag)
            for fmt, file_path in record.get("reports", {}).items():
                path = Path(file_path)
                if path.exists():
                    st.download_button(f"Download {fmt}", path.read_bytes(), file_name=path.name, mime={"TXT":"text/plain", "PDF":"application/pdf", "DOCX":"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "SRT":"application/x-subrip"}.get(fmt, "application/octet-stream"), key=f"dl_{i}_{fmt}")

selected_history = next((entry for entry in st.session_state.history if entry.get("history_id") == st.session_state.selected_history_id), None)
if selected_history:
    st.divider()
    st.subheader(f"History · {selected_history.get('filename', 'Recording')}")
    st.caption(f"Processed {selected_history.get('processed_at', 'unknown time')} · {selected_history.get('status', 'Unknown')}")
    if selected_history.get("status") == "Failed":
        st.error(selected_history.get("error", "Unknown processing error"))
    else:
        st.write(single_paragraph(selected_history.get("text", "")))
