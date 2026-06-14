import streamlit as st

from .config import KEY_FILE, get_mistral_config, get_router_config, load_keys
from .key_manager import MistralKeyManager
from .ui.graph_tab import render_graph_tab
from .ui.ingest import render_ingest_tab
from .ui.sidebar import render_sidebar


def configure_page():
    st.set_page_config(page_title="Second Brain", page_icon="S", layout="wide", initial_sidebar_state="expanded")
    st.markdown("""
<style>
    .main-header { font-size: 2.4rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.1rem; }
    .sub-header { color: #888; font-size: 1rem; margin-bottom: 1.5rem; }
    .step-done { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 0.45rem 1rem; border-radius: 20px; font-weight: 600; display: inline-block; margin: 0.15rem 0; font-size: 0.85rem; }
    .step-active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.45rem 1rem; border-radius: 20px; font-weight: 600; display: inline-block; margin: 0.15rem 0; font-size: 0.85rem; }
    .step-pending { background: #e0e0e0; color: #888; padding: 0.45rem 1rem; border-radius: 20px; font-weight: 600; display: inline-block; margin: 0.15rem 0; font-size: 0.85rem; }
    .file-badge { background: #f0f2f6; border: 1px solid #ddd; border-radius: 8px; padding: 0.7rem 1rem; margin: 0.3rem 0; }
    .entity-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 1rem; margin: 0.4rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .entity-card.main-topic { border-left: 4px solid #667eea; }
    .entity-card.subtopic { border-left: 4px solid #38ef7d; }
    .entity-card.entity { border-left: 4px solid #fcb69f; }
    .ocr-box { background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.2rem; margin: 0.5rem 0; font-family: monospace; font-size: 0.82rem; line-height: 1.6; max-height: 300px; overflow-y: auto; white-space: pre-wrap; }
    #MainMenu, header, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


def main():
    configure_page()
    st.markdown('<p class="main-header">Second Brain</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload &rarr; OCR &rarr; Knowledge Graph</p>', unsafe_allow_html=True)

    keys = load_keys()
    mc = get_mistral_config(keys)
    rc = get_router_config(keys)
    rm = render_sidebar(keys)

    if mc["errors"]:
        st.error("Config Mistral belum valid di `"+KEY_FILE+"`")
        for err in mc["errors"]: st.error(err)
        st.code('''{
  "mistral": {
    "api_key1": "your-mistral-api-key-1",
    "api_key2": "your-mistral-api-key-2",
    "api_key3": "your-mistral-api-key-3",
    "api_key4": "your-mistral-api-key-4",
    "api_key5": "your-mistral-api-key-5",
    "api_key6": "your-mistral-api-key-6",
    "api_key7": "your-mistral-api-key-7",
    "usage_mode": "sequential"
  }
}''', language="json")
        return
    key_manager = MistralKeyManager(mc)

    tab_ingest, tab_graph = st.tabs(["Ingest", "Knowledge Graph"])

    with tab_ingest:
        render_ingest_tab(key_manager, rc, rm)

    with tab_graph:
        render_graph_tab()
