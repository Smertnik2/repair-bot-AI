REAL_PRICES = {
    "iphone_15_battery": "360-460 zl (iSpot акция 360 zl, обычная 460 zl)",
    "iphone_15_plus_battery": "400-500 zl",
    "iphone_15_pro_battery": "400-500 zl",
    "iphone_15_pro_max_battery": "400-500 zl",
    "iphone_15_screen_orig": "999 zl",
    "iphone_15_plus_screen_orig": "1199 zl",
    "iphone_15_pro_max_screen_orig": "1299-1349 zl",
    "iphone_15_rear_glass": "599-999 zl",
    "iphone_15_camera_glass": "349 zl",
    "iphone_14_screen": "700-900 zl",
    "iphone_13_screen": "500-700 zl",
    "iphone_12_screen": "400-600 zl",
    "iphone_11_screen": "300-450 zl",
    "iphone_12_13_14_battery": "200-300 zl",
    "iphone_11_battery": "150-250 zl",
    "samsung_screen_s": "500-700 zl",
    "samsung_screen_a": "250-400 zl",
    "samsung_battery": "150-220 zl",
    "xiaomi_screen": "180-350 zl",
    "xiaomi_battery": "120-180 zl",
    "laptop_cleaning": "от 150 zl стандарт, 180 zl геймерский, до 375 zl премиум",
    "laptop_cleaning_hp": "от 100 zl",
    "laptop_screen_14_15": "300-600 zl",
    "laptop_battery": "200-450 zl",
    "laptop_keyboard": "150-300 zl",
}

def get_price_text(query: str) -> str:
    q = query.lower()
    if "15 pro max" in q and "экран" in q: return REAL_PRICES["iphone_15_pro_max_screen_orig"]
    if "15 plus" in q and "экран" in q: return REAL_PRICES["iphone_15_plus_screen_orig"]
    if "15" in q and "экран" in q: return REAL_PRICES["iphone_15_screen_orig"]
    if "15" in q and "батаре" in q: return REAL_PRICES["iphone_15_battery"]
    if "батаре" in q: return REAL_PRICES["iphone_12_13_14_battery"]
    if "чистка" in q: return REAL_PRICES["laptop_cleaning"]
    if "экран" in q and "ноут" in q: return REAL_PRICES["laptop_screen_14_15"]
    return "Диагностика 0 zl, точную цену скажем за 10 мин"