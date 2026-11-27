import urllib.parse
import uuid
from chat import add_chat_msg, get_user_chat, count_unread_for_user, count_unread_for_admin, load_chats, mark_admin_read, delete_chat
from fastapi.staticfiles import StaticFiles
from promos import get_promos, get_active_promo, save_promo, archive_promo
import random
import re
import secrets
from analytics import get_stats, track_visit, track_missed_search
import json, time, urllib.parse, pyotp, qrcode, base64, io
from pathlib import Path
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
from security import hash_pw, verify_pw, load_users, USERS_FILE, sign_session, verify_session, check_rate_limit, record_fail, verify_2fa, is_admin_user, is_strong_admin_pw, gen_email_otp, check_email_otp
from notifier import send_email, send_2fa_code, get_cfg
from store import get_products, save_product, check_stop_words, get_tax, add_tax, check_fz109_updates, get_stop_suggestions, add_stop_word, LEC_FILE, PROD_FILE
from finance import get_records, add_order, add_manual, update_order, refund_order, delete_record, export_kudir_csv, mark_paid, FIN_FILE, save_records
from farmers import get_farmers, add_farmer, del_farmer, FARM_FILE
from upload_guard import save_safe_image
from undo_mgr import save_undo, get_undo, apply_undo
from validators import validate_order_data

app = FastAPI()

@app.middleware("http")
async def anti_clone_protection(request: Request, call_next):
    ua = (request.headers.get("user-agent") or "").lower()
    bad_agents = ("httrack", "webcopier", "teleport", "offline explorer", "sitegrabber", "webzip", "nikto", "sqlmap")
    if any(b in ua for b in bad_agents):
        return Response("Access Denied", status_code=403)
    resp = await call_next(request)
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp

app.mount("/media", StaticFiles(directory="/app/media"), name="media")
@app.on_event("startup")
def on_start(): check_fz109_updates()
@app.middleware("http")
async def csrf_and_sec(request: Request, call_next):
    if request.method == "POST" and not request.url.path.startswith("/api/"):
        orig = request.headers.get("origin", "")
        host = request.headers.get("host", "")
        if orig and host and host not in orig:
            return Response("CSRF blocked", status_code=403)
    vid = request.cookies.get("vid") or secrets.token_hex(8)
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if request.method == "GET" and not is_admin_user(u): track_visit(vid, u, request.url.path, request.query_params.get("ordered") == "1")
    resp = await call_next(request)
    if "text/html" in resp.headers.get("content-type", ""): resp.headers["Cache-Control"] = "no-store, must-revalidate"
    if not request.cookies.get("vid"): resp.set_cookie("vid", vid, max_age=86400, httponly=True, samesite="lax")
    return resp

templates = Jinja2Templates(directory="templates")
ABOUT_FILE = Path("/app/data/about.json")

DEFAULT_TOPICS = {
    "microbiology": {"cat": "Микробиология", "title": "Активизация полезной почвенной микрофлоры", "desc": "Научные основы поддержания естественного баланса среды.", "lectures": [{"id": 1, "title": "Лекция 1. Активизация полезной почвенной микрофлоры", "text": "Полезная почвенная микрофлора формирует естественную биологическую среду вокруг корневой системы.", "img": ""}]},
    "agrotech": {"cat": "Агротехника", "title": "Поддержание экологического равновесия", "desc": "Обзорные лекции по работе с почвенными субстратами.", "lectures": [{"id": 1, "title": "Лекция 1. Природные механизмы устойчивости среды", "text": "Профилактическое поддержание баланса микрофлоры в теплицах и на садовых участках.", "img": ""}]}
}

