import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from ..config import OCR_MODEL, SUPPORTED_FORMATS
from ..entities import extract_entities
from ..graph_store import get_existing_topics, load_graph, merge_entities, save_graph
from ..ocr import extract_pdf_text, ocr_from_url, ocr_image, render_pdf_pages

def render_ingest_tab(mistral_key_manager, router_cfg, router_model):
    st.markdown("### Upload Documents")
    
    tab_file, tab_url, tab_paste = st.tabs(["Upload Files", "Image URL", "Paste Text"])
    
    source_type = None
    uploaded_files = None
    url_input = None
    paste_text = None
    
    with tab_file:
        uploaded_files = st.file_uploader("Drop PDFs or images here", type=SUPPORTED_FORMATS, accept_multiple_files=True)
        if uploaded_files:
            source_type = "file"
            st.info(str(len(uploaded_files))+" file(s) ready")
            for f in uploaded_files:
                st.markdown('<div class="file-badge"><b>'+f.name+'</b> &mdash; '+str(round(f.size/1024,1))+' KB</div>', unsafe_allow_html=True)
    
    with tab_url:
        url_input = st.text_input("Image URL", placeholder="https://example.com/image.jpg")
        if url_input: source_type = "url"
    
    with tab_paste:
        paste_text = st.text_area("Paste notes here", height=250, placeholder="Paste any text or notes...")
        if paste_text and paste_text.strip(): source_type = "paste"
    
    st.divider()
    
    if source_type is None:
        st.info("Upload a file, enter a URL, or paste text to begin.")
        return
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        process = st.button("Extract and Build Graph", type="primary", use_container_width=True)
    
    if not process: return
    
    # step 1: ocr
    ocr_results = []
    
    if source_type == "paste":
        ocr_results.append({"success":True,"text":paste_text.strip(),"source":"Pasted Notes","method":"direct_input","elapsed":0,"usage":{},"model":"N/A"})
    elif source_type == "url":
        with st.spinner("Extracting text from URL..."):
            r = ocr_from_url(mistral_key_manager, url_input)
            r["source"] = url_input
            r["method"] = "url_ocr"
            ocr_results.append(r)
    elif source_type == "file":
        progress = st.progress(0)
        for idx, uf in enumerate(uploaded_files):
            progress.progress(idx/len(uploaded_files), text="Processing "+uf.name+"...")
            raw = uf.read()
            ext = Path(uf.name).suffix.lower()
            
            if ext == ".pdf":
                with st.spinner("Extracting text from "+uf.name+"..."):
                    pdf_text = extract_pdf_text(raw)
                if pdf_text and len(pdf_text.strip()) > 50:
                    ocr_results.append({"success":True,"text":pdf_text,"source":uf.name,"method":"pdf_text","elapsed":0,"usage":{},"model":"PyMuPDF"})
                else:
                    with st.spinner("Rendering pages for OCR..."):
                        pages = render_pdf_pages(raw)
                    if not pages:
                        ocr_results.append({"success":False,"error":"Cannot read PDF","text":"","source":uf.name,"elapsed":0})
                    else:
                        combined = []
                        tu = {"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}
                        tt = 0
                        for pi, pg in enumerate(pages):
                            with st.spinner("OCR page "+str(pi+1)+"/"+str(len(pages))):
                                pr = ocr_image(mistral_key_manager, pg, "page_"+str(pi+1)+".png")
                            if pr["success"]:
                                combined.append(pr["text"])
                                for k in tu: tu[k] += pr.get("usage",{}).get(k,0)
                                tt += pr.get("elapsed",0)
                        ocr_results.append({"success":len(combined)>0,"text":"\n\n--- Page Break ---\n\n".join(combined),"source":uf.name,"method":"pdf_ocr","elapsed":round(tt,2),"usage":tu,"model":OCR_MODEL})
            else:
                with st.spinner("OCR on "+uf.name+"..."):
                    r = ocr_image(mistral_key_manager, raw, uf.name)
                    r["source"] = uf.name
                    r["method"] = "image_ocr"
                    ocr_results.append(r)
            
            progress.progress((idx+1)/len(uploaded_files), text="Done: "+uf.name)
        progress.progress(1.0, text="OCR complete!")
    
    # step 2: entity extraction
    successful_ocr = [r for r in ocr_results if r.get("success") and r.get("text","").strip()]
    
    if not successful_ocr:
        st.warning("No text extracted. Nothing to process.")
        return
    
    graph = load_graph()
    existing_topics = get_existing_topics(graph)
    
    st.markdown("---")
    st.markdown("### Extracting Entities and Building Graph...")
    
    extraction_results = []
    for r in successful_ocr:
        text = r["text"]
        if not text or text.strip() == "[No text detected]": continue
        with st.spinner("Extracting entities from: "+r.get("source","")+"..."):
            er = extract_entities(router_cfg, text, existing_topics, model_override=router_model)
            er["source"] = r.get("source","Unknown")
            
            if er.get("success") and er.get("entities"):
                graph = merge_entities(er["entities"], er["source"], graph)
                save_graph(graph)
                existing_topics = get_existing_topics(graph)
            
            extraction_results.append(er)

    # display results
    st.markdown("---")
    st.markdown("### Results")
    
    sc = sum(1 for e in extraction_results if e.get("success"))
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Files Processed", len(successful_ocr))
    m2.metric("Entities Extracted", sc)
    m3.metric("Total Nodes", len(graph.get("nodes",{})))
    m4.metric("Total Edges", len(graph.get("edges",[])))
    
    for i, (ocr_r, er) in enumerate(zip(successful_ocr, extraction_results)):
        source = ocr_r.get("source","Document "+str(i+1))
        text = ocr_r.get("text","")
        
        with st.expander(source+" -- "+str(len(text.split()))+" words", expanded=True):
            st.markdown("#### Extracted Entities")
            if er.get("success") and er.get("entities"):
                ent = er["entities"]
                
                if ent.get("main_topics"):
                    st.markdown("**Main Topics:**")
                    for t in ent["main_topics"]:
                        st.markdown('<div class="entity-card main-topic"><b>'+t.get("name","")+'</b><br><small>'+t.get("description","")+'</small></div>', unsafe_allow_html=True)
                
                if ent.get("subtopics"):
                    st.markdown("**Subtopics:**")
                    for s in ent["subtopics"]:
                        st.markdown('<div class="entity-card subtopic"><b>'+s.get("name","")+'</b> <small>(under: '+s.get("parent_topic","")+')</small><br><small>'+s.get("description","")+'</small></div>', unsafe_allow_html=True)
                
                if ent.get("entities"):
                    st.markdown("**Entities:**")
                    for e in ent["entities"]:
                        st.markdown('<div class="entity-card entity"><b>'+e.get("name","")+'</b> <small>['+e.get("entity_type","")+'] under: '+e.get("parent_topic","")+'</small><br><small>'+e.get("description","")+'</small></div>', unsafe_allow_html=True)
                
                if ent.get("relationships"):
                    st.markdown("**Relationships:**")
                    for rel in ent["relationships"]:
                        st.caption(rel.get("from","")+" --["+rel.get("relation","")+"]--> "+rel.get("to","")+(" | "+rel.get("context","") if rel.get("context") else ""))
                
                if ent.get("tags"):
                    st.markdown("**Tags:** "+", ".join(["`"+t+"`" for t in ent["tags"]]))
                
                usage = er.get("usage",{})
                st.caption(str(er["elapsed"])+"s | Model: "+str(er.get("model",""))+" | Tokens: "+str(usage.get("total_tokens",0)))
            elif er:
                st.error("Extraction failed: "+er.get("error","Unknown"))
            else:
                st.warning("9Router not configured.")
            
            st.markdown("---")
            st.markdown("#### Raw Extracted Text")
            st.markdown('<div class="ocr-box">'+text+'</div>', unsafe_allow_html=True)
    
    # export
    if extraction_results:
        st.markdown("---")
        st.markdown("### Export")
        c1, c2 = st.columns(2)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with c1:
            st.download_button("Download Graph JSON", data=json.dumps(graph,indent=2,ensure_ascii=False), file_name="knowledge_graph_"+ts+".json", mime="application/json", use_container_width=True)
        with c2:
            export_data = {"date":datetime.now().isoformat(),"extractions":[{"source":er.get("source"),"entities":er.get("entities"),"elapsed":er.get("elapsed")} for er in extraction_results if er.get("success")],"graph":graph}
            st.download_button("Download Full Export", data=json.dumps(export_data,indent=2,ensure_ascii=False), file_name="brain_export_"+ts+".json", mime="application/json", use_container_width=True)


