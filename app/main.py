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

def ctx(request: Request, **extra):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    return {"request": request, "tax": get_tax(), "active_promo": get_active_promo(), "user": u, "is_admin": is_admin_user(u), "tax": get_tax(), "active_promo": get_active_promo(), "undo": get_undo() if u in [k for k, v in load_users().items() if k == "admin" or v.get("role") == "admin"] else None, **extra}

@app.get("/", response_class=HTMLResponse)
@app.get("/category/{slug}", response_class=HTMLResponse)
async def home(request: Request, slug: str = "", q: str = "", cat: str = "", purp: str = ""):
    items = [x for x in get_products() if (not slug or x.get("slug")==slug) and (not cat or x.get("cat")==cat) and (not purp or x.get("purp")==purp) and (not q or q.lower() in x["name"].lower())]
    u_q = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if q.strip() and not items and not is_admin_user(u_q): track_missed_search(q, u_q)
    return templates.TemplateResponse(request, "home.html", ctx(request, slug=slug, q=q, products=items, tax=get_tax(), cat=cat, purp=purp))

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
    return RedirectResponse("/owner?msg=1", 303)

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
    return templates.TemplateResponse(request, "account.html", ctx(request, msg=msg, prof=load_users().get(u, {}), my_orders=my_orders, farmers=get_farmers()))

@app.post("/account/profile")
async def save_prof(request: Request, fio: str = Form(""), email: str = Form(...), phone: str = Form("")):
    u = verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))
    if not u: return RedirectResponse("/login", 303)
    users = load_users()
    users[u]["fio"], users[u]["email"], users[u]["phone"] = fio.strip(), email.strip(), phone.strip()
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2))
    return RedirectResponse("/account?msg=1", 303)

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
    return RedirectResponse("/account?msg=1", 303)

@app.get("/order/create")
async def order_get_redir(): return RedirectResponse("/cart", 303)

@app.post("/order/create")
async def create_order(request: Request, fio: str = Form(...), phone: str = Form(...), email: str = Form(...), zip_code: str = Form(...), address: str = Form(...), total: int = Form(...), summary: str = Form(...)):
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
    return RedirectResponse("/account?msg=1", 303)

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
    return templates.TemplateResponse(request, "owner.html", ctx(request, topics=get_topics(), farmers=get_farmers(), msg=msg, recs=recs, inc=inc, exp=exp, adm_2fa=adm.get("2fa", False), all_users=load_users(), stats=get_stats(), promos=get_promos()))

@app.post("/owner/lecture")
async def save_lec(request: Request, topic: str = Form(...), new_cat: str = Form(""), new_desc: str = Form(""), lec_id: int = Form(0), title: str = Form(...), text: str = Form(""), photo: UploadFile = File(None)):
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
async def save_about(request: Request, title: str = Form(...), text: str = Form(...), photo: UploadFile = File(None)):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    ab = get_about(); ab["title"], ab["text"] = title, text
    if photo and photo.filename: ab["img"] = await save_safe_image(photo, "about")
    ABOUT_FILE.write_text(json.dumps(ab, ensure_ascii=False, indent=2), encoding="utf-8")
    return RedirectResponse("/about", 303)

@app.post("/owner/finance")
async def owner_fin(request: Request, ftype: str = Form(...), amount: int = Form(...), note: str = Form(...)):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FIN_FILE, "добавление записи", "/owner"); add_manual(ftype, amount, note)
    return RedirectResponse("/owner?msg=1", 303)

@app.post("/owner/order/paid/{oid}")
async def owner_ord_paid(request: Request, oid: int):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FIN_FILE, "подтверждение оплаты", "/owner"); mark_paid(oid)
    return RedirectResponse("/owner?msg=1", 303)

@app.post("/owner/order/edit/{oid}")
async def owner_ord_edit(request: Request, oid: int, fio: str = Form(...), phone: str = Form(...), zip_code: str = Form(...), address: str = Form(...), status: str = Form(...), track: str = Form("")):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        save_undo(FIN_FILE, "изменение заказа", "/owner"); update_order(oid, fio, phone, zip_code, address, status, track)
    return RedirectResponse("/owner?msg=1", 303)

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
    return RedirectResponse("/owner?msg=1", 303)

@app.get("/owner/export.csv")
async def owner_csv(request: Request):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    return Response("\ufeff" + export_kudir_csv(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=KUDiR_MICOVALD_FNS.csv"})

@app.post("/owner/2fa")
async def toggle_2fa(request: Request, enable: str = Form("0")):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))):
        users = load_users(); users["admin"]["2fa"] = (enable == "1")
        USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2))
    return RedirectResponse("/owner?msg=1", 303)

@app.post("/owner/undo")
async def do_undo(request: Request):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    return RedirectResponse(apply_undo(), 303)

@app.get("/logout")
async def logout():
    r = RedirectResponse("/", 303); r.delete_cookie("user"); return r

@app.post("/owner/product-save")
async def save_prod_full(request: Request, pid: int = Form(0), name: str = Form(...), desc: str = Form(""), price: int = Form(...), cat: str = Form(...), new_cat: str = Form(""), purp: str = Form(...), new_purp: str = Form(""), photo: UploadFile = File(None)):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    c_val = new_cat.strip() or cat
    p_val = new_purp.strip() or purp
    if check_stop_words(f"{name} {desc} {c_val} {p_val}"): return RedirectResponse("/?err=stop", 303)
    if new_cat.strip(): add_tax("directions", c_val)
    if new_purp.strip(): add_tax("purposes", p_val)
    old = next((x for x in get_products() if x["id"] == pid), {}) if pid > 0 else {}
    img_url = await save_safe_image(photo, "products") if (photo and photo.filename) else old.get("img", "/media/products/p1.webp")
    save_undo(PROD_FILE, "изменение каталога", "/")
    save_product({"name": name, "desc": desc, "slug": "substrates" if "субстрат" in c_val.lower() else "sets", "cat": c_val, "purp": p_val, "price": price, "img": img_url}, pid)
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
    return RedirectResponse("/owner?msg=1", 303)

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
    return RedirectResponse("/account?msg=1", 303)

@app.post("/owner/promo/save")
async def owner_promo_save(request: Request, pid: int = Form(0), title: str = Form(...), desc: str = Form(...), discount: int = Form(10), start_date: str = Form(...), end_date: str = Form(...)):
    if not is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): return RedirectResponse("/login", 303)
    if check_stop_words(f"{title} {desc}"): return RedirectResponse("/owner?err=stop", 303)
    save_promo(pid, title, desc, discount, start_date, end_date)
    return RedirectResponse("/owner?msg=1", 303)

@app.post("/owner/promo/archive/{pid}")
async def owner_promo_arch(request: Request, pid: int):
    if is_admin_user(verify_session(request.cookies.get("user", ""), request.headers.get("user-agent", ""))): archive_promo(pid)
    return RedirectResponse("/owner?msg=1", 303)

@app.get("/promos", response_class=HTMLResponse)
async def promos_page(request: Request):
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    act = [p for p in get_promos() if p.get("active") and p.get("start_date", "") <= today <= p.get("end_date", "9999-12-31")]
    return templates.TemplateResponse(request, "promos.html", ctx(request, active_promos=act))
