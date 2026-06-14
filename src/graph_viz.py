import json

import requests
def build_graph_html(graph, height=650, dark_mode=False):
    try:
        from pyvis.network import Network
    except ImportError:
        return None
    
    graph_bg = "#0f1117" if dark_mode else "#ffffff"
    graph_font = "#f4f4f5" if dark_mode else "#333333"
    edge_color = "#6b7280" if dark_mode else "#cccccc"
    net = Network(height=str(height)+"px", width="100%", bgcolor=graph_bg, font_color=graph_font, directed=True)
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
        
        # tooltip: hanya judul dan deskripsi
        title = '<b>' + label + '</b>'
        if desc:
            title += '<br><br>' + desc
        
        node["_chatgpt_url"] = chatgpt_url
        net.add_node(nid, label=label, title=title, color=st["color"], size=st["size"], shape=st["shape"], font={"size":14 if ntype=="main_topic" else 11,"color":graph_font})
    
    # buat edges
    for edge in edges:
        s = edge.get("source","")
        t = edge.get("target","")
        rel = edge.get("relation","")
        ctx = edge.get("context","")
        if s in nodes and t in nodes:
            net.add_edge(s, t, title=rel+(": "+ctx if ctx else ""), label=rel, font={"size":8,"align":"middle","color":graph_font,"strokeWidth":0}, color={"color":edge_color,"highlight":"#667eea"}, arrows={"to":{"enabled":True,"scaleFactor":0.5}})
    
    net.set_options('{"physics":{"barnesHut":{"gravitationalConstant":-3000,"centralGravity":0.3,"springLength":150,"springConstant":0.05,"damping":0.09},"minVelocity":0.75},"interaction":{"hover":true,"tooltipDelay":200,"navigationButtons":true,"keyboard":true}}')
    
    html = net.generate_html()
    html = html.replace("background-color: #ffffff;", "background-color: "+graph_bg+";")
    html = html.replace("background: #ffffff;", "background: "+graph_bg+";")
    graph_style = "<style>html,body,#mynetwork,.vis-network{background:"+graph_bg+" !important;color:"+graph_font+" !important;} .vis-label,.vis-network text{fill:"+graph_font+" !important;color:"+graph_font+" !important;}</style>"
    html = html.replace("</head>", graph_style + "</head>")
    
    # inject custom tooltip dengan tombol delete node
    node_info = {}
    for nid, node in nodes.items():
        t = node.get("label", nid)
        d = node.get("description", "No description")
        if d: d = d.replace('"', '&quot;').replace("'", "&#39;").replace("\n", "<br>")
        node_info[nid] = {"t": t, "d": d, "u": node.get("_chatgpt_url", "")}
    node_info_js = json.dumps(node_info)

    custom_js = """
    <div id="custom-tooltip" style="display:none;position:fixed;z-index:10000;background:#1e1e2e;color:#cdd6f4;border:1px solid #585b70;border-radius:8px;padding:12px 16px;max-width:320px;box-shadow:0 4px 16px rgba(0,0,0,0.4);font-family:system-ui,-apple-system,sans-serif;font-size:13px;pointer-events:auto;">
      <div id="ct-title" style="font-weight:700;font-size:14px;color:#cba6f7;margin-bottom:6px;"></div>
      <div id="ct-desc" style="color:#a6adc8;line-height:1.5;margin-bottom:10px;"></div>
      <button id="ct-chatgpt" style="background:#ffffff;color:#000000;border:1px solid #000000;border-radius:5px;padding:6px 14px;cursor:pointer;font-weight:700;font-size:12px;width:100%;margin-bottom:8px;">Ask ChatGPT</button>
      <button id="ct-delete" style="background:#f38ba8;color:#1e1e2e;border:none;border-radius:5px;padding:6px 14px;cursor:pointer;font-weight:600;font-size:12px;width:100%;">[Delete Node]</button>
    </div>
    <script>
    (function() {
      var NI = """ + node_info_js + """;
      var tt = document.getElementById('custom-tooltip');
      var ttTitle = document.getElementById('ct-title');
      var ttDesc = document.getElementById('ct-desc');
      var ttChatGPT = document.getElementById('ct-chatgpt');
      var ttDel = document.getElementById('ct-delete');
      var activeId = null;
      var activeUrl = '';

      network.on('click', function(p) {
        var ids = p.nodes;
        if (ids && ids.length > 0) {
          var nid = ids[0];
          var info = NI[nid];
          if (info) {
            activeId = nid;
            activeUrl = info.u || '';
            ttTitle.textContent = info.t;
            ttDesc.innerHTML = info.d;
            ttChatGPT.style.display = activeUrl ? 'block' : 'none';
            var ne = document.getElementById(nid);
            if (ne) {
              var r = ne.getBoundingClientRect();
              tt.style.left = Math.min(r.right + 10, window.innerWidth - 340) + 'px';
              tt.style.top = Math.max(r.top - 10, 5) + 'px';
            } else {
              tt.style.left = (p.pointer.DOM.x + 15) + 'px';
              tt.style.top = (p.pointer.DOM.y - 10) + 'px';
            }
            tt.style.display = 'block';
          }
        } else {
          tt.style.display = 'none';
          activeId = null;
          activeUrl = '';
        }
      });

      ttChatGPT.addEventListener('click', function(ev) {
        ev.stopPropagation();
        if (activeUrl) {
          window.open(activeUrl, '_blank', 'noopener,noreferrer');
        }
      });

      ttDel.addEventListener('click', function(ev) {
        ev.stopPropagation();
        if (activeId) {
          window.parent.postMessage({type:'streamlit:setComponentValue', value:activeId}, '*');
          tt.style.display = 'none';
          activeId = null;
          activeUrl = '';
        }
      });

      tt.addEventListener('click', function(ev) { ev.stopPropagation(); });
    })();
    </script>
    """
    html = html.replace("</body>", custom_js + "</body>")
    return html

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


