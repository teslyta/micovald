import hashlib, os, hmac, json, time, pyotp
from pathlib import Path

DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
SECRET_FILE = DATA_DIR / "secret.key"
ATTEMPTS = {}

def get_secret() -> bytes:
    if not SECRET_FILE.exists():
        SECRET_FILE.write_bytes(os.urandom(32))
    return SECRET_FILE.read_bytes()

def sign_session(user: str, ua: str = "") -> str:
    ts = str(int(time.time()))
    payload = f"{user}|{ts}|{hashlib.sha256(ua.encode()).hexdigest()[:12]}"
    sig = hmac.new(get_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"

def verify_session(token: str, ua: str = "") -> str:
    if not token or "." not in token: return ""
    payload, sig = token.rsplit(".", 1)
    parts = payload.split("|")
    if len(parts) != 3: return ""
    user, ts, ua_h = parts
    if user == "admin" and (time.time() - int(ts)) > 1800: return ""
    if ua and ua_h != hashlib.sha256(ua.encode()).hexdigest()[:12]: return ""
    expected = hmac.new(get_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return user if hmac.compare_digest(sig, expected) else ""

def check_rate_limit(ip: str) -> bool:
    now = time.time()
    hist = [t for t in ATTEMPTS.get(ip, []) if now - t < 300]
    ATTEMPTS[ip] = hist
    return len(hist) < 5

def record_fail(ip: str):
    ATTEMPTS.setdefault(ip, []).append(time.time())

def hash_pw(pw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return f"{salt.hex()}:{dk.hex()}"

def verify_pw(pw: str, stored: str) -> bool:
    if ":" not in stored: return hmac.compare_digest(pw, stored)
    s_hex, h_hex = stored.split(":", 1)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(s_hex), 200_000)
    return hmac.compare_digest(dk.hex(), h_hex)

def load_users() -> dict:
    if not USERS_FILE.exists():
        u = {"admin": {"pw": hash_pw("admin"), "2fa": False, "totp": pyotp.random_base32()}}
        USERS_FILE.write_text(json.dumps(u, indent=2))
        return u
    return json.loads(USERS_FILE.read_text())

def verify_2fa(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)

import secrets
OTP_CODES = {}

def gen_email_otp(user: str) -> str:
    code = f"{secrets.randbelow(900000) + 100000}"
    OTP_CODES[user] = (code, time.time() + 300)
    return code

def check_email_otp(user: str, code: str) -> bool:
    item = OTP_CODES.pop(user, None)
    if not item: return False
    saved, exp = item
    if time.time() <= exp and hmac.compare_digest(saved, code.strip()):
        OTP_CODES.pop(user, None)
        return True
    return False

def is_admin_user(login: str) -> bool:
    if not login: return False
    if login == "admin": return True
    return load_users().get(login, {}).get("role") == "admin"

import re
def is_strong_admin_pw(pw: str) -> bool:
    return len(pw) >= 10 and bool(re.search(r"[A-Za-zА-Яа-я]", pw)) and bool(re.search(r"\d", pw))
