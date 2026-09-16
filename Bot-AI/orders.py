import json, os, random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode

DB_FILE = "orders.json"

STATUSES = {
    "ОФОРМЛЕН": {"text": "🟡 ЗАКАЗ ОФОРМЛЕН", "color": "#FFA500", "desc": "Ожидаем устройство"},
    "ПРИНЯТ": {"text": "🔵 ПРИНЯТ В СЕРВИС", "color": "#0088FF", "desc": "Устройство у нас"},
    "В РАБОТЕ": {"text": "🟠 В РАБОТЕ", "color": "#FF6600", "desc": "Мастер ремонтирует"},
    "ГОТОВ": {"text": "🟢 ГОТОВ", "color": "#00AA55", "desc": "Можно забирать"},
    "ВЫДАН": {"text": "⚫ ВЫДАН", "color": "#111111", "desc": "Заказ закрыт"},
}

def generate_order_id():
    return f"RF-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

def save_order(order_data):
    orders = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f)
        except: orders = []
    orders.append(order_data)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    return order_data

def update_order_status(order_id, new_status):
    if not os.path.exists(DB_FILE):
        return None
    with open(DB_FILE, "r", encoding="utf-8") as f:
        orders = json.load(f)
    for o in orders:
        if o['id'] == order_id:
            o['status'] = new_status
            o['updated'] = datetime.now().strftime("%d.%m.%Y %H:%M")
            break
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    return o

def get_order(order_id):
    if not os.path.exists(DB_FILE): return None
    with open(DB_FILE, "r", encoding="utf-8") as f:
        orders = json.load(f)
    for o in orders:
        if o['id'] == order_id:
            return o
    return None

def create_order_card(order):
    W, H = 1080, 1350
    bg = Image.new("RGB", (W, H), "#0F0F0F")
    draw = ImageDraw.Draw(bg)
    for y in range(H):
        draw.line([(0, y), (W, y)], fill=(15, 15, 30 + int(y*0.12)))

    card_x, card_y, card_w, card_h = 60, 120, 960, 1100
    shadow = Image.new("RGBA", (W, H), (0,0,0,0))
    ImageDraw.Draw(shadow).rounded_rectangle([card_x+10, card_y+20, card_x+card_w+10, card_y+card_h+20], radius=40, fill=(0,0,0,90))
    bg = Image.alpha_composite(bg.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(bg)
    draw.rounded_rectangle([card_x, card_y, card_x+card_w, card_y+card_h], radius=36, fill="#FFFFFF")
    draw.rounded_rectangle([card_x, card_y, card_x+card_w, card_y+140], radius=36, fill="#111111")
    draw.rectangle([card_x, card_y+100, card_x+card_w, card_y+140], fill="#111111")

    try:
        fb = ImageFont.truetype("arialbd.ttf", 40)
        fr = ImageFont.truetype("arial.ttf", 26)
        fs = ImageFont.truetype("arial.ttf", 20)
        fn = ImageFont.truetype("arialbd.ttf", 54)
    except:
        fb = fr = fs = fn = ImageFont.load_default()

    status_info = STATUSES.get(order.get('status','ОФОРМЛЕН'), STATUSES['ОФОРМЛЕН'])

    draw.text((card_x+40, card_y+30), "RepairFix", font=fb, fill="white")
    draw.text((card_x+40, card_y+80), "Swiebodzice • Kolejowa 12", font=fs, fill="#AAAAAA")
    draw.text((card_x+600, card_y+30), f"# {order['id']}", font=fb, fill="#00FF88")

    draw.text((card_x+40, card_y+170), order['id'], font=fn, fill="#111111")
    draw.text((card_x+40, card_y+235), f"{order['model']} • {order['service']}", font=fb, fill="#111111")
    draw.line([(card_x+40, card_y+285), (card_x+card_w-40, card_y+285)], fill="#EEEEEE", width=2)

    y = card_y+320
    rows = [
        ("Клиент:", order['phone']),
        ("Модель:", order['model']),
        ("Поломка:", order['issue'][:36]),
        ("Цена:", order['price']),
        ("Дата:", order['date']),
        ("Статус:", status_info['text']),
        ("", status_info['desc']),
    ]
    for k,v in rows:
        if k:
            draw.text((card_x+40, y), k, font=fs, fill="#888888")
            col = status_info['color'] if "Статус" in k else "#111111"
            draw.text((card_x+200, y), v, font=fr, fill=col)
        else:
            draw.text((card_x+200, y), v, font=fs, fill="#888888")
        y+=50

    qr = qrcode.QRCode(box_size=8, border=1)
    qr.add_data(f"{order['id']}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((180,180))
    bg.paste(qr_img, (card_x+card_w-230, card_y+card_h-230))

    path = f"{order['id']}.png"
    bg.save(path)
    return path