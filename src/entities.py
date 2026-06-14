import json
import time

import requests
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

