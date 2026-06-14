import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

from .config import VECTOR_FILE
from .graph_store import load_graph

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
VECTOR_DIMS = 512


def tokenize(text):
    return [t.lower() for t in TOKEN_RE.findall(text or "")]


def chunk_text(text, source, method="text", chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return []
    chunks = []
    start = 0
    idx = 0
    while start < len(clean):
        part = clean[start:start + chunk_size].strip()
        if part:
            stable = source + ":" + method + ":" + str(idx) + ":" + part[:80]
            chunk_id = hashlib.sha1(stable.encode("utf-8")).hexdigest()[:16]
            chunks.append({
                "id": chunk_id,
                "source": source,
                "method": method,
                "chunk_index": idx,
                "text": part,
                "created_at": datetime.now().isoformat(),
            })
        idx += 1
        if start + chunk_size >= len(clean):
            break
        start += max(1, chunk_size - overlap)
    return chunks


def text_vector(text):
    tokens = tokenize(text)
    if not tokens:
        return {}
    counts = {}
    for token in tokens:
        bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % VECTOR_DIMS
        counts[bucket] = counts.get(bucket, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {str(k): v / norm for k, v in counts.items()}


def cosine_sparse(a, b):
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(key, 0.0) for key, value in a.items())


def load_vector_index():
    path = Path(VECTOR_FILE)
    if not path.exists():
        return {"chunks": [], "updated_at": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"chunks": [], "updated_at": None}


def save_vector_index(index):
    index["updated_at"] = datetime.now().isoformat()
    with open(VECTOR_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def add_texts_to_index(items):
    index = load_vector_index()
    existing_ids = {chunk.get("id") for chunk in index.get("chunks", [])}
    new_chunks = []
    for item in items:
        source = item.get("source", "Unknown")
        method = item.get("method", "text")
        text = item.get("text", "")
        for chunk in chunk_text(text, source, method):
            if chunk["id"] in existing_ids:
                continue
            chunk["vector"] = text_vector(chunk["text"])
            new_chunks.append(chunk)
            existing_ids.add(chunk["id"])
    if new_chunks:
        index["chunks"] = index.get("chunks", []) + new_chunks
        save_vector_index(index)
    return len(new_chunks)


def graph_context_documents():
    graph = load_graph()
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])
    docs = []
    for nid, node in nodes.items():
        parts = [
            "Node: " + node.get("label", nid),
            "Type: " + node.get("type", ""),
        ]
        if node.get("description"):
            parts.append("Description: " + node.get("description", ""))
        if node.get("parent_topic"):
            parts.append("Parent: " + node.get("parent_topic", ""))
        related = []
        for edge in edges:
            if edge.get("source") == nid or edge.get("target") == nid:
                other_id = edge.get("target") if edge.get("source") == nid else edge.get("source")
                other_label = nodes.get(other_id, {}).get("label", other_id)
                related.append(other_label + " [" + edge.get("relation", "related_to") + "]")
        if related:
            parts.append("Related: " + ", ".join(related[:12]))
        docs.append({
            "id": "graph_" + nid,
            "source": "Knowledge Graph",
            "method": "graph_node",
            "chunk_index": 0,
            "text": "\n".join(parts),
            "vector": text_vector("\n".join(parts)),
        })
    return docs


def search_brain(query, top_k=6, include_graph=True):
    query_vector = text_vector(query)
    docs = load_vector_index().get("chunks", [])
    if include_graph:
        docs = docs + graph_context_documents()
    scored = []
    for doc in docs:
        score = cosine_sparse(query_vector, doc.get("vector", {}))
        if score > 0:
            scored.append({**doc, "score": score})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def rebuild_index_from_graph():
    graph_docs = graph_context_documents()
    index = {"chunks": graph_docs, "updated_at": datetime.now().isoformat()}
    save_vector_index(index)
    return len(graph_docs)
