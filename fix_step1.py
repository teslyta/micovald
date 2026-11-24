import pathlib, json

# 1. Очищаем тестовую запись XSS из analytics.json и запрещаем запись хакерских строк в упущенный спрос
af = pathlib.Path("data/analytics.json")
if af.exists():
    d = json.loads(af.read_text(encoding="utf-8"))
    d["missed"] = [m for m in d.get("missed", []) if "<script" not in m.get("q", "").lower() and "alert(" not in m.get("q", "").lower()]
    af.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

pa = pathlib.Path("app/analytics.py")
if pa.exists():
    ta = pa.read_text(encoding="utf-8")
    if "def track_missed_search" in ta and "<script" not in ta:
        ta = ta.replace("def track_missed_search(q: str, user: str = \"\"):", "def track_missed_search(q: str, user: str = \"\"):\n    if any(k in (q or \"\").lower() for k in (\"<script\", \"alert(\", \"select \", \"drop \", \"onerror=\")): return")
        pa.write_text(ta, encoding="utf-8")

# 2. Добавляем дату в имя файла отчета КУДиР для налоговой (KUDiR_MICOVALD_FNS_YYYY-MM-DD.csv)
pm = pathlib.Path("app/main.py")
tm = pm.read_text(encoding="utf-8")
tm = tm.replace(
    'headers={"Content-Disposition": "attachment; filename=KUDiR_MICOVALD_FNS.csv"}',
    'headers={"Content-Disposition": f"attachment; filename=KUDiR_MICOVALD_FNS_{time.strftime(\'%Y-%m-%d\')}.csv"}'
)

# 3. Добавляем отправку письма производителю при сообщении в чате с темой "Чат: {username}"
old_chat_send = 'add_chat_msg(u, "user", text, prod_name)'
new_chat_send = '''add_chat_msg(u, "user", text, prod_name)
    try:
        from notifier import send_email_notify
        send_email_notify(f"Чат: {u}", f"Покупатель {u} написал в чат:\\n{text}\\nТовар: {prod_name or 'Общий вопрос'}")
    except Exception: pass'''
if 'send_email_notify(f"Чат:' not in tm:
    tm = tm.replace(old_chat_send, new_chat_send)

# Передаем счетчик непрочитанных чатов для админа (admin_unread_chat) и страницу избранного /favorites
tm = tm.replace(
    '"unread_chat": count_unread_for_user(u),',
    '"unread_chat": count_unread_for_user(u), "admin_unread_chat": count_unread_for_admin(),'
)
if '@app.get("/favorites")' not in tm:
    tm += """
@app.get("/favorites", response_class=HTMLResponse)
async def favorites_page(request: Request):
    return templates.TemplateResponse(request, "favorites.html", ctx(request))
"""
pm.write_text(tm, encoding="utf-8")
