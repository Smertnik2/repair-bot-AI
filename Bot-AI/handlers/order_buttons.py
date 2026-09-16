from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from orders import STATUSES, update_order_status, get_order, create_order_card

def get_status_keyboard(order_id):
    buttons = [
        [InlineKeyboardButton("🔵 Принят", callback_data=f"st:{order_id}:ПРИНЯТ"),
         InlineKeyboardButton("🟠 В работе", callback_data=f"st:{order_id}:В РАБОТЕ")],
        [InlineKeyboardButton("🟢 Готов", callback_data=f"st:{order_id}:ГОТОВ"),
         InlineKeyboardButton("⚫ Выдан", callback_data=f"st:{order_id}:ВЫДАН")]
    ]
    return InlineKeyboardMarkup(buttons)

async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        _, order_id, new_status = query.data.split(":", 2)
        order = update_order_status(order_id, new_status)
        if not order:
            await query.edit_message_text(f"Заказ {order_id} не найден")
            return
        
        img_path = create_order_card(order)
        status_info = STATUSES[new_status]
        
        # Обновляем сообщение мастеру
        await query.edit_message_text(
            f"✅ Статус изменен!\n\n📦 {order_id}\n📞 {order['phone']}\n{status_info['text']}\n{status_info['desc']}",
            reply_markup=get_status_keyboard(order_id)
        )
        
        # Отправляем клиенту новую картинку (если у нас есть его chat_id)
        try:
            if 'uid' in order:
                await context.bot.send_photo(
                    chat_id=order['uid'],
                    photo=open(img_path, "rb"),
                    caption=f"📦 Заказ *{order_id}* обновлен!\n\n{status_info['text']}\n{status_info['desc']}\n\nМодель: {order['model']}",
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"Не смог отправить клиенту: {e}")

    except Exception as e:
        print(f"Ошибка статуса: {e}")