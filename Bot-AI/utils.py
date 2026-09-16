import re

# Черный список фейков
FAKE_NUMBERS = {
    "000000000", "111111111", "222222222", "333333333", "444444444",
    "555555555", "666666666", "777777777", "888888888", "999999999",
    "123456789", "987654321", "123123123", "321321321", "000123456",
    "123456000", "111222333", "123123321"
}

def is_valid_polish_phone(digits_9: str) -> bool:
    """Проверяет 9 цифр польского номера"""
    if len(digits_9) != 9:
        return False
    if not digits_9.isdigit():
        return False
    if digits_9 in FAKE_NUMBERS:
        return False
    # Все цифры одинаковые 777777
    if len(set(digits_9)) == 1:
        return False
    # 5+ одинаковых подряд 55555
    if re.search(r'(\d)\1{4,}', digits_9):
        return False
    # Польские номера не начинаются с 0
    if digits_9.startswith("0"):
        return False
    # Последовательность 123456789 уже в блеклисте, но еще проверим
    # 123456, 234567 и т.д.
    sequential = "0123456789"
    if digits_9 in sequential or digits_9 in sequential[::-1]:
        return False
    return True

def normalize_polish(phone_raw: str) -> str | None:
    """Приводит к +48 XXX XXX XXX если валидный"""
    # Убираем все кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', phone_raw)
    
    # Убираем 0048 / +48 / 48
    digits = cleaned
    if digits.startswith("+48"):
        digits = digits[3:]
    elif digits.startswith("0048"):
        digits = digits[4:]
    elif digits.startswith("48") and len(digits) == 11:
        digits = digits[2:]
    
    # Должно остаться 9 цифр
    if len(digits) != 9:
        return None
    
    if not is_valid_polish_phone(digits):
        return None
    
    # Красивый формат: +48 123 456 789
    return f"+48 {digits[0:3]} {digits[3:6]} {digits[6:9]}"

def find_phone(text: str) -> str | None:
    """
    Ищет в тексте ТОЛЬКО польский номер.
    Возвращает нормализованный +48 XXX XXX XXX или None
    """
    # Ищем все похожее на номера: +48 xxx xxx xxx, xxx-xxx-xxx, 9 цифр подряд
    patterns = [
        r'\+48[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{3}',
        r'0048[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}',
        r'48[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}',
        r'\b\d{3}[\s\-]?\d{3}[\s\-]?\d{3}\b',
        r'\b\d{9}\b'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for m in matches:
            raw = m.group(0)
            normalized = normalize_polish(raw)
            if normalized:
                print(f"✅ Валидный PL номер: {normalized} из {raw}")
                return normalized
    
    print(f"❌ Нет валидного PL номера в: {text}")
    return None

def is_denied(text):
    deny = ["кнопочн","бабушкофон","принтер","мфу","картридж","телевизор","холодильник","стиралк"]
    return any(w in text.lower() for w in deny) and len(text) < 50