def get_topics() -> dict:
    if not LEC_FILE.exists(): LEC_FILE.write_text(json.dumps(DEFAULT_TOPICS, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(LEC_FILE.read_text(encoding="utf-8"))

def get_about() -> dict:
    return json.loads(ABOUT_FILE.read_text(encoding="utf-8")) if ABOUT_FILE.exists() else {"title": "О производителе MICOVALD", "text": "", "img": ""}


def get_chat_actor(request: Request):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if u: return u, False
    gid = request.cookies.get("guest_chat_id", "")
    if not gid or not gid.startswith("Guest_"):
        gid = "Guest_" + uuid.uuid4().hex[:6].upper()
    return gid, True

def ctx(request: Request, **extra):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    return {"request": request, "tax": get_tax(), "used_cats": sorted({x.get("cat","") for x in get_products() if x.get("cat")}), "used_purps": sorted({x.get("purp","") for x in get_products() if x.get("purp")}), "active_promo": get_active_promo(), "unread_chat": count_unread_for_user(u), "admin_unread_chat": count_unread_for_admin(), "all_chats": (load_chats() if is_admin_user(u) else {}), "nav_topics": get_topics(), "my_chat_msgs": get_user_chat(u or request.cookies.get("guest_chat_id", ""), mark_read=False)[-8:], "nav_articles": (json.loads(Path("/app/data/encyclopedia.json").read_text(encoding="utf-8")) if Path("/app/data/encyclopedia.json").exists() else []), "valid_pairs_json": json.dumps([{"c": x.get("cat",""), "p": x.get("purp","")} for x in get_products()], ensure_ascii=False), "user": u, "is_admin": is_admin_user(u), "tax": get_tax(), "used_cats": sorted({x.get("cat","") for x in get_products() if x.get("cat")}), "used_purps": sorted({x.get("purp","") for x in get_products() if x.get("purp")}), "active_promo": get_active_promo(), "unread_chat": count_unread_for_user(u), "admin_unread_chat": count_unread_for_admin(), "all_chats": (load_chats() if is_admin_user(u) else {}), "nav_topics": get_topics(), "my_chat_msgs": get_user_chat(u or request.cookies.get("guest_chat_id", ""), mark_read=False)[-8:], "nav_articles": (json.loads(Path("/app/data/encyclopedia.json").read_text(encoding="utf-8")) if Path("/app/data/encyclopedia.json").exists() else []), "valid_pairs_json": json.dumps([{"c": x.get("cat",""), "p": x.get("purp","")} for x in get_products()], ensure_ascii=False), "undo": get_undo() if u in [k for k, v in load_users().items() if k == "admin" or v.get("role") == "admin"] else None, **extra}

@app.get("/", response_class=HTMLResponse)
@app.get("/category/{slug}", response_class=HTMLResponse)
async def home(request: Request, slug: str = "", q: str = "", cat: str = "", purp: str = ""):
    items = [x for x in get_products() if (not slug or x.get("slug")==slug) and (not cat or (x.get("purp")==cat[5:] if cat.startswith("purp:") else x.get("cat")==cat)) and (not purp or x.get("purp")==purp) and (not q or q.lower() in x["name"].lower())]
    u_q = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if q.strip() and not items and not is_admin_user(u_q): track_missed_search(q, u_q)
    found_articles = []
    if q.strip() and not items:
        encs = json.loads(Path("/app/data/encyclopedia.json").read_text(encoding="utf-8")) if Path("/app/data/encyclopedia.json").exists() else []
        ql = q.lower().strip()
        found_articles = [a for a in encs if ql in (a.get("title","") + " " + a.get("body","") + " " + a.get("cat","")).lower()]
    return templates.TemplateResponse(request, "home.html", ctx(request, slug=slug, q=q, products=items, found_articles=found_articles, tax=get_tax(), cat=cat, purp=purp))

@app.get("/cart", response_class=HTMLResponse)
async def cart_p(request: Request):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    u_em = load_users().get(u, {}).get("email", "") if u else ""
    return templates.TemplateResponse(request, "cart.html", ctx(request, ordered=request.query_params.get("ordered"), user_email=u_em, err=request.query_params.get("err", "")))

@app.get("/encyclopedia", response_class=HTMLResponse)
async def enc_p(request: Request):
    return templates.TemplateResponse(request, "encyclopedia.html", ctx(request, articles=get_topics()))

@app.get("/encyclopedia/{slug}", response_class=HTMLResponse)
async def art_p(request: Request, slug: str):
    return templates.TemplateResponse(request, "article.html", ctx(request, art=get_topics().get(slug), slug=slug))

@app.get("/about", response_class=HTMLResponse)
async def about_p(request: Request):
    return templates.TemplateResponse(request, "about.html", ctx(request, about=get_about(), vk_posts=[], vk_ok=False))

@app.get("/farmers", response_class=HTMLResponse)
async def farmers_p(request: Request, sent: str = ""):
    return templates.TemplateResponse(request, "farmers.html", ctx(request, sent=sent))

@app.get("/how-to-order", response_class=HTMLResponse)
async def how_p(request: Request):
    return templates.TemplateResponse(request, "how_to_order.html", ctx(request))

@app.post("/owner/set-admin")
async def set_admin_role(request: Request, target_user: str = Form(...), make_admin: str = Form("1")):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not is_admin_user(u): return RedirectResponse("/login", 303)
    users = load_users()
    tu = target_user.strip()
    admins = [k for k, v in users.items() if k == "admin" or v.get("role") == "admin"]
    if tu in users and tu != "admin" and (make_admin == "1" or len(admins) > 1):
        users[tu]["role"] = "admin" if make_admin == "1" else "user"
        USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2))
    return RedirectResponse("/owner?tab=sec&msg=1", 303)

@app.get("/login", response_class=HTMLResponse)
async def login_p(request: Request, err: str = ""):
    a, b = random.randint(2, 9), random.randint(1, 8)
    cap_sig = sign_session(f"cap:{a+b}:{int(time.time())}")
    return templates.TemplateResponse(request, "login.html", ctx(request, err=err, cap_q=f"{a} + {b}", cap_sig=cap_sig))

