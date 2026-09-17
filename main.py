import os
import random
import string
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import Client, create_client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL", "https://ehxjgvekembxtfurofqc.supabase.co"
)
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


class VPSRequest(BaseModel):
  name: str
  os: str = "Ubuntu 24.04 LTS"


@app.get("/")
def read_root():
  return {"status": "VPS Engine API is Live"}


@app.post("/api/create-vps")
def create_vps(req: VPSRequest):
  fake_ip = f"{random.randint(45, 185)}.{random.randint(10, 200)}.{random.randint(1, 254)}.{random.randint(2, 250)}"
  chars = string.ascii_letters + string.digits + "@#$"
  password = "".join(random.choice(chars) for _ in range(12))

  # Save server in Supabase if key is configured
  if SUPABASE_KEY:
    try:
      supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
      supabase.table("servers").insert({
          "name": req.name,
          "ip_address": fake_ip,
          "os_name": req.os,
          "status": "running",
          "root_password": password,
      }).execute()
    except Exception as e:
      print(f"DB Error: {e}")

  return {
      "status": "success",
      "server": {
          "name": req.name,
          "os": req.os,
          "ip": fake_ip,
          "root_password": password,
          "ssh_command": f"ssh root@{fake_ip}",
      },
  }


@app.get("/api/servers")
def get_servers():
  if not SUPABASE_KEY:
    return {"servers": []}
  try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    res = (
        supabase.table("servers")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return {"servers": res.data}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
