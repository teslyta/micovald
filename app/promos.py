import json, time
from datetime import datetime
from pathlib import Path
from db_guard import atomic_save, clean_str

PROMO_FILE = Path("/app/data/promos.json")

def get_promos() -> list:
    if not PROMO_FILE.exists(): return []
    items = json.loads(PROMO_FILE.read_text(encoding="utf-8"))
    today = datetime.now().strftime("%Y-%m-%d")
    changed = False
    for p in items:
        if p.get("active") and p.get("end_date") and p["end_date"] < today:
            p["active"] = False
            changed = True
    if changed: atomic_save(PROMO_FILE, items)
    return items

def get_active_promo():
    today = datetime.now().strftime("%Y-%m-%d")
    for p in get_promos():
        if p.get("active") and p.get("start_date", "") <= today <= p.get("end_date", "9999-12-31"):
            return p
    return None

def save_promo(pid: int, title: str, desc: str, discount: int, start_date: str, end_date: str, target_cat: str = ""):
    items = get_promos()
    for p in items: p["active"] = False
    t, d, tc = clean_str(title, 120), clean_str(desc, 500), clean_str(target_cat, 80)
    disc = max(1, min(90, int(discount)))
    if pid > 0:
        for p in items:
            if p["id"] == pid:
                p.update({"title": t, "desc": d, "discount": disc, "start_date": start_date, "end_date": end_date, "target_cat": tc, "active": True})
                break
    else:
        items.insert(0, {"id": int(time.time() * 1000), "title": t, "desc": d, "discount": disc, "start_date": start_date, "end_date": end_date, "target_cat": tc, "active": True})
    atomic_save(PROMO_FILE, items)

def archive_promo(pid: int):
    items = get_promos()
    for p in items:
        if p["id"] == pid: p["active"] = False
    atomic_save(PROMO_FILE, items)
