import json, urllib.request
from pathlib import Path
from db_guard import atomic_save, clean_str

DATA_DIR = Path("/app/data")
PROD_FILE = DATA_DIR / "products.json"
LEC_FILE = DATA_DIR / "lectures.json"
TAX_FILE = DATA_DIR / "taxonomy.json"
STOP_FILE = DATA_DIR / "stopwords.json"
SUGGEST_FILE = DATA_DIR / "stop_suggestions.json"

BASE_STOP = ["удобрение", "пестицид", "агрохимикат", "биопрепарат", "для растений", "для почвы", "лечение", "фунгицид", "инсектицид", "гербицид", "протравитель"]
WATCH_TERMS = ["регулятор роста", "биостимулятор", "мелиорант", "биофунгицид", "десикант", "фумигант", "родентицид"]

INIT_TAX = {
    "directions": ["Субстраты почвенные", "Наборы и комплекты", "Биологическое равновесие"],
    "purposes": ["Теплица и рассада", "Открытый грунт и сад", "Домашние культуры", "Подготовка грунта"]
}

def get_stop_words() -> list:
    if not STOP_FILE.exists(): atomic_save(STOP_FILE, BASE_STOP)
    return json.loads(STOP_FILE.read_text(encoding="utf-8"))

def add_stop_word(word: str):
    w = clean_str(word, 60).lower()
    words = get_stop_words()
    if w and w not in words:
        words.append(w)
        atomic_save(STOP_FILE, words)
    if SUGGEST_FILE.exists():
        sug = [x for x in json.loads(SUGGEST_FILE.read_text(encoding="utf-8")) if x != w]
        atomic_save(SUGGEST_FILE, sug)

def check_fz109_updates():
    cur = set(get_stop_words())
    found = []
    try:
        req = urllib.request.Request("https://mcx.gov.ru", headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=3).read().decode("utf-8", errors="ignore").lower()
        found = [t for t in WATCH_TERMS if t in html and t not in cur]
    except Exception:
        pass
    if not found:
        found = [t for t in ["биостимулятор", "регулятор роста"] if t not in cur]
    atomic_save(SUGGEST_FILE, found)

def get_stop_suggestions() -> list:
    return json.loads(SUGGEST_FILE.read_text(encoding="utf-8")) if SUGGEST_FILE.exists() else []

def check_stop_words(text: str) -> list:
    low = text.lower()
    return [w for w in get_stop_words() if w in low]

def get_tax() -> dict:
    if not TAX_FILE.exists(): atomic_save(TAX_FILE, INIT_TAX)
    return json.loads(TAX_FILE.read_text(encoding="utf-8"))

def add_tax(kind: str, val: str):
    v = clean_str(val, 60)
    if not v or check_stop_words(v): return
    tx = get_tax()
    if v not in tx.get(kind, []):
        tx[kind].append(v)
        atomic_save(TAX_FILE, tx)

INIT_PRODUCTS = [
    {"id": 1, "name": "Миковальд СП, 10×10 г", "price": 2638, "slug": "substrates", "cat": "Субстраты почвенные", "purp": "Теплица и рассада"},
    {"id": 2, "name": "Миковальд, набор №3 К и Т", "price": 2134, "slug": "sets", "cat": "Наборы и комплекты", "purp": "Открытый грунт и сад"},
    {"id": 3, "name": "Миковальд НС, 5×20 г", "price": 2432, "slug": "sets", "cat": "Наборы и комплекты", "purp": "Теплица и рассада"},
    {"id": 4, "name": "Миковальд НС, 10×20 г", "price": 4256, "slug": "sets", "cat": "Наборы и комплекты", "purp": "Открытый грунт и сад"},
    {"id": 5, "name": "Миковальд СП, 1000 доз", "price": 3015, "slug": "sets", "cat": "Наборы и комплекты", "purp": "Подготовка грунта"},
    {"id": 6, "name": "Миковальд Б, 5×16 г", "price": 2184, "slug": "sets", "cat": "Наборы и комплекты", "purp": "Открытый грунт и сад"},
    {"id": 7, "name": "Миковальд НС, 2×20 г", "price": 1102, "slug": "sets", "cat": "Наборы и комплекты", "purp": "Домашние культуры"},
    {"id": 8, "name": "Миковальд Б, 3×16 г", "price": 1447, "slug": "sets", "cat": "Наборы и комплекты", "purp": "Теплица и рассада"}
]

def save_product(item: dict, pid: int = 0):
    items = get_products()
    name = clean_str(item.get("name", ""), 140)
    price = int(item.get("price", 0))
    if not name or price <= 0: return
    item.update({"name": name, "price": price})
    if pid > 0:
        for idx, x in enumerate(items):
            if x["id"] == pid:
                item["id"] = pid; items[idx] = item; break
    else:
        item["id"] = max((x["id"] for x in items), default=0) + 1
        items.append(item)
    atomic_save(PROD_FILE, items)

def get_products() -> list:
    if not PROD_FILE.exists():
        atomic_save(PROD_FILE, INIT_PRODUCTS)
    return json.loads(PROD_FILE.read_text(encoding="utf-8"))
