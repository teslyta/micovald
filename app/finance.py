import json, csv, io, time
from datetime import datetime
from pathlib import Path
from notifier import send_email, get_cfg
from db_guard import atomic_save

DATA_DIR = Path("/app/data")
FIN_FILE = DATA_DIR / "finance.json"

def get_records() -> list:
    if not FIN_FILE.exists(): return []
    recs = json.loads(FIN_FILE.read_text(encoding="utf-8"))
    now, changed = time.time(), False
    for idx, r in enumerate(recs):
        if "id" not in r: r["id"] = 1000 + idx; changed = True
        if r.get("status") == "Ожидает оплаты" and (now - r.get("ts", now)) > 86400:
            r["status"], r["restore_cart"], changed = "Отменён (истекли 24ч)", True, True
            send_email(r.get("email", ""), f"[MICOVALD: Заказ №{r['id']}] отменён (истекли 24 ч.)", f"Здравствуйте, {r.get('fio')}!\nЗаказ №{r['id']} на сумму {r['amount']} ₽ не был оплачен за 24 часа и отменён.")
    if changed: save_records(recs)
    return recs

def save_records(recs: list):
    atomic_save(FIN_FILE, recs)

def add_order(fio: str, phone: str, email: str, zip_code: str, address: str, total: int, summary: str, items_json: str = "[]", utm: str = "Сайт"):
    recs, now = get_records(), time.time()
    if total <= 0 or any(r.get("phone")==phone and r.get("note")==summary and r.get("amount")==total and (now - r.get("ts",0)) < 60 for r in recs): return
    oid = int(now * 1000)
    is_live = bool(get_cfg().get("YOOKASSA_SHOP_ID", "").strip())
    st = "Ожидает оплаты" if is_live else "Оплачен"
    recs.insert(0, {"id": oid, "ts": now, "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "Приход", "status": st, "amount": total, "fio": fio, "phone": phone, "email": email, "zip": zip_code, "address": address, "track": "", "note": summary, "items_json": items_json, "restore_cart": False, "source": utm})
    save_records(recs)
    send_email(get_cfg().get("OWNER_EMAIL", ""), f"[MICOVALD: Новый заказ №{oid}] на {total} ₽ от {fio}", f"Поступил заказ №{oid} ({st})\nПокупатель: {fio}, тел. {phone}, Email: {email}\nДоставка: {zip_code}, {address}\nСостав: {summary}\nСумма: {total} ₽")
    if is_live:
        send_email(email, f"[MICOVALD: Заказ №{oid}] оформлен — ожидает оплаты", f"Здравствуйте, {fio}!\nВаш заказ №{oid} ({summary}) на сумму {total} ₽ ожидает оплаты.")
    else:
        send_email(email, f"[MICOVALD: Заказ №{oid}] Заказ принят и оплачен", f"Здравствуйте, {fio}!\nОплата {total} ₽ по заказу №{oid} ({summary}) успешно прошла! Электронный чек сформирован. Адрес доставки: {zip_code}, {address}.")
    return oid

def mark_paid(oid: int):
    recs = get_records()
    for r in recs:
        if r.get("id") == oid:
            r["status"] = "Оплачен"
            send_email(r.get("email", ""), f"[MICOVALD: Заказ №{oid}] Заказ принят и оплачен", f"Здравствуйте, {r.get('fio')}!\nОплата {r['amount']} ₽ по заказу №{oid} подтверждена. Электронный чек сформирован.")
    save_records(recs)

def update_order(oid: int, fio: str, phone: str, zip_code: str, address: str, status: str, track: str = ""):
    recs = get_records()
    for r in recs:
        if r.get("id") == oid:
            old_st = r.get("status")
            r.update({"fio": fio, "phone": phone, "zip": zip_code, "address": address, "status": status, "track": track})
            if status == "Отправлен" and (old_st != "Отправлен" or track):
                send_email(r.get("email", ""), f"[MICOVALD: Заказ №{oid}] отправлен Почтой России!", f"Здравствуйте, {fio}!\nЗаказ №{oid} отправлен Почтой России. Трек-номер: {track or 'уточняется'}.\nАдрес: {zip_code}, {address}")
    save_records(recs)

def add_manual(rtype: str, amount: int, note: str):
    recs = get_records()
    recs.insert(0, {"id": int(time.time() * 1000), "ts": time.time(), "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "type": rtype, "status": "Проведено", "amount": amount, "fio": "", "phone": "", "email": "", "zip": "", "address": "", "track": "", "note": note, "source": "Ручной ввод"})
    save_records(recs)

def refund_order(oid: int):
    recs = get_records()
    for r in recs:
        if r.get("id") == oid and r.get("status") != "Возврат (отменён)":
            r["status"] = "Возврат (отменён)"
            send_email(r.get("email", ""), f"[MICOVALD: Заказ №{oid}] отменён", f"Заказ №{oid} отменён. При наличии оплаты оформлен возврат средств.")
    save_records(recs)

def delete_record(oid: int):
    save_records([r for r in get_records() if r.get("id") != oid])

def export_kudir_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["КНИГА УЧЁТА ДОХОДОВ И РАСХОДОВ (УСН) — РАЗДЕЛ I", f"Актуальная форма КУДиР ФНС на {datetime.now().strftime('%d.%m.%Y')}"])
    w.writerow(["№ п/п (гр. 1)", "Дата и № документа (гр. 2)", "Содержание операции (гр. 3)", "Доходы, руб. (гр. 4)", "Расходы, руб. (гр. 5)"])
    idx, s_in, s_out = 1, 0, 0
    for r in reversed(get_records()):
        st = r.get("status", "")
        if st in ("Ожидает оплаты", "Тестовый заказ") or r.get("source") == "admin" or "тест" in r.get("fio", "").lower(): continue
        if r["type"] == "Приход":
            if st == "Возврат (отменён)":
                s_in -= r["amount"]; w.writerow([idx, f"От {r['date'][:10]} № {r['id']}-В", f"Возврат по заказу №{r['id']}", -r["amount"], 0]); idx += 1
            else:
                s_in += r["amount"]; w.writerow([idx, f"От {r['date'][:10]} № {r['id']}", f"Реализация: {r['note']} ({r.get('fio','')})", r["amount"], 0]); idx += 1
                if r.get("fio"): s_out += 350; w.writerow([idx, f"От {r['date'][:10]} № {r['id']}-П", f"Почтовые расходы по заказу №{r['id']}", 0, 350]); idx += 1
        elif r["type"] == "Расход":
            s_out += r["amount"]; w.writerow([idx, f"От {r['date'][:10]} № {r['id']}", r["note"], 0, r["amount"]]); idx += 1
    w.writerow([])
    w.writerow(["", "", "ИТОГО ДОХОДОВ И РАСХОДОВ:", s_in, s_out])
    w.writerow(["", "", "Налоговая база (УСН 15%):", max(0, s_in - s_out), ""])
    w.writerow(["", "", "Налог УСН 6% / УСН 15%:", f"{round(max(0, s_in)*0.06, 2)} ₽ (6%)", f"{round(max(0, s_in-s_out)*0.15, 2)} ₽ (15%)"])
    return buf.getvalue()
