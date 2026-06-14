"""
Second Brain - Knowledge Graph Builder
Cara pakai:
  1. pip install streamlit requests pymupdf pdfplumber pyvis networkx
  2. Isi key.json sama API keys lo
  3. Jalanin: streamlit run main.py
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import json
import time
import io
import os
import uuid
from pathlib import Path
from datetime import datetime

# config utama
KEY_FILE = "key.json"
GRAPH_FILE = "knowledge_graph.json"
OCR_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
OCR_MODEL = "pixtral-12b-2409"
MAX_TOKENS = 4096
SUPPORTED_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp", "gif", "pdf"]
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# setting halaman
st.set_page_config(page_title="Second Brain", page_icon="S", layout="wide", initial_sidebar_state="expanded")

# css custom
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
@st.cache_resource
def load_keys():
    p = Path(KEY_FILE)
    if not p.exists(): return {}
    try:
        with open(p, "r") as f: return json.load(f)
    except: return {}

def get_mistral_key(k): return k.get("mistral",{}).get("api_key","").strip()

def get_router_config(k):
    c = k.get("9router",{})
    return {"api_key": c.get("api_key","").strip(), "base_url": c.get("base_url","http://localhost:20128/v1").strip(), "model": c.get("model","").strip()}

def get_mime(f):
    e = Path(f).suffix.lower()
    m = {".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".bmp":"image/bmp",".tiff":"image/tiff",".tif":"image/tiff",".webp":"image/webp",".gif":"image/gif",".pdf":"application/pdf"}
    return m.get(e, "image/jpeg")

# knowledge graph storage
def load_graph():
    p = Path(GRAPH_FILE)
    if not p.exists(): return {"nodes":{},"edges":[],"sources":[]}
    try:
        with open(p,"r",encoding="utf-8") as f: return json.load(f)
    except: return {"nodes":{},"edges":[],"sources":[]}

def save_graph(g):
    with open(GRAPH_FILE,"w",encoding="utf-8") as f: json.dump(g,f,indent=2,ensure_ascii=False)

def get_existing_topics(g): return [n["label"] for n in g.get("nodes",{}).values()]

def node_id(name): return name.lower().strip().replace(" ","_")[:80]

# gabung entity ke graph
def merge_entities(data, source, graph):
    nodes = graph.get("nodes",{})
    edges = graph.get("edges",[])
    sources = graph.get("sources",[])
    now = datetime.now().isoformat()
    if source not in sources: sources.append(source)

    def add_node(name, ntype, desc, parent=""):
        nid = node_id(name)
        if nid in nodes:
            e = nodes[nid]
            if source not in e.get("sources",[]): e["sources"].append(source)
            if desc and (not e.get("description") or len(desc) > len(e.get("description",""))): e["description"] = desc
            e["updated_at"] = now
        else:
            nodes[nid] = {"id":nid,"label":name,"type":ntype,"description":desc or "","parent_topic":parent,"sources":[source],"created_at":now,"updated_at":now}
        return nid

    for t in data.get("main_topics",[]):
        n = t.get("name","").strip()
        if n: add_node(n, "main_topic", t.get("description",""))

    for s in data.get("subtopics",[]):
        n = s.get("name","").strip()
        p = s.get("parent_topic","").strip()
        if n:
            nid = add_node(n, "subtopic", s.get("description",""), p)
            if p:
                pid = node_id(p)
                ek = pid + "->" + nid + ":subtopic_of"
                if not any(x.get("key")==ek for x in edges):
                    edges.append({"key":ek,"source":pid,"target":nid,"relation":"subtopic_of","context":n+" is subtopic of "+p})

    for e in data.get("entities",[]):
        n = e.get("name","").strip()
        p = e.get("parent_topic","").strip()
        if n:
            nid = add_node(n, "entity", e.get("description",""), p)
            if p:
                pid = node_id(p)
                ek = pid + "->" + nid + ":contains"
                if not any(x.get("key")==ek for x in edges):
                    edges.append({"key":ek,"source":pid,"target":nid,"relation":"contains","context":p+" contains "+n})

    for r in data.get("relationships",[]):
        f = r.get("from","").strip()
        t = r.get("to","").strip()
        rel = r.get("relation","related_to").strip()
        if f and t:
            fid = node_id(f)
            tid = node_id(t)
            ek = fid + "->" + tid + ":" + rel
            if not any(x.get("key")==ek for x in edges):
                edges.append({"key":ek,"source":fid,"target":tid,"relation":rel,"context":r.get("context","")})

    for tag in data.get("tags",[]):
        if tag.strip(): add_node(tag.strip(), "tag", "")

    graph["nodes"] = nodes
    graph["edges"] = edges
    graph["sources"] = sources
    return graph

# ocr functions
def ocr_image(api_key, img_bytes, filename):
    mime = get_mime(filename)
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    payload = {
        "model": OCR_MODEL, "max_tokens": MAX_TOKENS,
        "messages": [
            {"role":"system","content":"You are a highly accurate OCR engine. Extract ALL text from the image with maximum fidelity. Preserve paragraphs, line breaks, headings. Convert tables to markdown. Preserve lists. Output ONLY extracted text. No commentary."},
            {"role":"user","content":[{"type":"text","text":"Extract all text from this document."},{"type":"image_url","image_url":"data:"+mime+";base64,"+b64}]}
        ]
    }
    start = time.time()
    try:
        r = requests.post(OCR_ENDPOINT, headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"}, json=payload, timeout=120)
    except Exception as e:
        return {"success":False,"error":str(e),"text":"","elapsed":0}
    elapsed = time.time() - start
    if r.status_code != 200:
        return {"success":False,"error":"HTTP "+str(r.status_code),"text":"","elapsed":elapsed}
    data = r.json()
    choices = data.get("choices",[])
    if not choices:
        return {"success":False,"error":"No text detected","text":"","elapsed":elapsed}
    return {"success":True,"text":choices[0].get("message",{}).get("content",""),"elapsed":round(elapsed,2),"usage":data.get("usage",{}),"model":data.get("model",OCR_MODEL)}

def ocr_from_url(api_key, url):
    payload = {
        "model": OCR_MODEL, "max_tokens": MAX_TOKENS,
        "messages": [
            {"role":"system","content":"You are a highly accurate OCR engine. Extract ALL text. Preserve structure. Output ONLY text."},
            {"role":"user","content":[{"type":"text","text":"Extract all text from this document."},{"type":"image_url","image_url":url}]}
        ]
    }
    start = time.time()
    try:
        r = requests.post(OCR_ENDPOINT, headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"}, json=payload, timeout=120)
    except Exception as e:
        return {"success":False,"error":str(e),"text":"","elapsed":0}
    elapsed = time.time() - start
    if r.status_code != 200:
        return {"success":False,"error":"HTTP "+str(r.status_code),"text":"","elapsed":elapsed}
    data = r.json()
    choices = data.get("choices",[])
    if not choices:
        return {"success":False,"error":"No text detected","text":"","elapsed":elapsed}
    return {"success":True,"text":choices[0].get("message",{}).get("content",""),"elapsed":round(elapsed,2),"usage":data.get("usage",{}),"model":data.get("model",OCR_MODEL)}

def extract_pdf_text(pdf_bytes):
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        txt = "\n\n".join([p.get_text() for p in doc])
        doc.close()
        if txt.strip(): return txt
    except: pass
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            txt = "\n\n".join([p.extract_text() or "" for p in pdf.pages])
            if txt.strip(): return txt
    except: pass
    return ""

def render_pdf_pages(pdf_bytes, dpi=200):
    imgs = []
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        mat = fitz.Matrix(dpi/72, dpi/72)
        for p in doc: imgs.append(p.get_pixmap(matrix=mat).tobytes("png"))
        doc.close()
    except: pass
    return imgs

# entity extraction via 9router
def extract_entities(config, text, existing_topics, model_override=""):
    base_url = config["base_url"].rstrip("/")
    endpoint = base_url + "/chat/completions"
    
    # bikin prompt buat extract entities
    existing_list = ""
    if existing_topics:
        existing_list = "\n\nIMPORTANT: These topics already exist in the knowledge graph:\n" + ", ".join(existing_topics[:50]) + "\n\nWhen extracting entities, if a topic matches or closely relates to an existing topic above, use the EXACT existing topic name so it can be linked. Do NOT create duplicates."
    
    system = "You are a knowledge graph builder. Analyze the text and extract a structured knowledge graph.\n\nRules:\n1. Identify MAIN TOPICS - broad, high-level subjects\n2. Identify SUBTOPICS - specific areas under main topics\n3. Identify ENTITIES - concepts, people, organizations, technologies, terms\n4. Identify RELATIONSHIPS - how entities relate (cross-links)\n5. Identify TAGS - keywords for categorization\n\nEach entity should have a clear parent_topic. Relationships connect entities across different branches.\n\nYou MUST respond with valid JSON only. No markdown, no explanation.\n\nStructure:\n{\n  \"main_topics\": [{\"name\": \"...\", \"description\": \"...\"}],\n  \"subtopics\": [{\"name\": \"...\", \"parent_topic\": \"...\", \"description\": \"...\"}],\n  \"entities\": [{\"name\": \"...\", \"entity_type\": \"concept|person|organization|technology|term|event\", \"parent_topic\": \"...\", \"description\": \"...\"}],\n  \"relationships\": [{\"from\": \"...\", \"to\": \"...\", \"relation\": \"uses|requires|related_to|enables|competes_with|part_of|influences\", \"context\": \"brief explanation\"}],\n  \"tags\": [\"tag1\", \"tag2\"]\n}" + existing_list
    
    max_input = 12000
    text_input = text[:max_input] + "\n\n[... truncated ...]" if len(text) > max_input else text
    model = model_override.strip() or config.get("model","").strip() or "gpt-4o-mini"
    
    payload = {
        "model": model, "max_tokens": 3000, "stream": False,
        "messages": [
            {"role":"system","content":system},
            {"role":"user","content":"Extract the knowledge graph entities from this text:\n\n" + text_input}
        ]
    }
    
    headers = {"Content-Type":"application/json"}
    if config.get("api_key"):
        headers["Authorization"] = "Bearer " + config["api_key"]
    
    start = time.time()
    try:
        r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    except requests.exceptions.ConnectionError:
        return {"success":False,"error":"Gak bisa connect ke 9Router di "+config["base_url"],"entities":None,"elapsed":0}
    except Exception as e:
        return {"success":False,"error":str(e),"entities":None,"elapsed":0}
    
    elapsed = time.time() - start
    if r.status_code != 200:
        return {"success":False,"error":"HTTP "+str(r.status_code)+": "+r.text[:500],"entities":None,"elapsed":elapsed}
    
    try:
        data = r.json()
    except:
        return {"success":False,"error":"Non-JSON response: "+r.text[:500],"entities":None,"elapsed":elapsed}
    
    choices = data.get("choices",[])
    if not choices:
        return {"success":False,"error":"Empty response","entities":None,"elapsed":elapsed}
    
    raw = choices[0].get("message",{}).get("content","")
    content = raw.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1].strip()=="```" else lines[1:])
    
    try:
        entities = json.loads(content)
    except:
        try:
            si = content.index("{")
            ei = content.rindex("}") + 1
            entities = json.loads(content[si:ei])
        except:
            return {"success":False,"error":"Failed to parse JSON: "+raw[:300],"entities":None,"elapsed":elapsed}
    
    return {"success":True,"entities":entities,"elapsed":round(elapsed,2),"model":data.get("model",model),"usage":data.get("usage",{})}

# graph visualization
def build_graph_html(graph, height=650):
    try:
        from pyvis.network import Network
    except ImportError:
        return None
    
    net = Network(height=str(height)+"px", width="100%", bgcolor="#ffffff", font_color="#333333", directed=True)
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150, spring_strength=0.05, damping=0.09)
    
    nodes = graph.get("nodes",{})
    edges = graph.get("edges",[])
    
    styles = {
        "main_topic": {"color":"#667eea","size":35,"shape":"dot"},
        "subtopic": {"color":"#38ef7d","size":25,"shape":"dot"},
        "entity": {"color":"#fcb69f","size":15,"shape":"dot"},
        "tag": {"color":"#e0e0e0","size":10,"shape":"dot"}
    }
    
    # buat setiap node
    for nid, node in nodes.items():
        ntype = node.get("type","entity")
        st = styles.get(ntype, styles["entity"])
        
        # ambil connected nodes
        connected = [e for e in edges if e.get("source")==nid or e.get("target")==nid]
        connected_info = []
        for e in connected:
            other_id = e["target"] if e["source"]==nid else e["source"]
            other_node = nodes.get(other_id,{})
            other_label = other_node.get("label", other_id)
            relation = e.get("relation","")
            other_desc = other_node.get("description","")
            connected_info.append({"label": other_label, "relation": relation, "description": other_desc})
        
        # bangun prompt buat chatgpt
        label = node.get("label","")
        desc = node.get("description","")
        parent = node.get("parent_topic","")
        sources = node.get("sources",[])
        
        prompt = "I'm studying the following topic from my knowledge graph. Please explain it in detail and help me learn more about it.\n\n"
        prompt += "## Topic: " + label + "\n"
        prompt += "**Type:** " + ntype + "\n"
        if desc: prompt += "**Description:** " + desc + "\n"
        if parent: prompt += "**Parent Topic:** " + parent + "\n"
        
        if connected_info:
            prompt += "\n## Related Topics:\n"
            for ci in connected_info:
                prompt += "- **" + ci["label"] + "** [" + ci["relation"] + "]"
                if ci["description"]: prompt += ": " + ci["description"]
                prompt += "\n"
        
        if sources:
            prompt += "\n## Source Documents:\n"
            prompt += "This information comes from: " + ", ".join(sources) + "\n"
        
        prompt += "\nPlease:\n"
        prompt += "1. Explain **" + label + "** in detail\n"
        if connected_info:
            related_names = [ci["label"] for ci in connected_info[:5]]
            prompt += "2. How does it relate to: " + ", ".join(related_names) + "?\n"
            prompt += "3. What are the key concepts I should know?\n"
            prompt += "4. Suggest further topics to explore\n"
        else:
            prompt += "2. What are the key concepts I should know?\n"
            prompt += "3. What related topics should I explore?\n"
        
        # url encode prompt
        encoded_prompt = requests.utils.quote(prompt, safe="")
        chatgpt_url = "https://chatgpt.com/?ask=" + encoded_prompt
        
        # bangun tooltip HTML
        # [Ask ChatGPT] link di paling awal
        title = '<a href="' + chatgpt_url + '" target="_blank" style="color:#667eea;text-decoration:underline;font-weight:bold;">[Ask ChatGPT]</a>'
        title += '<br><br><b>' + label + '</b>'
        title += '<br><i>Type: ' + ntype + '</i>'
        
        # full description (no truncation)
        if desc:
            title += '<br><br><b>Description:</b><br>' + desc
        
        # parent topic
        if parent:
            title += '<br><br><b>Parent Topic:</b> ' + parent
        
        # connected nodes
        if connected_info:
            title += '<br><br><b>Related Topics:</b>'
            for ci in connected_info:
                title += '<br>- <b>' + ci["label"] + '</b> [' + ci["relation"] + ']'
                if ci["description"]:
                    title += ': ' + ci["description"]
        
        # sources
        if sources:
            title += '<br><br><b>Sources:</b> ' + ", ".join(sources)
        
        net.add_node(nid, label=label, title=title, color=st["color"], size=st["size"], shape=st["shape"], font={"size":14 if ntype=="main_topic" else 11})
    
    # buat edges
    for edge in edges:
        s = edge.get("source","")
        t = edge.get("target","")
        rel = edge.get("relation","")
        ctx = edge.get("context","")
        if s in nodes and t in nodes:
            net.add_edge(s, t, title=rel+(": "+ctx if ctx else ""), label=rel, font={"size":8,"align":"middle"}, color={"color":"#cccccc","highlight":"#667eea"}, arrows={"to":{"enabled":True,"scaleFactor":0.5}})
    
    net.set_options('{"physics":{"barnesHut":{"gravitationalConstant":-3000,"centralGravity":0.3,"springLength":150,"springConstant":0.05,"damping":0.09},"minVelocity":0.75},"interaction":{"hover":true,"tooltipDelay":200,"navigationButtons":true,"keyboard":true}}')
    
    html = net.generate_html()
    return html

# sidebar
def render_sidebar(keys):
    with st.sidebar:
        st.markdown("### Status")
        mk = get_mistral_key(keys)
        if mk: st.success("Mistral OCR: Connected")
        else: st.error("Mistral OCR: No key")
        
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

# main app
def main():
    st.markdown('<p class="main-header">Second Brain</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload &rarr; OCR &rarr; Knowledge Graph</p>', unsafe_allow_html=True)
    
    keys = load_keys()
    mk = get_mistral_key(keys)
    rc = get_router_config(keys)
    rm = render_sidebar(keys)
    
    if not mk:
        st.error("Mistral API key belum ada. Tambahin di `"+KEY_FILE+"`")
        return
    
    # tabs
    tab_ingest, tab_graph = st.tabs(["Ingest", "Knowledge Graph"])
    
    with tab_ingest:
        render_ingest_tab(mk, rc, rm)
    
    with tab_graph:
        render_graph_tab()

# ingest tab
def render_ingest_tab(mistral_key, router_cfg, router_model):
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
            r = ocr_from_url(mistral_key, url_input)
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
                                pr = ocr_image(mistral_key, pg, "page_"+str(pi+1)+".png")
                            if pr["success"]:
                                combined.append(pr["text"])
                                for k in tu: tu[k] += pr.get("usage",{}).get(k,0)
                                tt += pr.get("elapsed",0)
                        ocr_results.append({"success":len(combined)>0,"text":"\n\n--- Page Break ---\n\n".join(combined),"source":uf.name,"method":"pdf_ocr","elapsed":round(tt,2),"usage":tu,"model":OCR_MODEL})
            else:
                with st.spinner("OCR on "+uf.name+"..."):
                    r = ocr_image(mistral_key, raw, uf.name)
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

# graph tab
def build_chatgpt_prompt(node, nodes, edges):
    """bangun prompt lengkap dari node + context buat kirim ke chatgpt"""
    label = node.get("label","")
    ntype = node.get("type","")
    desc = node.get("description","")
    parent = node.get("parent_topic","")
    sources = node.get("sources",[])
    
    prompt = "I'm studying the following topic from my knowledge graph. Please explain it in detail and help me learn more about it.\n\n"
    prompt += "## Topic: " + label + "\n"
    prompt += "**Type:** " + ntype + "\n"
    if desc: prompt += "**Description:** " + desc + "\n"
    if parent: prompt += "**Parent Topic:** " + parent + "\n"
    
    # ambil connected nodes
    nid = node.get("id","")
    connected = [e for e in edges if e.get("source")==nid or e.get("target")==nid]
    
    if connected:
        prompt += "\n## Related Topics:\n"
        for e in connected:
            other_id = e["target"] if e["source"]==nid else e["source"]
            other_node = nodes.get(other_id,{})
            other_label = other_node.get("label", other_id)
            other_desc = other_node.get("description","")
            relation = e.get("relation","")
            context = e.get("context","")
            prompt += "- **" + other_label + "** [" + relation + "]"
            if other_desc: prompt += ": " + other_desc
            prompt += "\n"
    
    if sources:
        prompt += "\n## Source Documents:\n"
        prompt += "This information comes from: " + ", ".join(sources) + "\n"
    
    prompt += "\nPlease:\n"
    prompt += "1. Explain **" + label + "** in detail\n"
    if connected:
        related_names = [nodes.get(e["target"] if e["source"]==nid else e["source"],{}).get("label","") for e in connected[:5]]
        prompt += "2. How does it relate to: " + ", ".join([n for n in related_names if n]) + "?\n"
        prompt += "3. What are the key concepts I should know?\n"
        prompt += "4. Suggest further topics to explore\n"
    else:
        prompt += "2. What are the key concepts I should know?\n"
        prompt += "3. What related topics should I explore?\n"
    
    return prompt

def render_graph_tab():
    graph = load_graph()
    nodes = graph.get("nodes",{})
    edges = graph.get("edges",[])
    
    if not nodes:
        st.info("Knowledge graph is empty. Go to the Ingest tab to add some documents.")
        return
    
    st.markdown("### Knowledge Graph")
    st.caption(str(len(nodes))+" nodes | "+str(len(edges))+" edges | "+str(len(graph.get("sources",[])))+" sources")
    
    # visualization
    html = build_graph_html(graph, height=650)
    if html:
        components.html(html, height=670, scrolling=True)
    else:
        st.warning("Install pyvis for graph visualization: pip install pyvis")
    
    st.markdown("---")
    st.markdown("### All Nodes")
    
    # filter
    filter_type = st.selectbox("Filter by type", ["All","main_topic","subtopic","entity","tag"])
    search_query = st.text_input("Search nodes", placeholder="Type to filter...")
    
    filtered = {}
    for nid, node in nodes.items():
        if filter_type != "All" and node.get("type") != filter_type: continue
        if search_query and search_query.lower() not in node.get("label","").lower(): continue
        filtered[nid] = node
    
    st.caption("Showing "+str(len(filtered))+" of "+str(len(nodes))+" nodes")
    
    # group by type
    for ntype in ["main_topic","subtopic","entity","tag"]:
        type_nodes = {k:v for k,v in filtered.items() if v.get("type")==ntype}
        if not type_nodes: continue
        
        type_label = ntype.replace("_"," ").title()+"s"
        st.markdown("#### "+type_label+" ("+str(len(type_nodes))+")")
        
        for nid, node in type_nodes.items():
            with st.expander(node.get("label",nid)):
                st.markdown("**Type:** "+node.get("type",""))
                if node.get("description"):
                    st.markdown("**Description:** "+node["description"])
                if node.get("parent_topic"):
                    st.markdown("**Parent:** "+node["parent_topic"])
                if node.get("sources"):
                    st.markdown("**Sources:** "+", ".join(node["sources"]))
                
                # connections
                connected = [e for e in edges if e.get("source")==nid or e.get("target")==nid]
                if connected:
                    st.markdown("**Connections:**")
                    for e in connected:
                        other = e["target"] if e["source"]==nid else e["source"]
                        other_label = nodes.get(other,{}).get("label",other)
                        direction = "--> " if e["source"]==nid else "<-- "
                        st.caption(direction+other_label+" ["+e.get("relation","")+"]"+(" | "+e.get("context","") if e.get("context") else ""))
                
                # ask chatgpt button
                st.markdown("---")
                prompt_text = build_chatgpt_prompt(node, nodes, edges)
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    # tombol buat buka chatgpt
                    chatgpt_url = "https://chatgpt.com/?ask=" + requests.utils.quote(prompt_text, safe="")
                    st.markdown("[Ask ChatGPT about this topic](" + chatgpt_url + ")", unsafe_allow_html=False)
                with col2:
                    # tombol buat liat prompt
                    if st.button("Preview Prompt", key="preview_"+nid):
                        st.text_area("Prompt to be sent:", value=prompt_text, height=200, key="prompt_"+nid)
    
    # danger zone
    st.markdown("---")
    st.markdown("### Danger Zone")
    if st.button("Reset Knowledge Graph", type="secondary"):
        st.warning("Click again to confirm. This will delete ALL nodes and edges.")
        if st.button("Confirm Reset"):
            save_graph({"nodes":{},"edges":[],"sources":[]})
            st.success("Knowledge graph has been reset.")
            st.rerun()

if __name__ == "__main__":
    main()