@app.post("/api/send-login-2fa")
async def api_send_2fa(request: Request, login: str = Form(...), password: str = Form(...), cap_ans: str = Form(""), cap_sig: str = Form(""), website_url: str = Form(""), prefer: str = Form("auto")):
    ip = request.client.host if request.client else "local"
    if website_url or not check_rate_limit(ip): return {"ok": False, "msg": "Превышен лимит попыток или сработала защита от ботов"}
    raw_cap = verify_session(cap_sig)
    parts = raw_cap.split(":")
    if len(parts) != 3 or parts[1] != cap_ans.strip() or (time.time() - int(parts[2])) < 1:
        return {"ok": False, "msg": "Решите пример защиты от ботов правильно"}
    raw_l = login.strip()
    users_all = load_users()
    l = raw_l if raw_l in users_all else next((k for k, v in users_all.items() if v.get("email", "").lower() == raw_l.lower()), raw_l)
    u = users_all.get(l)
    if not u or not verify_pw(password.strip(), u["pw"]):
        record_fail(ip)
        return {"ok": False, "msg": "Неверный логин или пароль"}
    if not u.get("2fa"):
        return {"ok": True, "no_2fa": True, "msg": "Для этого аккаунта 2FA отключена — нажмите Войти"}
    em = u.get("email", "") or (get_cfg().get("OWNER_EMAIL", "") if l == "admin" else "")
    ph = u.get("phone", "")
    c2 = gen_email_otp(l)
    ch = send_2fa_code(em, ph, c2, "вход в кабинет", prefer)
    if not ch: return {"ok": False, "msg": "Укажите телефон или Email в Личном кабинете для 2FA"}
    dest = f"по SMS на +{ph[:4]}***{ph[-2:]}" if ch == "phone" else f"на почту {em[:3]}***@{em.split('@')[-1]}"
    return {"ok": True, "msg": f"Код 2FA отправлен {dest}"}

@app.get("/register", response_class=HTMLResponse)
async def reg_p(request: Request):
    return templates.TemplateResponse(request, "register.html", ctx(request))

@app.get("/account", response_class=HTMLResponse)
async def acc_p(request: Request, msg: str = ""):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not u: return RedirectResponse("/login", 303)
    my_orders = [x for x in get_records() if x.get("source") == u]
    return templates.TemplateResponse(request, "account.html", ctx(request, recs=get_records(), stats=get_stats(), promos=get_promos(), topics=get_topics(), all_chats=load_chats(), msg=msg, prof=load_users().get(u, {}), my_orders=my_orders, farmers=get_farmers()))

@app.post("/account/profile")
async def save_prof(request: Request, fio: str = Form(""), email: str = Form(...), phone: str = Form("")):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not u: return RedirectResponse("/login", 303)
    users = load_users()
    users[u]["fio"], users[u]["email"], users[u]["phone"] = fio.strip(), email.strip(), phone.strip()
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2))
    return RedirectResponse("/cart?ordered=1", 303)

@app.post("/login")
async def do_login(request: Request, login: str = Form(...), password: str = Form(...), otp: str = Form("")):
    ip = request.client.host if request.client else "local"
    if not check_rate_limit(ip): return RedirectResponse("/login?err=limit", 303)
    l = login.strip()
    u = load_users().get(l)
    if u and verify_pw(password.strip(), u["pw"]):
        if u.get("2fa"):
            if not otp:
                c2 = gen_email_otp(l)
                send_email(get_cfg().get("OWNER_EMAIL", ""), "Код 2FA MICOVALD", f"Код: {c2}")
                return RedirectResponse("/login?need2fa=1", 303)
            if not check_email_otp(l, otp): return RedirectResponse("/login?err=2fa", 303)
        r = RedirectResponse("/owner" if is_admin_user(l) else "/account", 303)
        r.set_cookie("user", sign_session(l, request.headers.get("user-agent", "")), httponly=True, samesite="lax")
        return r
    record_fail(ip)
    return RedirectResponse("/login?err=1", 303)

@app.post("/register")
async def do_reg(request: Request, login: str = Form(...), email: str = Form(...), password: str = Form(...)):
    users = load_users(); l = login.strip()
    if l in users or "@" not in email: return RedirectResponse("/register?err=1", 303)
    users[l] = {"pw": hash_pw(password.strip()), "email": email.strip(), "2fa": True, "role": "user"}
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2))
    r = RedirectResponse("/account?welcome=1", 303)
    r.set_cookie("user", sign_session(l, request.headers.get("user-agent", "")), httponly=True, samesite="lax")
    return r

@app.post("/account/send-sec-code")
async def send_sec_code(request: Request):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if u:
        prof = load_users().get(u, {})
        c2 = gen_email_otp(u)
        send_2fa_code(prof.get("email", ""), prof.get("phone", ""), c2, "смена пароля")
    return RedirectResponse("/account?code_sent=1", 303)

@app.post("/change-password")
async def ch_pass(request: Request, new_password: str = Form(...), otp: str = Form("")):
    l = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not l: return RedirectResponse("/login", 303)
    pw = new_password.strip()
    if is_admin_user(l):
        if not is_strong_admin_pw(pw):
            return RedirectResponse("/account?err=" + urllib.parse.quote("Пароль администратора должен быть от 10 символов и содержать буквы и цифры"), 303)
        if not check_email_otp(l, otp):
            return RedirectResponse("/account?err=" + urllib.parse.quote("Неверный или не запрошенный код подтверждения 2FA"), 303)
    users = load_users(); users[l]["pw"] = hash_pw(pw)
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2))
    return RedirectResponse("/cart?ordered=1", 303)

@app.get("/order/create")
async def order_get_redir(): return RedirectResponse("/cart", 303)

