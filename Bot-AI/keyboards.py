from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def reply_menu():
    """Маленькая кнопка внизу экрана - всегда видна"""
    return ReplyKeyboardMarkup(
        [["📋 Меню"]],
        resize_keyboard=True,
        is_persistent=True
    )

def main_menu():
    """Всплывающее меню с адресом/ценами"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Ремонт iPhone", callback_data="price_iphone"),
         InlineKeyboardButton("💻 Ноутбуки", callback_data="price_laptop")],
        [InlineKeyboardButton("💰 Цены", callback_data="price_all"),
         InlineKeyboardButton("📍 Где мы", callback_data="address")],
        [InlineKeyboardButton("📞 Номер телефона", callback_data="call_master")]
    ])