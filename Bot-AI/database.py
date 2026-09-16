import sqlite3
import os
import json
from datetime import datetime
from config import ADMIN_CHAT_ID as GROUP_ID, ADDRESS

DB_PATH = "repairfix.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        uid INTEGER,
        phone TEXT,
        username TEXT,
        model TEXT,
        issue TEXT,
        price TEXT,
        date TEXT,
        updated TEXT,
        status TEXT,
        warranty_months INTEGER,
        warranty_from TEXT,
        warranty_to TEXT,
        warranty_text TEXT,
        photo_path TEXT
    )''')
    conn.commit()
    # Миграция из старого json если есть
    if os.path.exists("orders.json") and os.path.getsize(DB_PATH) < 1000:
        try:
            with open("orders.json","r",encoding="utf-8") as f:
                data=json.load(f)
                for o in data:
                    c.execute("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (o.get('id'),o.get('uid'),o.get('phone'),o.get('username'),o.get('model'),o.get('issue'),o.get('price'),o.get('date'),o.get('updated',o.get('date')),o.get('status','ОФОРМЛЕН'),o.get('warranty_months'),o.get('warranty_from'),o.get('warranty_to'),o.get('warranty_text'),None))
            conn.commit()
            print(f"✅ Мигрировано {len(data)} заказов из json")
        except: pass
    conn.close()

def save_order(order):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (order['id'],order.get('uid'),order.get('phone'),order.get('username'),order.get('model'),order.get('issue'),order.get('price'),order.get('date'),order.get('updated',order.get('date')),order.get('status','ОФОРМЛЕН'),order.get('warranty_months'),order.get('warranty_from'),order.get('warranty_to'),order.get('warranty_text'),order.get('photo_path')))
    conn.commit(); conn.close()

def get_order(order_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    row=c.fetchone(); conn.close()
    return dict(row) if row else None

def update_order(order_id, **kwargs):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    sets = ", ".join([f"{k}=?" for k in kwargs.keys()])
    c.execute(f"UPDATE orders SET {sets} WHERE id=?", (*kwargs.values(), order_id))
    conn.commit(); conn.close()
    return get_order(order_id)

def find_orders(query):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    like=f"%{query}%"
    c.execute("SELECT * FROM orders WHERE phone LIKE? OR id LIKE? OR model LIKE? ORDER BY date DESC LIMIT 10", (like,like,like))
    rows=c.fetchall(); conn.close()
    return [dict(r) for r in rows]

def get_stats():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    stats=dict(c.fetchall())
    c.execute("SELECT COUNT(*) FROM orders WHERE date LIKE?", (f"%{datetime.now().strftime('%d.%m.%Y')}%",))
    today=c.fetchone()[0]
    conn.close()
    return stats, today

async def save_lead(bot, phone, username, msg, title, uid, reply_markup=None):
    try:
        now=datetime.now().strftime("%d.%m.%Y %H:%M")
        order_id=phone.split("|")[1].strip() if "|" in phone else "RF-"
        clean=phone.split("|")[0].strip()
        text=f"🔥 НОВЫЙ ЗАКАЗ {order_id}\n📞 {clean}\n👤 {username}\n🆔 {uid}\n📝 {msg[:100]}\n⏰ {now}\n📍 {ADDRESS}"
        await bot.send_message(chat_id=GROUP_ID, text=text, reply_markup=reply_markup)
        return True
    except Exception as e:
        print(e); return False