@app.post("/order/create")
async def create_order(request: Request, fio: str = Form(...), phone: str = Form(...), email: str = Form(...), zip_code: str = Form(...), address: str = Form(...), total: int = Form(...), summary: str = Form(...), cart_json: str = Form("[]")):
    err = validate_order_data(fio, phone, zip_code, address)
    if "@" not in email: err = "Укажите корректный Email для получения чека"
    if total <= 0 or err: return RedirectResponse(f"/cart?err={urllib.parse.quote(err or 'Корзина пуста')}", 303)
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", "")) or "Гость"
    oid = add_order(fio.strip(), phone.strip(), email.strip(), zip_code.strip(), address.strip(), total, summary, "[]", u)
    return RedirectResponse(f"/cart?ordered=1&oid={oid or ''}", 303)

@app.post("/account/cancel-order/{oid}")
async def user_cancel_order(request: Request, oid: int):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if u and any(x.get("id") == oid and x.get("source") == u for x in get_records()): refund_order(oid)
    return RedirectResponse("/cart?ordered=1", 303)

@app.post("/farmers/send")
async def farmers_send(request: Request, kind: str = Form("Сотрудничество"), name: str = Form(...), phone: str = Form(...), farm: str = Form(""), msg: str = Form(...)):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    clean_n, clean_m = name.strip(), msg.strip()
    digits_p = "".join(c for c in phone if c.isdigit())
    if len(clean_n) < 2 or any(c.isdigit() for c in clean_n) or len(digits_p) != 11 or len(clean_m) < 10 or not any(c in "аеёиоуыэюяaeiouy" for c in clean_m.lower()) or re.search(r"(.)\1{3,}", clean_m.lower()):
        err = urllib.parse.quote("Опишите вопрос осмысленным текстом")
        return RedirectResponse(f"/account?err={err}" if u else f"/farmers?err={err}", 303)
    add_farmer(kind, name.strip(), phone.strip(), farm.strip(), clean_m)
    return RedirectResponse("/account?msg=1" if u else "/farmers?sent=1", 303)

@app.get("/owner", response_class=HTMLResponse)
async def owner_p(request: Request, msg: str = ""):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not is_admin_user(u): return RedirectResponse("/login", 303)
    recs = get_records()
    inc = sum(x["amount"] for x in recs if x["type"]=="Приход" and x.get("status") in ("Оплачен", "Отправлен", "Доставлен", "Проведено") and x.get("source") != "admin" and "тест" not in x.get("fio", "").lower())
    exp = sum(x["amount"] for x in recs if x["type"]=="Расход")
    adm = load_users().get("admin", {})
    return templates.TemplateResponse(request, "owner.html", ctx(request, all_chats=load_chats(), topics=get_topics(), farmers=get_farmers(), msg=msg, recs=recs, inc=inc, exp=exp, adm_2fa=adm.get("2fa", False), all_users=load_users(), stats=get_stats(), promos=get_promos()))

@app.post("/owner/lecture")
async def save_lec(request: Request, topic: str = Form(...), new_cat: str = Form(""), new_desc: str = Form(""), lec_id: int = Form(0), title: str = Form(...), text: str = Form(""), photo: UploadFile = File(None), extra_photos: list[UploadFile] = File(None)):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    data = get_topics()
    if topic == "__new__" and new_cat.strip():
        slug = f"sec_{int(time.time())}"; data[slug] = {"cat": new_cat.strip(), "title": new_cat.strip(), "desc": new_desc.strip() or "Авторский раздел", "lectures": []}; topic = slug
    img_url = await save_safe_image(photo, "") if (photo and photo.filename) else ""
    lecs = data[topic]["lectures"]
    found = next((x for x in lecs if x["id"] == lec_id), None) if lec_id > 0 else None
    save_undo(LEC_FILE, "изменение лекций", f"/encyclopedia/{topic}")
    if found:
        found["title"], found["text"] = title, text
        if img_url: found["img"] = img_url
    else:
        next_id = max((x["id"] for x in lecs), default=0) + 1
        lecs.append({"id": next_id, "title": f"Лекция {next_id}. {title}", "text": text, "img": img_url})
    LEC_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return RedirectResponse(f"/encyclopedia/{topic}", 303)

@app.post("/owner/lecture/delete")
async def del_lec(request: Request, topic: str = Form(...), lec_id: int = Form(...)):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    data = get_topics()
    if topic in data:
        save_undo(LEC_FILE, "удаление лекции", f"/encyclopedia/{topic}")
        data[topic]["lectures"] = [x for x in data[topic]["lectures"] if x["id"] != lec_id]
        LEC_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return RedirectResponse(f"/encyclopedia/{topic}", 303)

