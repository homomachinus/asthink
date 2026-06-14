import requests
import streamlit as st
import streamlit.components.v1 as components

from ..graph_store import load_graph, save_graph
from ..graph_viz import build_chatgpt_prompt, build_graph_html
def handle_node_deletion(nid):
    graph = load_graph()
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])
    
    # collect node + all subnodes recursively
    to_delete = set()
    queue = [nid]
    while queue:
        current = queue.pop(0)
        if current in to_delete:
            continue
        to_delete.add(current)
        # find children (nodes whose parent_topic matches this node's label)
        current_label = nodes.get(current, {}).get("label", "")
        for cid, cnode in nodes.items():
            if cid not in to_delete and cnode.get("parent_topic") == current_label:
                queue.append(cid)
    
    # remove nodes
    for did in to_delete:
        nodes.pop(did, None)
    
    # remove edges connected to any deleted node
    edges = [e for e in edges if e.get("source") not in to_delete and e.get("target") not in to_delete]
    
    graph["nodes"] = nodes
    graph["edges"] = edges
    save_graph(graph)
    return len(to_delete)


def render_graph_tab():
    # handle node deletion from graph visualization
    if st.session_state.get("_delete_node_request"):
        nid = st.session_state.pop("_delete_node_request")
        count = handle_node_deletion(nid)
        st.success(f"Deleted {count} node(s) and their connections.")
        st.rerun()
    
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

