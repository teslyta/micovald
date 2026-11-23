from email.utils import formatdate, make_msgid
import smtplib, ssl
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path

LOG_MAIL = Path("/app/data/sent_emails.log")

def get_cfg() -> dict:
    p = Path("/app/integrations.txt")
    return dict(l.split("=", 1) for l in p.read_text().splitlines() if "=" in l and not l.startswith("#")) if p.exists() else {}

def send_email(to_email: str, subject: str, body: str):
    if not to_email or "@" not in to_email: return
    cfg = get_cfg()
    with open(LOG_MAIL, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] TO: {to_email} | {subject}\n{body}\n{'-'*30}\n")
    host, user, pw = cfg.get("SMTP_HOST", "").strip(), cfg.get("SMTP_USER", "").strip(), cfg.get("SMTP_PASS", "").strip()
    if host and user and pw:
        try:
            msg = EmailMessage()
            msg["Subject"], msg["From"], msg["To"] = subject, user, to_email
            msg["Date"], msg["Message-ID"] = formatdate(localtime=True), make_msgid(domain="yandex.ru")
            msg.set_content(body + '\n\n--\nС уважением, MICOVALD\nРешения для фермеров и сельхозпредприятий\nИндивидуальный подбор почвенных субстратов MICOVALD под ваши культуры, оптовые партии, консультации микробиолога и сопроводительная документация.\nСайт: https://micovald.ru | Почта: micovald@yandex.ru')
            with smtplib.SMTP_SSL(host, int(cfg.get("SMTP_PORT") or 465), context=ssl.create_default_context(), timeout=5) as s:
                s.login(user, pw); s.send_message(msg)
        except Exception as e:
            print("SMTP_ERR:", e, flush=True)

def send_2fa_code(target_email: str, target_phone: str, code: str, action: str = "вход в кабинет", prefer: str = "auto") -> str:
    text = f"MICOVALD: Код подтверждения ({action}): {code}. Никому не сообщайте этот код."
    cfg = get_cfg()
    ph = "".join(c for c in (target_phone or "") if c.isdigit())
    if len(ph) == 11 and ph.startswith("8"): ph = "7" + ph[1:]
    em = (target_email or "").strip()

    if prefer != "email" and len(ph) == 11:
        with open(LOG_MAIL, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] SMS TO: +{ph} | {text}\n{'-'*30}\n")
        sms_key = cfg.get("SMS_RU_API_ID", "").strip()
        if sms_key:
            try:
                import urllib.request, urllib.parse
                urllib.request.urlopen(f"https://sms.ru{sms_key}&to={ph}&msg={urllib.parse.quote(text)}&json=1", timeout=4)
            except Exception as e:
                print("SMS_ERR:", e, flush=True)
        return "phone"

    if em and "@" in em:
        send_email(em, f"[MICOVALD: Код безопасности] {code}", text)
        return "email"
    return ""