@app.post("/owner/product")
async def add_product(request: Request, name: str = Form(...), desc: str = Form(""), slug: str = Form(...), price: int = Form(...), photo: UploadFile = File(...)):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    if check_stop_words(f"{name} {desc}"): return RedirectResponse("/", 303)
    imgs_list = list(old.get("images") or ([img_url] if img_url else []))
    if img_url and (not imgs_list or imgs_list != img_url):
        if imgs_list: imgs_list = img_url
        else: imgs_list.append(img_url)
    for ep in (extra_photos or []):
        if ep and getattr(ep, "filename", ""):
            u_ep = await save_safe_image(ep, "products")
            if u_ep and u_ep not in imgs_list: imgs_list.append(u_ep)
    save_undo(PROD_FILE, "добавление товара", "/")
    save_product({"name": name, "desc": desc, "slug": slug, "cat": "Субстраты почвенные" if slug == "substrates" else "Наборы и комплекты", "price": price, "img": await save_safe_image(photo, "products")})
    return RedirectResponse("/", 303)

@app.post("/owner/delete-product/{pid}")
async def del_prod(request: Request, pid: int):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(PROD_FILE, "удаление товара", "/")
        PROD_FILE.write_text(json.dumps([x for x in get_products() if x["id"] != pid], ensure_ascii=False, indent=2), encoding="utf-8")
    return RedirectResponse("/", 303)

@app.post("/owner/about")
async def save_about(request: Request, title: str = Form(...), text: str = Form(...), photo: UploadFile = File(None), extra_photos: list[UploadFile] = File(None)):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    ab = get_about(); ab["title"], ab["text"] = title, text
    if photo and photo.filename: ab["img"] = await save_safe_image(photo, "about")
    ABOUT_FILE.write_text(json.dumps(ab, ensure_ascii=False, indent=2), encoding="utf-8")
    return RedirectResponse("/about", 303)

@app.post("/owner/finance")
async def owner_fin(request: Request, ftype: str = Form(...), amount: int = Form(...), note: str = Form(...)):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FIN_FILE, "добавление записи", "/owner"); add_manual(ftype, amount, note)
    return RedirectResponse("/owner?tab=sec&msg=1", 303)

@app.post("/owner/order/paid/{oid}")
async def owner_ord_paid(request: Request, oid: int):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FIN_FILE, "подтверждение оплаты", "/owner"); mark_paid(oid)
    return RedirectResponse("/owner?tab=sec&msg=1", 303)

@app.post("/owner/order/edit/{oid}")
async def owner_ord_edit(request: Request, oid: int, fio: str = Form(...), phone: str = Form(...), zip_code: str = Form(...), address: str = Form(...), status: str = Form(...), track: str = Form("")):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FIN_FILE, "изменение заказа", "/owner"); update_order(oid, fio, phone, zip_code, address, status, track)
    return RedirectResponse("/owner?tab=sec&msg=1", 303)

@app.post("/owner/order/refund/{oid}")
async def owner_ord_refund(request: Request, oid: int):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FIN_FILE, "возврат заказа", "/owner"); refund_order(oid)
    return RedirectResponse("/owner?msg=refund", 303)

@app.post("/owner/order/delete/{oid}")
async def owner_ord_del(request: Request, oid: int):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FIN_FILE, "удаление заказа", "/owner"); delete_record(oid)
    return RedirectResponse("/owner?msg=del", 303)

@app.post("/owner/farmers/delete/{fid}")
async def owner_farm_del(request: Request, fid: int):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FARM_FILE, "удаление обращения", "/owner"); del_farmer(fid)
    return RedirectResponse("/owner?tab=farmers&msg=1", 303)

@app.get("/owner/export.csv")
async def owner_csv(request: Request):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    return Response("\ufeff" + export_kudir_csv(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename=KUDiR_MICOVALD_FNS_{time.strftime('%Y-%m-%d')}.csv"})

@app.post("/owner/2fa")
async def toggle_2fa(request: Request, enable: str = Form("0")):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        users = load_users(); users["admin"]["2fa"] = (enable == "1")
        USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2))
    return RedirectResponse("/owner?tab=sec&msg=1", 303)

@app.post("/owner/undo")
async def do_undo(request: Request):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    return RedirectResponse(apply_undo(), 303)

@app.get("/logout")
async def logout():
    r = RedirectResponse("/?logged_out=1", 303); r.delete_cookie("user"); r.headers["Clear-Site-Data"] = '"storage"'; return r

@app.get("/owner/product-save")
async def save_prod_get(): return RedirectResponse("/", 303)

@app.post("/owner/product-save")
async def save_prod_full(request: Request, pid: int = Form(0), name: str = Form(...), desc: str = Form(""), price: int = Form(...), stock: int = Form(1), cat: str = Form(""), new_cat: str = Form(""), purp: str = Form(""), new_purp: str = Form(""), photo: UploadFile = File(None), extra_photos: list[UploadFile] = File(None)):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    c_val = new_cat.strip() or cat
    p_val = new_purp.strip() or purp
    sw_hit = check_stop_words(f"{name} {desc} {c_val} {p_val}")
    if sw_hit: return RedirectResponse(f"/product/{pid}?err_sw={urllib.parse.quote(", ".join(sw_hit))}" if pid > 0 else f"/?err=stop&sw={urllib.parse.quote(", ".join(sw_hit))}", 303)
    if new_cat.strip(): add_tax("directions", c_val)
    if new_purp.strip(): add_tax("purposes", p_val)
    old = next((x for x in get_products() if x["id"] == pid), {}) if pid > 0 else {}
    img_url = old.get("img", "/media/products/p1.webp")
    if photo and getattr(photo, "filename", ""):
        saved_u = await save_safe_image(photo, "products")
        if saved_u: img_url = saved_u
    imgs_list = [img_url] + [x for x in (old.get("images") or []) if x and x != img_url]
    for ep in (extra_photos or []):
        if ep and getattr(ep, "filename", ""):
            u_ep = await save_safe_image(ep, "products")
            if u_ep and u_ep not in imgs_list: imgs_list.append(u_ep)
    save_undo(PROD_FILE, "изменение каталога", "/")
    save_product({"name": name, "desc": desc, "slug": "substrates" if "субстрат" in c_val.lower() else "sets", "cat": c_val, "purp": p_val, "price": price, "stock": max(0, int(stock)), "img": img_url, "images": imgs_list}, pid)
    return RedirectResponse("/", 303)

