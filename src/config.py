from pathlib import Path
import json
import streamlit as st

KEY_FILE = "key.json"
GRAPH_FILE = "knowledge_graph.json"
VECTOR_FILE = "output/brain_vector_index.json"
OCR_ENDPOINT = "https://api.mistral.ai/v1/ocr"
OCR_MODEL = "mistral-ocr-latest"
MAX_TOKENS = 4096
SUPPORTED_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp", "gif", "pdf"]
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
@st.cache_resource
def load_keys():
    p = Path(KEY_FILE)
    if not p.exists(): return {}
    try:
        with open(p, "r") as f: return json.load(f)
    except: return {}

def get_mistral_config(k):
    c = k.get("mistral",{})
    keys = []
    for i in range(1, 8):
        key = c.get("api_key"+str(i), "").strip()
        if key: keys.append({"index":i,"key":key})
    legacy_key = c.get("api_key", "").strip()
    if legacy_key and not keys:
        keys.append({"index":1,"key":legacy_key})
    mode = c.get("usage_mode", "sequential").strip().lower().replace("_", "-")
    if mode in ["roundrobin", "round-robin"]: mode = "round_robin"
    elif mode == "sequential": mode = "sequential"
    else: mode = "invalid"
    errors = []
    if len(keys) < 7:
        errors.append("Mistral needs 7 keys: api_key1 sampai api_key7.")
    if mode == "invalid":
        errors.append("mistral.usage_mode harus `sequential` atau `round_robin`.")
    return {"keys":keys,"usage_mode":mode,"errors":errors}

def get_router_config(k):
    c = k.get("9router",{})
    return {"api_key": c.get("api_key","").strip(), "base_url": c.get("base_url","http://localhost:20128/v1").strip(), "model": c.get("model","").strip()}

def get_mime(f):
    e = Path(f).suffix.lower()
    m = {".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".bmp":"image/bmp",".tiff":"image/tiff",".tif":"image/tiff",".webp":"image/webp",".gif":"image/gif",".pdf":"application/pdf"}
    return m.get(e, "image/jpeg")





