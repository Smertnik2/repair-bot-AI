# -*- coding: utf-8 -*-
import os, re, json, sqlite3, tempfile, asyncio
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, ADMIN_CHAT_ID as GROUP_ID
from handlers.text import create_order_card, get_status_keyboard

DB_PATH = "repairfix.db"

REMIND_TEXT = {
    'pl': "Cześć! 📱 Twój telefon {model} ({id}) jest GOTOWY do odbioru od {date} w RepairFix, ul. Kolejowa 12.\nCzekamy 10:00-18:00. Daj znać kiedy będziesz!",
    'ru': "Привет! 📱 Твой телефон {model} ({id}) ГОТОВ с {date} в RepairFix, ул. Колейова 12.\nЖдем 10:00-18:00. Напиши когда заберешь!",
    'uk': "Привіт! 📱 Твій телефон {model} ({id}) ГОТОВИЙ з {date} в RepairFix, вул. Колейова 12.\nЧекаємо 10:00-18:00. Напиши коли забереш!"
}
REMIND_TEXT_7 = {
    'pl': "🔔 Przypomnienie: telefon {model} ({id}) nadal czeka od {date}.",
    'ru': "🔔 Напоминание: телефон {model} ({id}) все еще у нас с {date}.",
    'uk': "🔔 Нагадування: телефон {model} ({id}) досі у нас з {date}."
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY, uid INTEGER, phone TEXT, username TEXT, model TEXT, issue TEXT, price TEXT, date TEXT, updated TEXT, status TEXT, warranty_months INTEGER, warranty_from TEXT, warranty_to TEXT, warranty_text TEXT, photo_path TEXT, lang TEXT, reminded TEXT, reminded_7 TEXT)''')
    for col in ["lang TEXT", "reminded TEXT", "reminded_7 TEXT", "photo_path TEXT"]:
        try: c.execute(f"ALTER TABLE orders ADD COLUMN {col}")
        except: pass
    conn.commit(); conn.close()

def get_order(order_id):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    c = conn.cursor(); c.execute("SELECT * FROM orders WHERE id=?", (order_id,)); row=c.fetchone(); conn.close()
    return dict(row) if row else None

def update_order_status(order_id, new_status=None, warranty=None):
    init_db()
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    c = conn.cursor(); c.execute("SELECT * FROM orders WHERE id=?", (order_id,)); row=c.fetchone()
    if not row: conn.close(); return None
    o=dict(row)
    if warranty:
        months=int(warranty); to_date=datetime.now()+timedelta(days=30*months)
        o['warranty_months']=months; o['warranty_from']=datetime.now().strftime("%d.%m.%Y"); o['warranty_to']=to_date.strftime("%d.%m.%Y"); o['warranty_text']=f"{months} мес до {o['warranty_to']}"; o['updated']=datetime.now().strftime("%d.%m.%Y %H:%M")
    if new_status:
        o['status']=new_status; o['updated']=datetime.now().strftime("%d.%m.%Y %H:%M")
        if new_status=="ВЫДАН": o['reminded']=None; o['reminded_7']=None
    c.execute("UPDATE orders SET status=?, updated=?, warranty_months=?, warranty_from=?, warranty_to=?, warranty_text=?, reminded=?, reminded_7=? WHERE id=?",
              (o.get('status'),o.get('updated'),o.get('warranty_months'),o.get('warranty_from'),o.get('warranty_to'),o.get('warranty_text'),o.get('reminded'),o.get('reminded_7'),order_id))
    conn.commit(); conn.close(); return get_order(order_id)

def find_orders(query):
    init_db(); conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; c = conn.cursor()
    like=f"%{query}%"; c.execute("SELECT * FROM orders WHERE phone LIKE? OR id LIKE? OR model LIKE? ORDER BY date DESC LIMIT 10", (like,like,like)); rows=c.fetchall(); conn.close()
    return [dict(r) for r in rows]

def get_stats():
    init_db(); conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT status, COUNT(*) FROM orders GROUP BY status"); stats=dict(c.fetchall())
    c.execute("SELECT COUNT(*) FROM orders WHERE date LIKE?", (f"%{datetime.now().strftime('%d.%m.%Y')}%",)); today=c.fetchone()[0]; conn.close()
    return stats, today

def get_price_keyboard(order_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("0 zl диагн.", callback_data=f"pr:{order_id}:0"), InlineKeyboardButton("150 zl", callback_data=f"pr:{order_id}:150"), InlineKeyboardButton("250 zl", callback_data=f"pr:{order_id}:250")],
        [InlineKeyboardButton("350 zl", callback_data=f"pr:{order_id}:350"), InlineKeyboardButton("450 zl", callback_data=f"pr:{order_id}:450"), InlineKeyboardButton("550 zl", callback_data=f"pr:{order_id}:550")],
        [InlineKeyboardButton("◀ Назад", callback_data=f"back:{order_id}")]
    ])

async def safe_edit(q, text, reply_markup=None):
    try:
        if q.message.photo or q.message.document: await q.edit_message_caption(caption=text, reply_markup=reply_markup)
        else: await q.edit_message_text(text=text, reply_markup=reply_markup)
    except:
        try: await q.message.reply_text(text, reply_markup=reply_markup)
        except: pass

def extract_order_id(text):
    m = re.search(r'RF-\d{8}-\d{3,4}', text.upper())
    return m.group(0) if m else None

def extract_price(text):
    if re.search(r'\b\d{9}\b', text): return None
    t=text.lower()
    m=re.search(r'(?:цена|cena|price)?\s*(\d{2,4})\s*(?:zl|зл|zlo|pln)?', t)
    if m:
        p=int(m.group(1))
        if 10<=p<=5000: return p
    return None

async def daily_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; c=conn.cursor()
    c.execute("SELECT * FROM orders WHERE status='ГОТОВ'"); rows=[dict(r) for r in c.fetchall()]; conn.close()
    now=datetime.now()
    for o in rows:
        try:
            upd=datetime.strptime(o.get('updated') or o.get('date'), "%d.%m.%Y %H:%M")
            days=(now-upd).days
            lang=o.get('lang') or 'pl'
            if lang not in REMIND_TEXT: lang='pl'
            if days>=2 and o.get('reminded')!=now.strftime("%d.%m.%Y"):
                text=REMIND_TEXT[lang].format(model=o.get('model','телефон'), id=o['id'], date=o.get('updated'))
                if o.get('uid'):
                    try: await context.bot.send_message(chat_id=o['uid'], text=text)
                    except: pass
                await context.bot.send_message(chat_id=GROUP_ID, text=f"🔔 Напомнил (2д) {o['id']} {o.get('phone')}")
                conn=sqlite3.connect(DB_PATH); c=conn.cursor(); c.execute("UPDATE orders SET reminded=? WHERE id=?", (now.strftime("%d.%m.%Y"), o['id'])); conn.commit(); conn.close()
            if days>=7 and not o.get('reminded_7'):
                text2=REMIND_TEXT_7[lang].format(model=o.get('model','телефон'), id=o['id'], date=o.get('updated'))
                if o.get('uid'):
                    try: await context.bot.send_message(chat_id=o['uid'], text=text2)
                    except: pass
                await context.bot.send_message(chat_id=GROUP_ID, text=f"🔔🔔 Повторно (7д) {o['id']}")
                conn=sqlite3.connect(DB_PATH); c=conn.cursor(); c.execute("UPDATE orders SET reminded_7=? WHERE id=?", (now.strftime("%d.%m.%Y"), o['id'])); conn.commit(); conn.close()
        except Exception as e: print(f"remind err {e}")

async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    _, oid, ns = q.data.split(":",2)
    order=update_order_status(oid, new_status=ns)
    if not order: return
    img=create_order_card(order)
    await safe_edit(q, f"✅ {oid}\nСтатус: {ns}\nДата: {order.get('updated')}", get_status_keyboard(oid))
    if img and os.path.exists(img):
        await context.bot.send_photo(chat_id=GROUP_ID, photo=open(img,"rb"), caption=f"{ns} | {oid}")

async def warranty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    _, oid, months = q.data.split(":",2)
    order=update_order_status(oid, warranty=months)
    if not order: return
    img=create_order_card(order)
    await safe_edit(q, f"🛡 {oid}\nГарантия: {months} мес до {order.get('warranty_to')}", get_status_keyboard(oid))
    if img and os.path.exists(img):
        await context.bot.send_photo(chat_id=GROUP_ID, photo=open(img,"rb"), caption=f"🛡 {oid} гарантия {months} мес")

async def price_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    _, oid = q.data.split(":",1)
    await safe_edit(q, f"💰 Выбери цену для {oid}:", get_price_keyboard(oid))

async def price_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    _, oid, price = q.data.split(":",2)
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("UPDATE orders SET price=?, updated=? WHERE id=?", (f"{price} zl", datetime.now().strftime("%d.%m.%Y %H:%M"), oid)); conn.commit(); conn.close()
    await safe_edit(q, f"💰 {oid} цена: {price} zl", get_status_keyboard(oid))

async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    _, oid = q.data.split(":",1)
    await safe_edit(q, f"Заказ {oid}", get_status_keyboard(oid))

async def pdf_warranty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer(text="⏳ Генерирую PDF...")
    except: pass
    _, oid = q.data.split(":",1)
    order=get_order(oid)
    if not order: return
    try:
        from handlers.pdf_generator import create_warranty_pdf
        from config import BOT_USERNAME
        await safe_edit(q, f"⏳ Генерирую гарантию {oid}...", get_status_keyboard(oid))
        pdf_path = await asyncio.to_thread(create_warranty_pdf, order, BOT_USERNAME, order.get('lang') or 'pl')
        await context.bot.send_document(chat_id=GROUP_ID, document=open(pdf_path,"rb"), filename=os.path.basename(pdf_path), caption=f"📄 Гарантия {oid}", reply_markup=get_status_keyboard(oid))
        try:
            if order.get('uid'): await context.bot.send_document(chat_id=order['uid'], document=open(pdf_path,"rb"), filename=os.path.basename(pdf_path), caption=f"📄 Ваша гарантия {oid}")
        except: pass
        if os.path.exists(pdf_path): os.remove(pdf_path)
    except Exception as e:
        await context.bot.send_message(chat_id=GROUP_ID, text=f"❌ Ошибка PDF: {e}")

async def pdf_receipt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer(text="⏳ Генерирую чек...")
    except: pass
    _, oid = q.data.split(":",1)
    order=get_order(oid)
    if not order: return
    try:
        from handlers.pdf_generator import create_receipt_pdf
        await safe_edit(q, f"⏳ Генерирую чек {oid}...", get_status_keyboard(oid))
        pdf_path = await asyncio.to_thread(create_receipt_pdf, order, order.get('lang') or 'pl')
        await context.bot.send_document(chat_id=GROUP_ID, document=open(pdf_path,"rb"), filename=os.path.basename(pdf_path), caption=f"🧾 Чек {oid}", reply_markup=get_status_keyboard(oid))
        if os.path.exists(pdf_path): os.remove(pdf_path)
    except Exception as e:
        await context.bot.send_message(chat_id=GROUP_ID, text=f"❌ Ошибка чека: {e}")

async def admin_price_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id!= GROUP_ID: return
    text=update.message.text or ""
    if text.startswith("/"): return
    price=extract_price(text)
    if not price: return
    order_id=extract_order_id(text)
    if not order_id and update.message.reply_to_message:
        reply=(update.message.reply_to_message.text or "")+" "+(update.message.reply_to_message.caption or "")
        order_id=extract_order_id(reply)
    if not order_id:
        conn=sqlite3.connect(DB_PATH); c=conn.cursor(); c.execute("SELECT id FROM orders ORDER BY date DESC LIMIT 1"); row=c.fetchone(); conn.close()
        if row: order_id=row[0]
    if not order_id or not get_order(order_id): return
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("UPDATE orders SET price=?, updated=? WHERE id=?", (f"{price} zl", datetime.now().strftime("%d.%m.%Y %H:%M"), order_id)); conn.commit(); conn.close()
    await update.message.reply_text(f"💰 {order_id} → {price} zl", reply_markup=get_status_keyboard(order_id))

async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Собираю Excel..."); init_db()
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; c=conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY date DESC"); rows=c.fetchall(); conn.close()
    if not rows: await update.message.reply_text("❌ Не найдено"); return
    try: import openpyxl
    except: await update.message.reply_text("❌ pip install openpyxl"); return
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="RepairFix"
    ws.append(["ID","Телефон","Модель","Цена","Статус","Гарантия","Язык","Дата"])
    for r in rows: ws.append([r["id"],r["phone"],r["model"],r["price"],r["status"],r["warranty_text"],r["lang"],r["updated"]])
    filename=f"RepairFix_{datetime.now().strftime('%d.%m.%Y')}.xlsx"; path=os.path.join(tempfile.gettempdir(), filename); wb.save(path)
    await update.message.reply_document(document=open(path,"rb"), filename=filename)

async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: await update.message.reply_text("Использование: /find 696..."); return
    res=find_orders(" ".join(context.args))
    if not res: await update.message.reply_text("❌ Не найдено"); return
    for o in res[:5]:
        img=create_order_card(o)
        if img and os.path.exists(img): await update.message.reply_photo(photo=open(img,"rb"), caption=f"{o['id']} | {o['status']}", reply_markup=get_status_keyboard(o['id']))
        else: await update.message.reply_text(f"{o['id']} | {o['status']}", reply_markup=get_status_keyboard(o['id']))

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats,today=get_stats(); txt=f"📊 {datetime.now().strftime('%d.%m.%Y')} Сегодня: {today}\n"
    for k,v in stats.items(): txt+=f"{k}: {v}\n"
    txt+=f"Всего: {sum(stats.values())}"; await update.message.reply_text(txt)

async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Проверяю ГОТОВ >2 дней...")
    await daily_reminder_job(context)
    await update.message.reply_text("✅ Готово")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        oid=context.args[0].strip(); order=get_order(oid)
        if order:
            img=create_order_card(order)
            txt=f"📦 {order['id']}\nСтатус: {order.get('status')}\nМодель: {order.get('model')}\nЦена: {order.get('price')}"
            if img and os.path.exists(img): await update.message.reply_photo(photo=open(img,"rb"), caption=txt)
            else: await update.message.reply_text(txt)
            return
    await update.message.reply_text("RepairFix 🔧\n/find /stats /export /remind")

def main():
    init_db()
    app=ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("export", export_cmd))
    app.add_handler(CommandHandler("excel", export_cmd))
    app.add_handler(CommandHandler("remind", remind_cmd))
    app.add_handler(CallbackQueryHandler(status_callback, pattern="^st:"))
    app.add_handler(CallbackQueryHandler(warranty_callback, pattern="^wr:"))
    app.add_handler(CallbackQueryHandler(price_menu_callback, pattern="^price_menu:"))
    app.add_handler(CallbackQueryHandler(price_callback, pattern="^pr:"))
    app.add_handler(CallbackQueryHandler(back_callback, pattern="^back:"))
    app.add_handler(CallbackQueryHandler(pdf_warranty_callback, pattern="^pdf_w:"))
    app.add_handler(CallbackQueryHandler(pdf_receipt_callback, pattern="^pdf_r:"))

    # ✅ ФИКС ИМПОРТОВ
    from handlers.text import text_handler
    from handlers.photo import photo_handler

    app.add_handler(MessageHandler(filters.Chat(chat_id=GROUP_ID) & filters.TEXT & ~filters.COMMAND, admin_price_text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    if app.job_queue:
        app.job_queue.run_daily(daily_reminder_job, time=time(hour=10, minute=0), name="daily_remind")
        print("⏰ Авто-напоминание включено на 10:00 каждый день")
    else:
        print("⚠ JobQueue нет, только /remind")
    print(f"BOT ЗАПУЩЕН, группа {GROUP_ID}")
    app.run_polling()

if __name__=="__main__": main()