@app.post("/owner/stopword/add")
async def add_sw(request: Request, word: str = Form(...)):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): add_stop_word(word)
    return RedirectResponse(request.headers.get("referer", "/owner"), 303)

@app.post("/owner/clear-test")
async def clear_test_data(request: Request):
    # Удаляем тестовые заказы
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    save_records([r for r in get_records() if r.get("source") not in ("admin", "test") and "тест" not in r.get("fio", "").lower() and r.get("status") not in ("Тестовый заказ", "Оплачен (Тест)")])
    from analytics import STAT_FILE, atomic_save
    atomic_save(STAT_FILE, {"visits": {}, "missed": []})
    return RedirectResponse("/owner?tab=sec&msg=1", 303)

@app.get("/api/addr-suggest")
async def addr_suggest(q: str = ""):
    q = q.strip()
    if len(q) < 4: return []
    try:
        url = "https://openstreetmap.org" + urllib.parse.quote(q)
        req = urllib.request.Request(url, headers={"User-Agent": "MICOVALD-Store/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=3).read().decode("utf-8"))
        out = []
        for item in data:
            a = item.get("address", {})
            pc = a.get("postcode", "")
            city = a.get("city") or a.get("town") or a.get("village") or a.get("state", "")
            road = a.get("road", "")
            house = a.get("house_number", "")
            label = ", ".join([x for x in [city, road, house] if x]) or item.get("display_name", "")[:90]
            if label: out.append({"label": label, "zip": pc if len(pc)==6 and pc.isdigit() else ""})
        return out
    except Exception:
        return []

@app.post("/account/2fa")
async def user_toggle_2fa(request: Request, enable: str = Form("0")):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not u: return RedirectResponse("/login", 303)
    users = load_users()
    has_ph = len("".join(c for c in users[u].get("phone", "") if c.isdigit())) == 11
    if enable == "1" and not users[u].get("email") and not has_ph and u != "admin":
        return RedirectResponse("/account?err=" + urllib.parse.quote("Сначала укажите и сохраните Email в контактных данных выше"), 303)
    users[u]["2fa"] = (enable == "1")
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")
    return RedirectResponse("/cart?ordered=1", 303)

@app.post("/owner/promo/save")
async def owner_promo_save(request: Request, pid: int = Form(0), title: str = Form(...), desc: str = Form(...), discount: int = Form(10), start_date: str = Form(...), end_date: str = Form(...), target_cat: str = Form("")):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    if check_stop_words(f"{title} {desc}"): return RedirectResponse("/owner?err=stop", 303)
    save_promo(pid, title, desc, discount, start_date, end_date, target_cat)
    return RedirectResponse("/owner?tab=sec&msg=1", 303)

@app.post("/owner/promo/archive/{pid}")
async def owner_promo_arch(request: Request, pid: int):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): archive_promo(pid)
    return RedirectResponse("/owner?tab=sec&msg=1", 303)

@app.get("/promos", response_class=HTMLResponse)
async def promos_page(request: Request):
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    act = [p for p in get_promos() if p.get("active") and p.get("start_date", "") <= today <= p.get("end_date", "9999-12-31")]
    return templates.TemplateResponse(request, "promos.html", ctx(request, active_promos=act))

@app.get("/product/{pid}", response_class=HTMLResponse)
async def product_detail(request: Request, pid: int):
    prod = next((x for x in get_products() if x.get("id") == pid), None)
    if not prod: return RedirectResponse("/", 303)
    st = json.loads(Path("/app/data/analytics.json").read_text(encoding="utf-8")) if Path("/app/data/analytics.json").exists() else {}
    real_views = st.get("visits", {}).get(f"/product/{pid}", 0) + st.get("visits", {}).get("/", 0)
    return templates.TemplateResponse(request, "product.html", ctx(request, p=prod, real_views=real_views, articles=get_topics()))

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, prod: str = ""):
    u_chk = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if is_admin_user(u_chk): return RedirectResponse("/owner?tab=chats&msg=1", 303)
    actor, is_guest = get_chat_actor(request)
    resp = templates.TemplateResponse(request, "chat.html", ctx(request, messages=get_user_chat(actor, mark_read=True), prod_q=prod))
    if is_guest: resp.set_cookie("guest_chat_id", actor, max_age=86400*30, httponly=True, samesite="lax")
    return resp

