import json, time
from datetime import datetime
from pathlib import Path
from db_guard import atomic_save, clean_str

FARM_FILE = Path("/app/data/farmers.json")

def get_farmers() -> list:
    return json.loads(FARM_FILE.read_text(encoding="utf-8")) if FARM_FILE.exists() else []

def add_farmer(kind: str, name: str, phone: str, farm: str, msg: str):
    items = get_farmers()
    now = time.time()
    n, p, m = clean_str(name, 100), clean_str(phone, 30), clean_str(msg, 1000)
    if not n or not m: return
    if any(x.get("phone") == p and x.get("msg") == m and (now - x.get("ts", 0)) < 300 for x in items): return
    items.insert(0, {"id": int(now * 1000), "ts": now, "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "kind": clean_str(kind, 80), "name": n, "phone": p, "farm": clean_str(farm, 150), "msg": m})
    atomic_save(FARM_FILE, items)

def del_farmer(fid: int):
    atomic_save(FARM_FILE, [x for x in get_farmers() if x.get("id") != fid])
