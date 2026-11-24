import json, time
from pathlib import Path

CHAT_FILE = Path("/app/data/chats.json")

def load_chats():
    if not CHAT_FILE.exists(): return {}
    try: data = json.loads(CHAT_FILE.read_text(encoding="utf-8"))
    except Exception: return {}
    now_ms = int(time.time() * 1000)
    cutoff = now_ms - 24 * 3600 * 1000
    cleaned = {}
    changed = False
    for u, msgs in data.items():
        if not msgs: continue
        last_id = max((int(m.get("id", now_ms)) for m in msgs), default=now_ms)
        if last_id >= cutoff: cleaned[u] = msgs
        else: changed = True
    if changed: save_chats(cleaned)
    return cleaned

def save_chats(data):
    CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHAT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CHAT_FILE)

def add_chat_msg(username: str, sender: str, text: str, prod_name: str = ""):
    if not username or not text.strip(): return
    data = load_chats()
    msgs = data.setdefault(username, [])
    msgs.append({
        "id": int(time.time() * 1000),
        "sender": sender,
        "text": text.strip()[:1000],
        "prod": prod_name.strip()[:120],
        "ts": time.strftime("%d.%m.%Y %H:%M"),
        "read_by_user": sender == "user",
        "read_by_admin": sender == "admin"
    })
    save_chats(data)

def get_user_chat(username: str, mark_read: bool = False):
    data = load_chats()
    msgs = data.get(username, [])
    if mark_read and msgs:
        changed = False
        for m in msgs:
            if not m.get("read_by_user"):
                m["read_by_user"] = True
                changed = True
        if changed: save_chats(data)
    return msgs

def delete_chat(username: str):
    data = load_chats()
    if username in data:
        del data[username]
        save_chats(data)

def count_unread_for_user(username: str) -> int:
    if not username: return 0
    return sum(1 for m in load_chats().get(username, []) if not m.get("read_by_user"))

def count_unread_for_admin() -> int:
    return sum(1 for msgs in load_chats().values() for m in msgs if not m.get("read_by_admin"))

def mark_admin_read(username: str):
    data = load_chats()
    for m in data.get(username, []):
        m["read_by_admin"] = True
    save_chats(data)
