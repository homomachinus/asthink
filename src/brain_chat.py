import time

import requests

from .vector_store import search_brain


def call_router_chat(config, messages, model_override="", max_tokens=1200):
    base_url = config["base_url"].rstrip("/")
    endpoint = base_url + "/chat/completions"
    model = model_override.strip() or config.get("model", "").strip() or "gpt-4o-mini"
    headers = {"Content-Type": "application/json"}
    if config.get("api_key"):
        headers["Authorization"] = "Bearer " + config["api_key"]
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "stream": False,
        "messages": messages,
    }
    start = time.time()
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Gak bisa connect ke 9Router di " + config["base_url"], "elapsed": 0}
    except Exception as exc:
        return {"success": False, "error": str(exc), "elapsed": 0}
    elapsed = time.time() - start
    if response.status_code != 200:
        return {"success": False, "error": "HTTP " + str(response.status_code) + ": " + response.text[:500], "elapsed": elapsed}
    try:
        data = response.json()
    except Exception:
        return {"success": False, "error": "Non-JSON response: " + response.text[:500], "elapsed": elapsed}
    choices = data.get("choices", [])
    if not choices:
        return {"success": False, "error": "Empty response", "elapsed": elapsed}
    return {
        "success": True,
        "answer": choices[0].get("message", {}).get("content", ""),
        "elapsed": round(elapsed, 2),
        "model": data.get("model", model),
        "usage": data.get("usage", {}),
    }


def build_context(results):
    blocks = []
    for idx, item in enumerate(results, start=1):
        source = item.get("source", "Unknown")
        method = item.get("method", "text")
        score = round(item.get("score", 0), 3)
        text = item.get("text", "")
        blocks.append("[" + str(idx) + "] Source: " + source + " | Type: " + method + " | Score: " + str(score) + "\n" + text)
    return "\n\n".join(blocks)


def ask_brain(config, question, chat_history=None, model_override="", top_k=6):
    results = search_brain(question, top_k=top_k, include_graph=True)
    context = build_context(results)
    history = chat_history or []
    recent_history = history[-6:]
    system = "You are a helpful second-brain assistant. Answer using the retrieved context and knowledge graph context first. If the context is insufficient, say what is missing. Cite sources inline like [1], [2] when using them. Be concise but useful."
    user = "Retrieved context:\n" + (context or "No matching context found.") + "\n\nQuestion: " + question
    messages = [{"role": "system", "content": system}]
    for item in recent_history:
        role = item.get("role")
        content = item.get("content", "")
        if role in ["user", "assistant"] and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user})
    response = call_router_chat(config, messages, model_override=model_override)
    response["results"] = results
    return response
