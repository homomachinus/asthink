import streamlit as st

from ..config import get_mistral_config, get_router_config
from ..graph_store import load_graph
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
        st.markdown("### Settings")
        rm = st.text_input("9Router Model", value=rc.get("model","") or "gpt-4o-mini", help="Model buat di-route ke 9Router")
        
        st.divider()
        st.markdown("### Pipeline")
        st.markdown('<span class="step-done">1. Upload</span>', unsafe_allow_html=True)
        st.markdown('<span class="step-done">2. OCR (Mistral)</span>', unsafe_allow_html=True)
        st.markdown('<span class="step-active">3. Entity Extraction</span>', unsafe_allow_html=True)
        st.markdown('<span class="step-active">4. Knowledge Graph</span>', unsafe_allow_html=True)
        st.markdown('<span class="step-pending">5. Vector Store</span>', unsafe_allow_html=True)
        st.markdown('<span class="step-pending">6. Retrieval</span>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown("### Graph Stats")
        g = load_graph()
        nc = len(g.get("nodes",{}))
        ec = len(g.get("edges",[]))
        sc = len(g.get("sources",[]))
        st.metric("Nodes", nc)
        st.metric("Edges", ec)
        st.metric("Sources", sc)
        
        types = {}
        for n in g.get("nodes",{}).values():
            t = n.get("type","unknown")
            types[t] = types.get(t,0) + 1
        if types:
            for t,c in types.items():
                st.caption(t.replace("_"," ").title()+": "+str(c))
        
        st.divider()
        st.caption("Second Brain v0.3 - Knowledge Graph")
    
    return rm

