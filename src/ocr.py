import base64
import io
import time

import requests

from .config import OCR_ENDPOINT, OCR_MODEL, get_mime


def call_mistral_ocr(api_key, payload):
    start = time.time()
    try:
        response = requests.post(
            OCR_ENDPOINT,
            headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
            json=payload,
            timeout=120,
        )
    except Exception as exc:
        return {"success":False,"error":str(exc),"text":"","elapsed":0}
    elapsed = time.time() - start
    if response.status_code != 200:
        detail = ""
        try:
            body = response.json()
            detail = body.get("message") or body.get("error",{}).get("message","")
        except Exception:
            detail = response.text[:160]
        msg = "HTTP "+str(response.status_code)
        if detail:
            msg += ": "+detail
        return {"success":False,"error":msg,"text":"","elapsed":elapsed}
    try:
        data = response.json()
    except Exception as exc:
        return {"success":False,"error":"Invalid JSON response: "+str(exc),"text":"","elapsed":elapsed}
    text_parts = []
    for page in data.get("pages", []):
        markdown = page.get("markdown", "")
        if markdown and markdown.strip():
            text_parts.append(markdown.strip())
    text = "\n\n--- Page Break ---\n\n".join(text_parts)
    if not text.strip():
        return {"success":False,"error":"OCR returned no markdown text","text":"","elapsed":elapsed}
    return {"success":True,"text":text,"elapsed":round(elapsed,2),"usage":data.get("usage_info",{}),"model":data.get("model",OCR_MODEL)}


def ocr_with_key_manager(key_manager, payload):
    errors = []
    for key_info in key_manager.ordered_keys():
        result = call_mistral_ocr(key_info["key"], payload)
        result["key_index"] = key_info["index"]
        if result.get("success"):
            key_manager.report_success(key_info)
            if errors:
                result["fallback_errors"] = errors
            return result
        errors.append("api_key"+str(key_info["index"])+": "+result.get("error","Unknown error"))
        key_manager.report_failure(key_info)
    return {"success":False,"error":"All Mistral API keys failed: "+" | ".join(errors),"text":"","elapsed":0,"fallback_errors":errors}


def ocr_image(key_manager, img_bytes, filename):
    mime = get_mime(filename)
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    payload = {
        "model": OCR_MODEL,
        "document": {"type":"image_url", "image_url":"data:"+mime+";base64,"+b64},
        "include_image_base64": False,
    }
    return ocr_with_key_manager(key_manager, payload)


def ocr_from_url(key_manager, url):
    payload = {
        "model": OCR_MODEL,
        "document": {"type":"image_url", "image_url":url},
        "include_image_base64": False,
    }
    return ocr_with_key_manager(key_manager, payload)


def ocr_pdf(key_manager, pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    payload = {
        "model": OCR_MODEL,
        "document": {"type":"document_url", "document_url":"data:application/pdf;base64,"+b64},
        "include_image_base64": False,
    }
    result = ocr_with_key_manager(key_manager, payload)
    result["source"] = filename
    result["method"] = "pdf_ocr"
    return result


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
        for p in doc:
            imgs.append(p.get_pixmap(matrix=mat).tobytes("png"))
        doc.close()
    except: pass
    return imgs