@app.post("/chat/send")
async def chat_send(request: Request, text: str = Form(...), prod_name: str = Form(""), guest_name: str = Form("")):
    actor, is_guest = get_chat_actor(request)
    label = f"{actor} ({guest_name.strip()})" if (is_guest and guest_name.strip()) else actor
    add_chat_msg(actor, "user", text, prod_name)
    try:
        from notifier import send_email, get_cfg
        to_m = get_cfg().get("SMTP_USER", "").strip() or "micovald@yandex.ru"
        send_email(to_m, f"Чат: {label}", f"Покупатель {label} написал в чат:\n{text}\nТовар: {prod_name or 'Общий вопрос'}")
    except Exception: pass
    ref = (request.headers.get("referer") or "/").split("#")[0]
    sep = "&" if "?" in ref else "?"
    if "chat_open=1" not in ref and "/chat" not in ref: ref = f"{ref}{sep}chat_open=1"
    resp = RedirectResponse(ref, 303)
    if is_guest: resp.set_cookie("guest_chat_id", actor, max_age=86400*30, httponly=True, samesite="lax")
    return resp

@app.post("/owner/chat-reply")
async def owner_chat_reply(request: Request, target_user: str = Form(...), text: str = Form(...)):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not is_admin_user(u): return RedirectResponse("/login", 303)
    add_chat_msg(target_user, "admin", text)
    mark_admin_read(target_user)
    return RedirectResponse("/owner?tab=chats&msg=1", 303)

@app.get("/favorites", response_class=HTMLResponse)
async def favorites_page(request: Request):
    return templates.TemplateResponse(request, "favorites.html", ctx(request))

@app.post("/owner/chat-delete")
async def owner_chat_delete(request: Request, target_user: str = Form(...)):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not is_admin_user(u): return RedirectResponse("/login", 303)
    delete_chat(target_user)
    return RedirectResponse("/owner?tab=chats&msg=1", 303)

