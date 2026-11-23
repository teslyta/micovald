import json, time
from datetime import datetime
from pathlib import Path
from db_guard import atomic_save, clean_str

STAT_FILE = Path("/app/data/analytics.json")

def get_stats() -> dict:
    if not STAT_FILE.exists(): return {"visits": {}, "missed": []}
    return json.loads(STAT_FILE.read_text(encoding="utf-8"))

def track_visit(vid: str, user: str, path: str, ordered: bool = False):
    if path.startswith(("/media", "/api", "/favicon")): return
    st = get_stats()
    now = time.time()
    v = st["visits"].get(vid, {"vid": vid[:8], "user": "Гость", "start": now, "last": now, "date": datetime.now().strftime("%d.%m %H:%M"), "pages": [], "ordered": False})
    if user: v["user"] = user
    if ordered: v["ordered"] = True
    v["last"] = now
    if not v["pages"] or v["pages"][-1] != path: v["pages"].append(path)
    v["pages"] = v["pages"][-12:]
    st["visits"][vid] = v
    if len(st["visits"]) > 150:
        oldest = sorted(st["visits"].keys(), key=lambda k: st["visits"][k]["last"])[:30]
        for k in oldest: st["visits"].pop(k, None)
    atomic_save(STAT_FILE, st)

def track_missed_search(q: str, user: str):
    clean_q = clean_str(q, 80)
    if len(clean_q) < 2: return
    st = get_stats()
    st["missed"].insert(0, {"date": datetime.now().strftime("%d.%m %H:%M"), "q": clean_q, "user": user or "Гость"})
    st["missed"] = st["missed"][:50]
    atomic_save(STAT_FILE, st)
