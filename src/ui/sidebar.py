import streamlit as st

from ..config import get_mistral_config, get_router_config
from .prefs import is_dark_mode, safe_rerun, set_dark_mode


def render_sidebar(keys):
    with st.sidebar:
        st.markdown("### Status")
        mc = get_mistral_config(keys)
        if mc["errors"]:
            st.error("Mistral OCR: Config error")
            for err in mc["errors"]: st.caption(err)
        else:
            st.success("Mistral OCR: "+str(len(mc["keys"]))+" keys, "+mc["usage_mode"].replace("_"," "))

        rc = get_router_config(keys)
        if rc["base_url"]: st.success("9Router: "+rc["base_url"])
        else: st.error("9Router: Not configured")

        st.divider()
        st.markdown("### Appearance")
        current_dark = is_dark_mode()
        dark_mode = st.toggle("Dark mode", value=current_dark, help="Saved locally in output/user_preferences.json")
        if dark_mode != current_dark:
            set_dark_mode(dark_mode)
            safe_rerun()

        st.divider()
        st.markdown("### Settings")
        rm = st.text_input("9Router Model", value=rc.get("model","") or "gpt-4o-mini", help="Model buat di-route ke 9Router")

    return rm
