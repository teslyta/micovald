import re
JUNK = ("йцукен", "фывапр", "ячсмит", "qwerty", "asdf", "zxcv", "тест", "test", "1234", "абвг")

def validate_order_data(fio: str, phone: str, zip_code: str, address: str) -> str:
    f, p, z, a = fio.strip(), phone.strip(), zip_code.strip(), address.strip()
    if not re.fullmatch(r"[А-Яа-яЁёA-Za-z\-]{2,30}(\s+[А-Яа-яЁёA-Za-z\-]{2,30}){1,3}", f):
        return "Укажите корректные Фамилию и Имя (только буквы, от 2 слов)"
    if re.search(r"(.)\1{3,}", f.lower()) or any(w in f.lower() for w in JUNK):
        return "В ФИО обнаружен некорректный набор символов"
    digits = re.sub(r"\D", "", p)
    if len(digits) != 11 or digits[0] not in ("7", "8"):
        return "Телефон должен содержать 11 цифр в формате +7 (999) 123-45-67"
    if not re.fullmatch(r"\d{6}", z) or z == "000000":
        return "Почтовый индекс РФ должен состоять ровно из 6 цифр"
    if len(a) < 10 or not re.search(r"[А-Яа-яЁё]{3,}", a) or not re.search(r"\d+", a):
        return "Укажите полный адрес: город, улицу и номер дома"
    return ""
