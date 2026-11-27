from fastapi.testclient import TestClient
from main import app
from security import hash_pw, verify_pw, sign_session, verify_session
from store import check_stop_words

client = TestClient(app)

def run_tests():
    import pathlib
    pf = pathlib.Path('/app/data/promos.json')
    promos_backup = pf.read_text(encoding='utf-8') if pf.exists() else None
    for path in ["/", "/category/substrates", "/cart", "/encyclopedia", "/about", "/farmers", "/how-to-order", "/login", "/register"]:
        r = client.get(path)
        assert r.status_code == 200, f"Ошибка 404/500 на {path}"
    home_html = client.get("/").text
    assert home_html.count(">Для фермеров<") == 1, "Дубль ссылки Для фермеров в меню!"
    assert client.get("/owner", follow_redirects=False).status_code == 303
    tok = sign_session("admin")
    assert verify_session(tok) == "admin" and verify_session(tok + "x") == ""
    h = hash_pw("Secret123")
    assert verify_pw("Secret123", h) and not verify_pw("Wrong", h)
    assert "удобрение" in check_stop_words("Лучшее удобрение")
    from validators import validate_order_data
    assert validate_order_data("123", "123", "abc", "x") != ""
    assert validate_order_data("Иванов Иван", "+7 (999) 123-45-67", "190000", "г. Санкт-Петербург, Невский пр., д. 1") == ""
    from db_guard import atomic_save
    import tempfile, pathlib
    tf = pathlib.Path(tempfile.mktemp())
    atomic_save(tf, {"ok": 1}); assert tf.exists() and not list(tf.parent.glob("*.tmp"))
    tf.unlink(missing_ok=True)
    for secret_path in ["/data/finance.json", "/data/users.json", "/owner/export.csv", "/integrations.txt"]:
        assert client.get(secret_path, follow_redirects=False).status_code in (303, 403, 404), f"Утечка {secret_path}!"
    assert client.get("/promos").status_code == 200, "Ошибка страницы /promos"
    assert client.get("/data/promos.json", follow_redirects=False).status_code in (303, 403, 404), "Утечка promos.json!"
    from promos import save_promo, get_active_promo, archive_promo
    save_promo(0, "Тест акция", "Условия теста", 15, "2020-01-01", "2020-01-02")
    assert get_active_promo() is None, "Просроченная акция не ушла в архив!"
    home_html = client.get("/").text
    assert "viewport" in home_html and "repeat(2, minmax(0, 1fr))" in client.get("/media/style.css").text, "Нет мобильной адаптации!"
    assert client.get("/media/products/p1.webp").status_code == 200, "Картинки товаров не отдаются!"
    for pr in ["Для почвы", "Теплица и рассада", "Открытый грунт и сад"]:
        assert "Не найдено" not in client.get(f"/?cat=purp:{pr}").text and "₽" in client.get(f"/?cat=purp:{pr}").text, f"Пустой фильтр {pr}!"
    assert "MICOVALD: Код подтверждения (2FA)" in open("/app/notifier.py").read(), "Изменилась тема 2FA!"
    from main import get_products
    p0 = get_products()
    assert client.get(f"/product/{next(iter(p0))['id']}").status_code == 200, "Ошибка карточки товара!"
    assert client.get("/chat").status_code == 200, "Чат должен быть доступен без авторизации!"
    if promos_backup is not None: pf.write_text(promos_backup, encoding="utf-8")
    print("✅ ВСЕ АВТОТЕСТЫ (ВСЕ СТРАНИЦЫ, МЕНЮ БЕЗ ДУБЛЕЙ, БЕЗОПАСНОСТЬ, ФИЛЬТР) ПРОЙДЕНЫ!")

if __name__ == "__main__":
    run_tests()
