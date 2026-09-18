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


def get_supabase() -> Client:
  if not SUPABASE_KEY:
    raise HTTPException(status_code=500, detail="Supabase key not configured")
  return create_client(SUPABASE_URL, SUPABASE_KEY)


class VPSRequest(BaseModel):
  name: str
  os: str = "Ubuntu 24.04 LTS"


class CommandRequest(BaseModel):
  command: str


@app.get("/")
def read_root():
  return {"status": "VPS Engine API is Live"}


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

  return {
      "status": "success",
      "server": {
          "name": req.name,
          "os": req.os,
          "ip": fake_ip,
          "root_password": password,
      },
  }


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
    return {"status": "success", "message": "Server terminated successfully"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/servers/{server_id}/toggle")
def toggle_status(server_id: str):
  try:
    supabase = get_supabase()
    val = int(server_id) if server_id.isdigit() else server_id

    res = (
        supabase.table("servers").select("status").eq("id", val).single().execute()
    )
    current_status = res.data.get("status", "running")
    new_status = "stopped" if current_status == "running" else "running"

    supabase.table("servers").update({"status": new_status}).eq(
        "id", val
    ).execute()
    return {"status": "success", "new_status": new_status}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/servers/{server_id}/exec")
def exec_terminal(server_id: str, req: CommandRequest):
  cmd = req.command.strip().lower()
  if cmd == "uname -a":
    output = "Linux vps-node 6.8.0-generic #1 SMP PREEMPT_DYNAMIC x86_64 GNU/Linux"
  elif cmd == "uptime":
    output = "up 14 days, 3 hours, 22 min, 1 user, load average: 0.12, 0.08, 0.05"
  elif cmd == "whoami":
    output = "root"
  elif cmd in ["ls", "ls -la"]:
    output = "total 28\ndrwx------ 4 root root 4096 Sep 18 02:00 .\ndrwxr-xr-x 19 root root 4096 Sep 18 01:15 ..\n-rw-r--r-- 1 root root 3106 Apr 22 2024 .bashrc\n-rw-r--r-- 1 root root  161 Jul  9 2019 .profile"
  elif cmd in ["free -h", "free -m"]:
    output = (
        "               total        used        free      shared  buff/cache"
        "   available\nMem:           2.0Gi       480Mi       1.2Gi        12Mi"
        "       360Mi       1.5Gi\nSwap:          1.0Gi          0B       1.0Gi"
    )
  elif cmd == "df -h":
    output = "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        40G  4.2G   34G  11% /\ntmpfs           1.0G     0  1.0G   0% /dev/shm"
  elif cmd == "clear":
    output = "__CLEAR__"
  else:
    output = f"bash: {cmd}: command not found (try: uname -a, uptime, whoami, ls, free -h, df -h)"

  return {"command": req.command, "output": output}