@app.get("/api/suggest-addr")
async def api_suggest_addr(q: str = "", zip_code: str = ""):
    import urllib.request, urllib.parse, re as _re
    raw_q = q.strip()
    s = _re.sub(r'(?:^|\s)(?:г\.|гор\.|п\.|пос\.|ул\.|улица|пр\.|пр-т|проспект|ш\.|шоссе|д\.|дом|к\.|корп\.|стр\.|литера)(?=\s|$)', ' ', raw_q.replace(',', ' '), flags=_re.I)
    s = " ".join(s.split()).strip()
    z = "".join(c for c in zip_code if c.isdigit())
    if len(s) < 2 and len(z) != 6: return {"items": []}

    cache_file = Path("/app/data/zip_cache.json")
    try: zcache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    except Exception: zcache = {}

    ua = {"User-Agent": "MICOVALD-Shop/1.0 (micovald@yandex.ru)"}

    # 1. Пробуем определить город и улицы по 6-значному индексу через OpenStreetMap (с валидным User-Agent)
    if len(z) == 6 and z not in zcache:
        try:
            u_nom = f"https://openstreetmap.org{z}"
            req = urllib.request.Request(u_nom, headers=ua)
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
                city_lbl, lat, lon, found_streets = "", None, None, []
                for r in rows:
                    a = r.get("address", {})
                    reg = a.get("state") or ""
                    ct = a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or ""
                    st = a.get("road") or ""
                    if st and st not in found_streets: found_streets.append(st)
                    if not city_lbl and (ct or reg):
                        parts = [p for p in [reg if reg != ct else "", (f"г. {ct}" if a.get("city") or a.get("town") else ct)] if p]
                        city_lbl = ", ".join(parts)
                        lat, lon = r.get("lat"), r.get("lon")
                if city_lbl and lat and lon and len(found_streets) < 6:
                    ov_q = f'[out:json][timeout:3];way(around:2500,{lat},{lon})["highway"]["name"];out tags 35;'
                    req_ov = urllib.request.Request("https://overpass-api.de", data=("data=" + urllib.parse.quote(ov_q)).encode("utf-8"), headers=ua)
                    with urllib.request.urlopen(req_ov, timeout=3) as r_ov:
                        ov_data = json.loads(r_ov.read().decode("utf-8"))
                        for el in ov_data.get("elements", []):
                            nm = el.get("tags", {}).get("name", "")
                            if nm and nm not in found_streets and len(nm) > 3:
                                found_streets.append(nm)
                if city_lbl:
                    zcache[z] = [city_lbl, found_streets[:25]]
                    cache_file.write_text(json.dumps(zcache, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # Резервный справочник регионов и крупных городов РФ по 3-значному и 2-значному префиксу индекса (на случай недоступности OSM)
    if len(z) == 6 and z not in zcache:
        pref3 = {
            "162": ("Вологодская область, г. Череповец", ["Советский проспект", "проспект Победы", "улица Ленина", "проспект Строителей", "улица Металлургов", "Шекснинский проспект"]),
            "160": ("Вологодская область, г. Вологда", ["улица Ленина", "проспект Победы", "Пошехонское шоссе", "Ленинградская улица"]),
            "188": ("Ленинградская область, г. Всеволожск", ["Московская улица", "Центральная улица", "улица Вахрушева", "Колтушское шоссе", "Южное шоссе", "улица Героев", "Народная улица"]),
            "187": ("Ленинградская область, г. Тосно", ["проспект Ленина", "Советская улица", "Московское шоссе"]),
            "195": ("г. Санкт-Петербург", ["Заневский проспект", "Пискарёвский проспект", "Полюстровский проспект", "Новочеркасский проспект"]),
            "191": ("г. Санкт-Петербург", ["Невский проспект", "Лиговский проспект", "Владимирский проспект", "Литейный проспект"]),
            "125": ("г. Москва", ["Тверская улица", "Ленинградский проспект", "Большая Никитская улица"]),
            "630": ("Новосибирская область, г. Новосибирск", ["Красный проспект", "улица Ленина", "улица Кирова"]),
            "620": ("Свердловская область, г. Екатеринбург", ["проспект Ленина", "улица Малышева", "улица 8 Марта"]),
            "350": ("Краснодарский край, г. Краснодар", ["Красная улица", "улица Северная", "улица Ставропольская"]),
            "420": ("Республика Татарстан, г. Казань", ["улица Баумана", "проспект Ямашева", "улица Пушкина"]),
        }
        pref2 = {
            "10": ("г. Москва", []), "11": ("г. Москва", []), "12": ("г. Москва", []), "14": ("Московская область", []),
            "18": ("Ленинградская область", []), "19": ("г. Санкт-Петербург", []),
            "34": ("Ростовская область, г. Ростов-на-Дону", []), "35": ("Краснодарский край", []),
            "42": ("Республика Татарстан", []), "44": ("Самарская область", []), "45": ("Челябинская область", []),
            "60": ("Нижегородская область", []), "62": ("Свердловская область", []), "63": ("Новосибирская область", []),
            "66": ("Красноярский край", []), "69": ("Приморский край, г. Владивосток", []),
        }
        if z[:3] in pref3: zcache[z] = list(pref3[z[:3]])
        elif z[:2] in pref2: zcache[z] = list(pref2[z[:2]])

    out = []
    if len(z) == 6 and z in zcache:
        city_lbl, streets = zcache[z]
        s_clean = s.lower()
        for w in (city_lbl.lower() + " санкт петербург москва краснодар новосибирск екатеринбург казань").replace(",", "").split():
            if len(w) >= 3: s_clean = s_clean.replace(w, " ")
        street_tokens = [w for w in s_clean.split() if len(w) >= 2 and not w.isdigit()]
        nums = [w for w in s.split() if w.isdigit()]
        if streets:
            for st in streets:
                if not street_tokens or all(t in st.lower() for t in street_tokens):
                    if nums:
                        h_num = nums[0]
                        out.append({"addr": f"{city_lbl}, {st}, д. {h_num}", "zip": z})
                        for suf in ["кв. 1", "кв. 10", "кв. 25", "к. 1, кв. 1", "стр. 1"]:
                            out.append({"addr": f"{city_lbl}, {st}, д. {h_num}, {suf}", "zip": z})
                    elif street_tokens:
                        for h in ["1", "2", "5", "10", "15", "25"]:
                            out.append({"addr": f"{city_lbl}, {st}, д. {h}", "zip": z})
                    else:
                        out.append({"addr": f"{city_lbl}, {st}, ", "zip": z, "keep_typing": True})
        if not out:
            if nums and street_tokens:
                base_st = " ".join(street_tokens).capitalize()
                h_num = nums[0]
                out.append({"addr": f"{city_lbl}, {base_st}, д. {h_num}", "zip": z})
                for suf in ["к. 1", "стр. 1", "литера А"]:
                    out.append({"addr": f"{city_lbl}, {base_st}, д. {h_num}, {suf}", "zip": z})
            elif street_tokens:
                base_st = " ".join(street_tokens).capitalize()
                for h in ["1", "5", "10", "15", "25"]:
                    out.append({"addr": f"{city_lbl}, {base_st}, д. {h}", "zip": z})
            else:
                out.append({"addr": f"{city_lbl}, ", "zip": z, "prefix_only": True})
        return {"items": out[:15]}

    # 2. Поиск по произвольному тексту адреса без индекса через Nominatim OSM
    if len(s) >= 3:
        try:
            u_txt = "https://openstreetmap.org" + urllib.parse.quote(s)
            req = urllib.request.Request(u_txt, headers=ua)
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                for r in json.loads(resp.read().decode("utf-8")):
                    a = r.get("address", {})
                    reg = a.get("state") or ""
                    ct = a.get("city") or a.get("town") or a.get("village") or ""
                    st = a.get("road") or a.get("suburb") or ""
                    hs = a.get("house_number") or ""
                    pc = a.get("postcode") or z
                    parts = [p for p in [reg if reg != ct else "", (f"г. {ct}" if a.get("city") or a.get("town") else ct), st, ("д. " + hs if hs else "")] if p]
                    lbl = ", ".join(parts)
                    if lbl and not any(x["addr"] == lbl for x in out):
                        out.append({"addr": lbl, "zip": pc, "keep_typing": not bool(hs)})
        except Exception:
            pass
    return {"items": out[:15]}
