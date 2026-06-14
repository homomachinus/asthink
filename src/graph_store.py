import json
from datetime import datetime
from pathlib import Path

from .config import GRAPH_FILE
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

