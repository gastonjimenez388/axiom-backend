# ARCHIVO: axiom_backend.py
# AXIOM - Central Backend v2.1 (Optimized for Deployment)

import os
import json
import base64
import requests
import urllib.parse
import urllib.request
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="ui")
CORS(app, resources={r"/api/*": {"origins": "https://www.aeronexares.com"}})

# Configuración mediante variables de entorno con valores por defecto
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
BASE_DIR = os.getenv("AXIOM_DATA_DIR", "./data")
SHARED_BOX = os.path.join(BASE_DIR, "Resources")
AVATARS_DIR = os.path.join(BASE_DIR, "Avatares")
REPORTS_DIR = os.path.join(BASE_DIR, "Reports")
CHAT_LOG = os.path.join(BASE_DIR, "chat_log.json")

AGENTS = {
    "ORION": {"model": "llama3:8b", "role": "Master orchestrator of AXIOM."},
    "NOVA": {"model": "llama3:8b", "model_vision": "moondream", "role": "Visual intelligence."},
    "PRAXA": {"model": "initium/law_model", "role": "Legal counsel and process expert."},
    "CIPHER": {"model": "qwen2.5-coder:7b", "role": "Senior IT engineer and developer."},
    "ATLAS": {"model": "llama3:8b", "role": "Knowledge base."},
    "LUMEN": {"model": "llama3:8b", "generates_image": True, "role": "Creative director."},
    "VAULT": {"model": "llama3:8b", "role": "Finance and cost intelligence."},
}

LANG_RULE = {
    "es": "CRITICAL RULE: You MUST respond ONLY in Spanish.",
    "en": "CRITICAL RULE: You MUST respond ONLY in English.",
    "zh": "CRITICAL RULE: You MUST respond ONLY in Chinese.",
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] AXIOM: {msg}")

def orion_route(user_msg, has_image, selected_agent, lang):
    import re
    msg_upper = user_msg.upper()
    agent_names = list(AGENTS.keys())
    if has_image and not any(n in msg_upper for n in agent_names):
        return "NOVA"
    mentioned = [n for n in agent_names if n in msg_upper]
    if not mentioned: return selected_agent
    if len(mentioned) == 1: return mentioned[0]
    action_verbs = ["PODES", "PUEDES", "CAN", "COULD", "WOULD", "SHOULD", "SABES", "DIME", "EXPLICA", "ANALIZA"]
    for name in mentioned:
        idx = msg_upper.find(name)
        after = msg_upper[idx + len(name):idx + len(name) + 40]
        if any(v in after for v in action_verbs): return name
    return mentioned[-1]

def ollama_chat(model, system_prompt, user_message, image_b64=None):
    if image_b64:
        payload = {"model": model, "prompt": f"{system_prompt}\n\nDescribe precisely.", "images": [image_b64], "stream": False, "options": {"num_predict": 500}}
        endpoint = f"{OLLAMA_HOST}/api/generate"
    else:
        payload = {"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}], "stream": False, "options": {"num_predict": 600}}
        endpoint = f"{OLLAMA_HOST}/api/chat"
    try:
        r = requests.post(endpoint, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "") if image_b64 else data.get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {str(e)}"

def save_chat(agent, user_msg, response):
    os.makedirs(os.path.dirname(CHAT_LOG), exist_ok=True)
    history = []
    if os.path.exists(CHAT_LOG):
        try:
            with open(CHAT_LOG, "r", encoding="utf-8") as f: history = json.load(f)
        except: history = []
    history.append({"ts": datetime.now().isoformat(), "agent": agent, "user": user_msg, "response": response})
    with open(CHAT_LOG, "w", encoding="utf-8") as f: json.dump(history[-200:], f, ensure_ascii=False, indent=2)

@app.route("/")
def index(): return send_from_directory("ui", "axiom_ui.html")

@app.route("/api/status")
def status():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        return jsonify({"ollama": True, "models": models, "agents": list(AGENTS.keys()), "version": "AXIOM-PROD-2.1"})
    except: return jsonify({"ollama": False})

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_msg = data.get("message", "").strip()
    selected = data.get("agent", "ORION").upper()
    image_b64 = data.get("image_b64", None)
    lang = data.get("lang", "es")
    if not user_msg: return jsonify({"error": "Empty message"}), 400
    agent_name = orion_route(user_msg, bool(image_b64), selected, lang)
    agent = AGENTS.get(agent_name, AGENTS["ORION"])
    system_prompt = f"You are {agent_name}. Role: {agent['role']}. {LANG_RULE.get(lang, LANG_RULE['es'])}"
    model_to_use = agent.get("model_vision", agent["model"]) if (image_b64 and agent_name == "NOVA") else agent["model"]
    response = ollama_chat(model_to_use, system_prompt, user_msg, image_b64)
    save_chat(agent_name, user_msg, response)
    return jsonify({"agent": agent_name, "response": response, "ts": datetime.now().isoformat()})

@app.route("/api/sharedbox/list")
def sharedbox_list():
    os.makedirs(SHARED_BOX, exist_ok=True)
    files = [{"name": f, "size": os.path.getsize(os.path.join(SHARED_BOX, f))} for f in os.listdir(SHARED_BOX)]
    return jsonify(files)

if __name__ == "__main__":
    os.makedirs(SHARED_BOX, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
