from fastapi.testclient import TestClient
from main import app
from security import hash_pw, verify_pw, sign_session, verify_session
from store import check_stop_words

client = TestClient(app)

def run_tests():
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
    print("✅ ВСЕ АВТОТЕСТЫ (ВСЕ СТРАНИЦЫ, МЕНЮ БЕЗ ДУБЛЕЙ, БЕЗОПАСНОСТЬ, ФИЛЬТР) ПРОЙДЕНЫ!")

if __name__ == "__main__":
    run_tests()
