import json
from pathlib import Path

import streamlit as st

PREFS_FILE = Path("output/user_preferences.json")


def load_preferences():
    if "user_preferences" in st.session_state:
        return st.session_state.user_preferences
    if PREFS_FILE.exists():
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except Exception:
            prefs = {}
    else:
        prefs = {}
    st.session_state.user_preferences = prefs
    return prefs


def save_preferences(prefs):
    PREFS_FILE.parent.mkdir(exist_ok=True)
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2, ensure_ascii=False)
    st.session_state.user_preferences = prefs


def safe_rerun():
    try:
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
    except Exception:
        pass

def is_dark_mode():
    return bool(load_preferences().get("dark_mode", False))


def set_dark_mode(enabled):
    prefs = dict(load_preferences())
    prefs["dark_mode"] = bool(enabled)
    save_preferences(prefs)


def apply_theme():
    dark = is_dark_mode()
    if dark:
        st.markdown("""
<style>
:root {
  color-scheme: dark;
  --sb-bg: #0f1117;
  --sb-card: #151923;
  --sb-panel: linear-gradient(135deg,#151923,#111827);
  --sb-assistant: #151923;
  --sb-border: #2a3142;
  --sb-text: #f4f4f5;
  --sb-muted: #a1a1aa;
}
html, body, .stApp, [data-testid="stAppViewContainer"] { background:#0f1117 !important; color:#f4f4f5 !important; }
section[data-testid="stSidebar"] { background:#111827 !important; color:#f4f4f5 !important; }
[data-testid="stHeader"] { background:rgba(15,17,23,0.88) !important; }
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *, .stMarkdown, .stMarkdown *, p, label, span, div, h1, h2, h3, h4, h5, h6 { color:inherit; }
.stApp a { color:#93c5fd !important; }
div[data-testid="stTabs"] button { color:#e5e7eb !important; }
div[data-testid="stTabs"] [aria-selected="true"] { color:#ffffff !important; }
div[data-testid="stMetric"] { background:#151923 !important; border:1px solid #2a3142 !important; border-radius:14px !important; padding:10px !important; }
div[data-testid="stMetric"] * { color:#f4f4f5 !important; }
.stTextInput input, .stTextArea textarea { background:#151923 !important; color:#f4f4f5 !important; border-color:#374151 !important; caret-color:#ffffff !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color:#9ca3af !important; }
.stSelectbox div[data-baseweb="select"] > div { background:#151923 !important; color:#f4f4f5 !important; border-color:#374151 !important; }
.stSlider [data-baseweb="slider"] { color:#8b5cf6 !important; }
.stButton button { border-color:#374151 !important; }
.file-badge, .entity-card, .ocr-box { background:#151923 !important; border-color:#2a3142 !important; color:#f4f4f5 !important; }
.sb-chat-hero, .sb-chat-input-card { background:#151923 !important; border-color:#2a3142 !important; box-shadow:0 12px 35px rgba(0,0,0,0.30) !important; }
.sb-chat-title, .sb-chat-bubble { color:#f4f4f5 !important; }
.sb-chat-subtitle, .sb-chat-label, .sb-chat-empty { color:#a1a1aa !important; }
.sb-chat-bubble { background:#151923 !important; border-color:#2a3142 !important; }
.sb-chat-row.user .sb-chat-bubble { background:#2563eb !important; color:#ffffff !important; border-color:#2563eb !important; }
.stApp, .stApp * { color: var(--sb-text) !important; }
.stApp .sb-chat-row.user .sb-chat-bubble, .stApp .sb-chat-row.user .sb-chat-bubble * { color:#ffffff !important; }
.stApp .sb-chat-subtitle, .stApp .sb-chat-label, .stApp .sb-chat-empty, .stApp small, .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] * { color: var(--sb-muted) !important; }
.stApp [data-baseweb], .stApp [data-baseweb] *, .stApp [class*="st-"] *, .stApp [class*="css-"] { color: var(--sb-text) !important; }
.stApp input, .stApp textarea, .stApp input *, .stApp textarea * { color:#f4f4f5 !important; -webkit-text-fill-color:#f4f4f5 !important; }
.stApp input::placeholder, .stApp textarea::placeholder { color:#9ca3af !important; -webkit-text-fill-color:#9ca3af !important; opacity:1 !important; }
.stApp button, .stApp button * { color:#f4f4f5 !important; }
.stApp button[kind="primary"], .stApp button[kind="primary"] * { color:#ffffff !important; }
.stApp [role="tab"], .stApp [role="tab"] * { color:#e5e7eb !important; }
.stApp [aria-selected="true"], .stApp [aria-selected="true"] * { color:#ffffff !important; }
.stApp [data-testid="stExpander"], .stApp [data-testid="stExpander"] * { color:#f4f4f5 !important; }
.stApp [data-testid="stAlert"], .stApp [data-testid="stAlert"] * { color:#f4f4f5 !important; }
.stApp [data-testid="stNotification"], .stApp [data-testid="stNotification"] * { color:#f4f4f5 !important; }
.stApp [data-testid="stFileUploader"], .stApp [data-testid="stFileUploader"] * { color:#f4f4f5 !important; }
.stApp [data-testid="stForm"], .stApp [data-testid="stForm"] * { color:#f4f4f5 !important; }
.stApp svg, .stApp svg * { color:inherit !important; fill:currentColor !important; }
.stApp [data-testid="stFileUploader"] section,
.stApp [data-testid="stFileUploader"] section > div,
.stApp [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"],
.stApp [data-testid="stFileUploaderDropzone"],
.stApp [data-testid="stFileUploaderDropzone"] * {
  background: var(--sb-card) !important;
  color: var(--sb-text) !important;
}
.stApp [data-testid="stFileUploader"] section,
.stApp [data-testid="stFileUploaderDropzone"] {
  border-color: #ffffff !important;
}
.stApp .file-badge,
.stApp .entity-card,
.stApp .ocr-box,
.stApp .sb-chat-hero,
.stApp .sb-chat-input-card,
.stApp .sb-chat-bubble,
.stApp div[data-testid="stMetric"],
.stApp [data-testid="stExpander"] details,
.stApp [data-testid="stExpander"] summary {
  border-color: #ffffff !important;
}
.stApp section[data-testid="stSidebar"] input,
.stApp section[data-testid="stSidebar"] textarea,
.stApp section[data-testid="stSidebar"] [data-baseweb="input"],
.stApp section[data-testid="stSidebar"] [data-baseweb="input"] > div,
.stApp section[data-testid="stSidebar"] [data-baseweb="base-input"],
.stApp section[data-testid="stSidebar"] [data-baseweb="base-input"] > div {
  background: var(--sb-card) !important;
  color: var(--sb-text) !important;
  -webkit-text-fill-color: var(--sb-text) !important;
  border-color: #ffffff !important;
}
.stApp [data-testid="stFileUploader"] section,
.stApp [data-testid="stFileUploader"] section div,
.stApp [data-testid="stFileUploaderDropzone"],
.stApp [data-testid="stFileUploaderDropzone"] div,
.stApp [data-testid="stFileUploaderDropzone"] button,
.stApp [data-testid="stFileUploaderDropzone"] label {
  background-color: var(--sb-card) !important;
  background: var(--sb-card) !important;
  color: var(--sb-text) !important;
  -webkit-text-fill-color: var(--sb-text) !important;
}
.stApp [data-testid="stFileUploaderDropzone"] svg,
.stApp [data-testid="stFileUploader"] svg {
  color: var(--sb-text) !important;
  fill: var(--sb-text) !important;
}
.stApp [data-testid="stFileUploaderDropzone"] button,
.stApp [data-testid="stFileUploader"] button,
.stApp .sb-chat-input-card button,
.stApp div[data-testid="column"] button {
  background: var(--sb-card) !important;
  color: var(--sb-text) !important;
  border: 1px solid #ffffff !important;
  box-shadow: none !important;
}
.stApp button[kind="primary"],
.stApp button[kind="primary"] * {
  background: #2563eb !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  border-color: #ffffff !important;
}
.stApp iframe {
  background: #0f1117 !important;
  border: 1px solid #ffffff !important;
  border-radius: 14px !important;
}
</style>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<style>
:root {
  color-scheme: light;
  --sb-bg: #ffffff;
  --sb-card: #ffffff;
  --sb-panel: linear-gradient(135deg,#ffffff,#f7f7f8);
  --sb-assistant: #f7f7f8;
  --sb-border: #e5e7eb;
  --sb-text: #111827;
  --sb-muted: #6b7280;
}
.stApp { background:#ffffff; color:#111827; }
</style>
""", unsafe_allow_html=True)
