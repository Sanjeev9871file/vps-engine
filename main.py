import os
import random
import string
import time
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from supabase import Client, create_client

app = FastAPI(title="VPS Cloud & Multi-AI Automation Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Clean & Secure Secrets Vault ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

MEGA_EMAIL = os.getenv("MEGA_EMAIL", "")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def get_supabase() -> Client:
  if not SUPABASE_URL or not SUPABASE_KEY:
    raise HTTPException(status_code=500, detail="Supabase credentials not configured in environment")
  return create_client(SUPABASE_URL, SUPABASE_KEY)


def send_telegram_alert(text: str):
  if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    return
  try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    requests.post(url, json=payload, timeout=8)
  except Exception as e:
    print(f"Telegram Alert Error: {e}")


# --- Multi-Provider AI Inference Gateway ---
def call_llm(provider: str, prompt: str) -> str:
  try:
    provider = provider.lower().strip()

    if provider == "groq":
      if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY is not set."
      url = "https://api.groq.com/openai/v1/chat/completions"
      headers = {
          "Authorization": f"Bearer {GROQ_API_KEY}",
          "Content-Type": "application/json",
      }
      payload = {
          "model": "llama-3.1-8b-instant",
          "messages": [{"role": "user", "content": prompt}],
      }
      r = requests.post(url, json=payload, headers=headers, timeout=20)
      return r.json()["choices"][0]["message"]["content"]

    elif provider == "nvidia":
      if not NVIDIA_API_KEY:
        return "Error: NVIDIA_API_KEY is not set."
      url = "https://integrate.api.nvidia.com/v1/chat/completions"
      headers = {
          "Authorization": f"Bearer {NVIDIA_API_KEY}",
          "Content-Type": "application/json",
      }
      payload = {
          "model": "meta/llama-3.1-70b-instruct",
          "messages": [{"role": "user", "content": prompt}],
      }
      r = requests.post(url, json=payload, headers=headers, timeout=25)
      return r.json()["choices"][0]["message"]["content"]

    elif provider == "cerebras":
      if not CEREBRAS_API_KEY:
        return "Error: CEREBRAS_API_KEY is not set."
      url = "https://api.cerebras.ai/v1/chat/completions"
      headers = {
          "Authorization": f"Bearer {CEREBRAS_API_KEY}",
          "Content-Type": "application/json",
      }
      payload = {
          "model": "llama3.1-8b",
          "messages": [{"role": "user", "content": prompt}],
      }
      r = requests.post(url, json=payload, headers=headers, timeout=20)
      return r.json()["choices"][0]["message"]["content"]

    elif provider == "mistral":
      if not MISTRAL_API_KEY:
        return "Error: MISTRAL_API_KEY is not set."
      url = "https://api.mistral.ai/v1/chat/completions"
      headers = {
          "Authorization": f"Bearer {MISTRAL_API_KEY}",
          "Content-Type": "application/json",
      }
      payload = {
          "model": "mistral-small-latest",
          "messages": [{"role": "user", "content": prompt}],
      }
      r = requests.post(url, json=payload, headers=headers, timeout=20)
      return r.json()["choices"][0]["message"]["content"]

    elif provider == "openrouter":
      if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY is not set."
      url = "https://openrouter.ai/api/v1/chat/completions"
      headers = {
          "Authorization": f"Bearer {OPENROUTER_API_KEY}",
          "Content-Type": "application/json",
      }
      payload = {
          "model": "meta-llama/llama-3.1-8b-instruct:free",
          "messages": [{"role": "user", "content": prompt}],
      }
      r = requests.post(url, json=payload, headers=headers, timeout=25)
      return r.json()["choices"][0]["message"]["content"]

    elif provider == "gemini":
      if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY is not set."
      url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
      payload = {
          "contents": [{"parts": [{"text": prompt}]}],
      }
      r = requests.post(url, json=payload, timeout=20)
      return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    return f"Unsupported provider: {provider}"

  except Exception as err:
    return f"AI Generation Error ({provider}): {str(err)}"


# --- Storage Orchestrator ---
def get_provider_usage(provider: str) -> int:
  try:
    supabase = get_supabase()
    res = (
        supabase.table("file_registry")
        .select("file_size_bytes")
        .eq("storage_provider", provider)
        .execute()
    )
    return sum(item["file_size_bytes"] for item in res.data)
  except Exception:
    return 0


def select_storage_target(file_size: int) -> str:
  if get_provider_usage("supabase") + file_size < 50 * 1024 * 1024:
    return "supabase"
  if get_provider_usage("mega") + file_size < 20 * 1024 * 1024 * 1024:
    return "mega"
  return "terabox_archive"


@app.get("/")
def read_root():
  return {"status": "VPS Engine API is Live"}


@app.get("/api/storage/metrics")
def get_storage_stats():
  try:
    supabase = get_supabase()
    res = (
        supabase.table("file_registry")
        .select("*")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return {
        "tiers": {
            "supabase": {
                "used_bytes": get_provider_usage("supabase"),
                "limit_bytes": 1024 * 1024 * 1024,
            },
            "mega": {
                "used_bytes": get_provider_usage("mega"),
                "limit_bytes": 20 * 1024 * 1024 * 1024,
            },
            "terabox": {"used_bytes": 0, "limit_bytes": 1024 * 1024 * 1024 * 1024},
        },
        "recent_files": res.data,
    }
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/storage/upload")
async def upload_file_to_pool(file: UploadFile = File(...)):
  try:
    content = await file.read()
    file_size = len(content)
    target = select_storage_target(file_size)
    download_url = "#"
    file_path = f"pool/{file.filename}"

    if target == "mega" and MEGA_EMAIL and MEGA_PASSWORD:
      try:
        from mega import Mega
        mega = Mega()
        m = mega.login(MEGA_EMAIL, MEGA_PASSWORD)
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
          f.write(content)
        uploaded = m.upload(temp_path)
        download_url = m.get_upload_link(uploaded)
        file_path = f"mega://{file.filename}"
        if os.path.exists(temp_path):
          os.remove(temp_path)
      except Exception:
        target = "supabase"
        download_url = f"{SUPABASE_URL}/storage/v1/object/public/system/{file_path}"
    else:
      target = "supabase"
      download_url = f"{SUPABASE_URL}/storage/v1/object/public/system/{file_path}"

    supabase = get_supabase()
    supabase.table("file_registry").insert({
        "file_name": file.filename,
        "file_size_bytes": file_size,
        "storage_provider": target,
        "file_path": file_path,
        "download_url": download_url,
    }).execute()

    send_telegram_alert(
        f"File Saved: {file.filename} ({file_size} bytes) -> {target.upper()}"
    )

    return {
        "status": "success",
        "routed_tier": target,
        "filename": file.filename,
        "size": file_size,
        "url": download_url,
    }
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


# --- AI Execution Endpoint ---
class RunAIRequest(BaseModel):
  provider: str = "groq"
  prompt: str


@app.post("/api/ai/execute")
def run_ai_task(req: RunAIRequest):
  result = call_llm(req.provider, req.prompt)
  return {"provider": req.provider, "output": result}


# --- VPS Lifecycle Handlers ---
class VPSRequest(BaseModel):
  name: str
  os: str = "Ubuntu 24.04 LTS"


@app.post("/api/create-vps")
def create_vps(req: VPSRequest):
  fake_ip = f"{random.randint(45, 185)}.{random.randint(10, 200)}.{random.randint(1, 254)}.{random.randint(2, 250)}"
  chars = string.ascii_letters + string.digits + "@#$"
  password = "".join(random.choice(chars) for _ in range(12))

  supabase = get_supabase()
  supabase.table("servers").insert({
      "name": req.name,
      "ip_address": fake_ip,
      "os_name": req.os,
      "status": "running",
      "root_password": password,
  }).execute()

  send_telegram_alert(f"VPS Node Provisioned: {req.name} ({req.os}) at {fake_ip}")
  return {"status": "success", "ip": fake_ip}


@app.get("/api/servers")
def get_servers():
  try:
    supabase = get_supabase()
    res = (
        supabase.table("servers")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return {"servers": res.data}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/servers/{server_id}")
def delete_server(server_id: str):
  try:
    supabase = get_supabase()
    val = int(server_id) if server_id.isdigit() else server_id
    supabase.table("servers").delete().eq("id", val).execute()
    return {"status": "success"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
