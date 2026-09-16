from telegram import Update
from telegram.ext import ContextTypes

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    # Сразу удаляем кнопки чтобы не висели как на скрине
    try:
        await q.edit_message_reply_markup(reply_markup=None)
    except:
        pass

    if q.data == "address":
        await q.message.reply_text(
            "📍 *RepairFix*\nСвебодзице, ul. Kolejowa 12\n⏰ Пн-Сб 10-18\n📞 +48 123 456 789",
            parse_mode="Markdown"
        )
    elif q.data == "call_master":
        await q.message.reply_text(
            "📞 *Звони мастеру:*\n+48 123 456 789\n\nИли оставь свой номер тут и мы сами наберем ⏰",
            parse_mode="Markdown"
        )
    else:
        await q.message.reply_text(
            "💰 *Прайс:*\n📱 Экран iPhone от 250 zl\n🔋 Батарея от 150 zl\n💻 Чистка ноута 120 zl\nДиагностика бесплатно! ✨",
            parse_mode="Markdown"
        )