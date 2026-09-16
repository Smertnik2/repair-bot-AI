# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "repairfix.db"

REMIND_TEXT = {
    'pl': "Cześć! 📱 Twój telefon {model} ({id}) jest GOTOWY do odbioru od {date} w RepairFix, ul. Kolejowa 12.\nCzekamy na Ciebie 10:00-18:00. Daj znać kiedy będziesz!",
    'ru': "Привет! 📱 Твой телефон {model} ({id}) ГОТОВ к выдаче с {date} в RepairFix, ул. Колейова 12.\nЖдем тебя с 10:00-18:00. Напиши когда будешь!",
    'uk': "Привіт! 📱 Твій телефон {model} ({id}) ГОТОВИЙ до видачі з {date} в RepairFix, вул. Колейова 12.\nЧекаємо тебе з 10:00-18:00. Напиши коли будеш!"
}

def get_ready_orders(days=2):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try: c.execute("ALTER TABLE orders ADD COLUMN reminded TEXT")
    except: pass
    c.execute("SELECT * FROM orders WHERE status='ГОТОВ'")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    res = []
    now = datetime.now()
    for o in rows:
        try:
            upd = datetime.strptime(o.get('updated') or o.get('date'), "%d.%m.%Y %H:%M")
            if (now - upd).days >= days:
                # не спамить каждый день - только если не напоминали сегодня
                if o.get('reminded')!= now.strftime("%d.%m.%Y"):
                    res.append(o)
        except: continue
    return res

def mark_reminded(order_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE orders SET reminded=? WHERE id=?", (datetime.now().strftime("%d.%m.%Y"), order_id))
    conn.commit(); conn.close()

async def daily_reminder_job(context):
    from config import ADMIN_CHAT_ID as GROUP_ID
    orders = get_ready_orders(days=2)
    if not orders:
        return
    for o in orders:
        lang = o.get('lang','pl')
        if lang not in REMIND_TEXT: lang='pl'
        text = REMIND_TEXT[lang].format(model=o.get('model',''), id=o['id'], date=o.get('updated',''))
        try:
            if o.get('uid'):
                await context.bot.send_message(chat_id=o['uid'], text=text)
            # в группу для тебя
            await context.bot.send_message(chat_id=GROUP_ID, text=f"🔔 Напомнил {o['id']} | {o.get('phone')} | {o.get('model')} - готов с {o.get('updated')}")
            mark_reminded(o['id'])
        except Exception as e:
            print(f"remind error {o['id']} {e}")