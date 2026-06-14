import base64
import io
import time
from pathlib import Path

import requests

from .config import MAX_TOKENS, OCR_ENDPOINT, OCR_MODEL, get_mime
def call_mistral_ocr(api_key, payload):
    start = time.time()
    try:
        r = requests.post(OCR_ENDPOINT, headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"}, json=payload, timeout=120)
    except Exception as e:
        return {"success":False,"error":str(e),"text":"","elapsed":0}
    elapsed = time.time() - start
    if r.status_code != 200:
        detail = ""
        try:
            detail = r.json().get("message") or r.json().get("error",{}).get("message","")
        except Exception:
            detail = r.text[:160]
        msg = "HTTP "+str(r.status_code)
        if detail: msg += ": "+detail
        return {"success":False,"error":msg,"text":"","elapsed":elapsed}
    try:
        data = r.json()
    except Exception as e:
        return {"success":False,"error":"Invalid JSON response: "+str(e),"text":"","elapsed":elapsed}
    choices = data.get("choices",[])
    if not choices:
        return {"success":False,"error":"No text detected","text":"","elapsed":elapsed}
    return {"success":True,"text":choices[0].get("message",{}).get("content",""),"elapsed":round(elapsed,2),"usage":data.get("usage",{}),"model":data.get("model",OCR_MODEL)}

def ocr_with_key_manager(key_manager, payload):
    errors = []
    for key_info in key_manager.ordered_keys():
        result = call_mistral_ocr(key_info["key"], payload)
        result["key_index"] = key_info["index"]
        if result.get("success"):
            key_manager.report_success(key_info)
            if errors: result["fallback_errors"] = errors
            return result
        errors.append("api_key"+str(key_info["index"])+": "+result.get("error","Unknown error"))
        key_manager.report_failure(key_info)
    return {"success":False,"error":"All Mistral API keys failed: "+" | ".join(errors),"text":"","elapsed":0,"fallback_errors":errors}

def ocr_image(key_manager, img_bytes, filename):
    mime = get_mime(filename)
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    payload = {
        "model": OCR_MODEL, "max_tokens": MAX_TOKENS,
        "messages": [
            {"role":"system","content":"You are a highly accurate OCR engine. Extract ALL text from the image with maximum fidelity. Preserve paragraphs, line breaks, headings. Convert tables to markdown. Preserve lists. Output ONLY extracted text. No commentary."},
            {"role":"user","content":[{"type":"text","text":"Extract all text from this document."},{"type":"image_url","image_url":"data:"+mime+";base64,"+b64}]}
        ]
    }
    return ocr_with_key_manager(key_manager, payload)

def ocr_from_url(key_manager, url):
    payload = {
        "model": OCR_MODEL, "max_tokens": MAX_TOKENS,
        "messages": [
            {"role":"system","content":"You are a highly accurate OCR engine. Extract ALL text. Preserve structure. Output ONLY text."},
            {"role":"user","content":[{"type":"text","text":"Extract all text from this document."},{"type":"image_url","image_url":url}]}
        ]
    }
    return ocr_with_key_manager(key_manager, payload)

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

