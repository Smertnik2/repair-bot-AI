# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import ContextTypes
import os
from datetime import datetime
from handlers.text import LANG_TEXT, generate_order_id, save_order_db, create_order_card, get_status_keyboard, save_lead
from config import ADDRESS

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id < 0:
        return

    uid = update.effective_chat.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    path = f"device_{uid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    await file.download_to_drive(path)
    context.user_data['last_photo'] = path

    # 1. ЕСЛИ КЛИЕНТ КИНУЛ ФОТО ПОСЛЕ ПРОСЬБЫ УТОЧНИТЬ МОДЕЛЬ
    if context.user_data.get('pending_phone'):
        phone = context.user_data['pending_phone']
        issue = context.user_data.get('pending_issue', 'Диагностика')
        lang = context.user_data.get('last_lang') or 'ru'
        lt = LANG_TEXT.get(lang, LANG_TEXT['ru'])
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name

        order_id = generate_order_id()
        order = {
            "id": order_id, "uid": uid, "phone": phone, "username": username,
            "model": "По фото - уточнить",
            "issue": issue[:60],
            "price": LANG_TEXT[lang]['diag'],
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "updated": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "status": "ОФОРМЛЕН",
            "photo_path": path,
            "lang": lang
        }
        save_order_db(order)
        try:
            from handlers.gsheet import sync_order_to_sheet
            sync_order_to_sheet(order)
        except:
            pass

        img = create_order_card(order)
        kb = get_status_keyboard(order_id)
        await save_lead(context.bot, f"{phone} | {order_id} | {order['model']} (по фото)", username, issue, f"Заказ {order_id}", uid, reply_markup=kb)

        if img and os.path.exists(img):
            await update.message.reply_photo(photo=open(img, "rb"), caption=lt['order_done'].format(id=order_id, model=order['model'], phone=phone, addr=ADDRESS), parse_mode="Markdown")

        context.user_data.clear()
        return

    # 2. ОБЫЧНЫЙ ПРИЕМ ФОТО - быстрая оценка без обещаний времени и гарантии
    await update.message.reply_text("Фото принял! 📸🔧 Похоже на замену экрана ~350 zl 💰 Время ремонта уточним после диагностики. Оставь номер? 📞")