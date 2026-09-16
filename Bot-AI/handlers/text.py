# -*- coding: utf-8 -*-
import asyncio
import re
import os
import qrcode
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, MODEL, ADDRESS, BOT_USERNAME
from config import ADMIN_CHAT_ID as GROUP_ID
from prompts import SYSTEM_PROMPT
from keyboards import main_menu
from PIL import Image, ImageDraw, ImageFont

DB_PATH = "repairfix.db"
LOGO_PATH = "logo_rf.png"

def detect_lang(text: str) -> str:
    if not text: return 'pl'
    t = text.lower()
    if any(ch in t for ch in ['і','ї','є','ґ']): return 'uk'
    if any('\u0400' <= c <= '\u04FF' for c in t): return 'ru'
    return 'pl'

LANG_TEXT = {
    'pl': {
        'photo_saved': "📸 Zdjecie zapisane! Teraz napisz model i wyslij numer telefonu.",
        'bad_phone': "❌ Numer nie polski\n✅ Przyklad: 791 123 456",
        'order_done': "✅ Zamowienie *{id}* przyjete!\n📱 {model}\n📞 {phone}\n📍 {addr}",
        'card_client': "KLIENT", 'card_model': "MODEL", 'card_issue': "USTERKA",
        'card_price': "CENA", 'card_date': "DATA", 'card_warr': "GWARANCJA",
        'status_wait': "Oczekujemy na urzadzenie",
        'status_przy': "Przyjety: {d}", 'status_work': "W pracy od {d}",
        'status_got': "Gotowy od {d}", 'status_wyd': "Wydany: {d}",
        'scan': "Zeskanuj aby sprawdzic • t.me/{bot}", 'diag': "Diagnostyka 0 zl",
        'ask_model': "Nie widze modelu 🤔 Napisz model np. *Asus X515* lub wyslij zdjecie naklejki z tylu",
    },
    'ru': {
        'photo_saved': "📸 Фото сохранено! Теперь напиши модель и пришли номер телефона.",
        'bad_phone': "❌ Номер не польский\n✅ Пример: 791 123 456",
        'order_done': "✅ Заказ *{id}* оформлен!\n📱 {model}\n📞 {phone}\n📍 {addr}",
        'card_client': "КЛИЕНТ", 'card_model': "МОДЕЛЬ", 'card_issue': "ПОЛОМКА",
        'card_price': "ЦЕНА", 'card_date': "ДАТА", 'card_warr': "ГАРАНТИЯ",
        'status_wait': "Ожидаем устройство",
        'status_przy': "Принят: {d}", 'status_work': "В работе с {d}",
        'status_got': "Готов с {d}", 'status_wyd': "Выдан: {d}",
        'scan': "Сканируй для проверки • t.me/{bot}", 'diag': "Диагностика 0 zl",
        'ask_model': "Не вижу модель 🤔 Напиши модель, например *Asus X515* или скинь фото наклейки сзади / коробки",
    },
    'uk': {
        'photo_saved': "📸 Фото збережено! Тепер напиши модель і надішли номер телефону.",
        'bad_phone': "❌ Номер не польський\n✅ Приклад: 791 123 456",
        'order_done': "✅ Замовлення *{id}* оформлено!\n📱 {model}\n📞 {phone}\n📍 {addr}",
        'card_client': "КЛІЄНТ", 'card_model': "МОДЕЛЬ", 'card_issue': "ПОЛОМКА",
        'card_price': "ЦІНА", 'card_date': "ДАТА", 'card_warr': "ГАРАНТІЯ",
        'status_wait': "Очікуємо пристрій",
        'status_przy': "Прийнято: {d}", 'status_work': "В роботі з {d}",
        'status_got': "Готовий з {d}", 'status_wyd': "Видано: {d}",
        'scan': "Скануй для перевірки • t.me/{bot}", 'diag': "Діагностика 0 zl",
        'ask_model': "Не бачу модель 🤔 Напиши модель або скинь фото наклейки",
    }
}

def get_status_keyboard(order_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔵 Принят",callback_data=f"st:{order_id}:ПРИНЯТ"),
         InlineKeyboardButton("🟠 В работе",callback_data=f"st:{order_id}:В РАБОТЕ")],
        [InlineKeyboardButton("🟢 Готов",callback_data=f"st:{order_id}:ГОТОВ"),
         InlineKeyboardButton("⚫ Выдан",callback_data=f"st:{order_id}:ВЫДАН")],
        [InlineKeyboardButton("💰 Цена",callback_data=f"price_menu:{order_id}")],
        [InlineKeyboardButton("📄 Гарантия PDF",callback_data=f"pdf_w:{order_id}"),
         InlineKeyboardButton("🧾 Чек PDF",callback_data=f"pdf_r:{order_id}")],
        [InlineKeyboardButton("🛡 1 мес",callback_data=f"wr:{order_id}:1"),
         InlineKeyboardButton("3 мес",callback_data=f"wr:{order_id}:3"),
         InlineKeyboardButton("6 мес",callback_data=f"wr:{order_id}:6"),
         InlineKeyboardButton("12 мес",callback_data=f"wr:{order_id}:12")],
    ])

def save_order_db(order):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY, uid INTEGER, phone TEXT, username TEXT, model TEXT, issue TEXT, price TEXT, date TEXT, updated TEXT, status TEXT, warranty_months INTEGER, warranty_from TEXT, warranty_to TEXT, warranty_text TEXT, photo_path TEXT, lang TEXT, reminded TEXT, reminded_7 TEXT)''')
    for col in ["lang TEXT","reminded TEXT","reminded_7 TEXT"]:
        try: c.execute(f"ALTER TABLE orders ADD COLUMN {col}")
        except: pass
    c.execute("INSERT OR REPLACE INTO orders (id,uid,phone,username,model,issue,price,date,updated,status,warranty_months,warranty_from,warranty_to,warranty_text,photo_path,lang,reminded,reminded_7) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (order['id'],order.get('uid'),order.get('phone'),order.get('username'),order.get('model'),order.get('issue'),order.get('price'),order.get('date'),order.get('updated',order.get('date')),order.get('status','ОФОРМЛЕН'),order.get('warranty_months'),order.get('warranty_from'),order.get('warranty_to'),order.get('warranty_text'),order.get('photo_path'), order.get('lang','ru'), order.get('reminded'), order.get('reminded_7')))
    conn.commit(); conn.close()

async def save_lead(bot, phone_text, username, msg, title, uid, reply_markup=None):
    try:
        text = f"🔥 НОВЫЙ ЗАКАЗ\n📞 {phone_text}\n👤 {username}\n📝 {msg[:100]}\n📍 {ADDRESS}"
        await bot.send_message(chat_id=GROUP_ID, text=text, reply_markup=reply_markup)
    except Exception as e: print(e)

MODEL_FIXED = MODEL.replace("models/", "").strip()
FALLBACK_MODELS = ["models/gemini-2.0-flash","gemini-2.0-flash-lite","gemini-1.5-flash"]
client = genai.Client(api_key=GEMINI_API_KEY)
chats = {}
def get_chat(uid):
    if uid in chats: return chats[uid]
    for m in list(dict.fromkeys([MODEL, MODEL_FIXED] + FALLBACK_MODELS)):
        try:
            chat = client.chats.create(model=m, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.8, max_output_tokens=600))
            chats[uid]=chat; return chat
        except: continue
    raise Exception("No model")

def find_phone_strong(text: str):
    d = re.sub(r'\D','',text)
    if d.startswith('48') and len(d)>=11: d=d[2:]
    if len(d)==9 and d[0] in '5678': return d
    if len(d)==10 and d[0]=='0' and d[1] in '5678': return d[1:]
    m=re.search(r'(?:\+?48)?\s*([5-8]\d{2}\s*\d{3}\s*\d{3})', text)
    if m:
        x=re.sub(r'\D','',m.group(1))
        if len(x)==9: return x
    return None

def looks_like_phone_attempt(t): return len(re.sub(r'\D','',t))>=7
def generate_order_id():
    import random; return f"RF-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

def parse_model_issue(raw: str):
    t = raw.lower()
    model = "Диагностика"
    if any(w in t for w in ["ноут", "laptop", "macbook"]):
        if "asus" in t or "асус" in t: model = "Ноутбук Asus"
        elif "lenovo" in t or "леново" in t: model = "Ноутбук Lenovo"
        elif "hp" in t: model = "Ноутбук HP"
        elif "acer" in t: model = "Ноутбук Acer"
        elif "dell" in t: model = "Ноутбук Dell"
        elif "macbook" in t or "макбук" in t: model = "MacBook"
        else: model = "Ноутбук"
    elif "iphone" in t or "айфон" in t:
        m = re.search(r'iphone\s*(\d+)', t) or re.search(r'(\d+)\s*(pro|promax|max)', t)
        if m: model = f"iPhone {m.group(1)}"
        else: model = "iPhone"
    elif "samsung" in t or "самсунг" in t: model = "Samsung"
    elif "xiaomi" in t or "ксяоми" in t or "redmi" in t: model = "Xiaomi"
    elif "ipad" in t: model = "iPad"

    issue_clean = re.sub(r'\+?48[\s\-]?', ' ', raw)
    issue_clean = re.sub(r'\b\d{9,}\b', ' ', issue_clean)
    issue_clean = re.sub(r'\s+', ' ', issue_clean).strip()

    if "экран" in t or "дисплей" in t or "матриц" in t: issue = "Разбит экран, нужна замена"
    elif "батарея" in t or "аккум" in t: issue = "Замена батареи"
    elif "не вкл" in t or "не включает" in t: issue = "Не включается"
    elif "вода" in t or "залил" in t: issue = "Попала вода"
    elif "заряд" in t: issue = "Не заряжается"
    elif "клав" in t: issue = "Проблема с клавиатурой"
    else: issue = issue_clean[:60] if len(issue_clean)>3 else "Диагностика"

    return model, issue

def _get_font(sz, bold=False):
    candidates = []
    if os.name == 'nt':
        candidates.append("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf")
    candidates += ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except: pass
    return ImageFont.load_default()

def create_order_card(order):
    try:
        lang = order.get('lang') or detect_lang(f"{order.get('issue','')} {order.get('model','')}")
        lt = LANG_TEXT.get(lang, LANG_TEXT['ru'])
        W,H = 1080, 1750
        bg = Image.new("RGB", (W,H), "#0B141A")
        draw = ImageDraw.Draw(bg)
        card_w, card_h = 980, 1550
        card_x = (W-card_w)//2
        card_y = 40
        draw.rounded_rectangle([card_x, card_y, card_x+card_w, card_y+card_h], radius=28, fill=(255,255,255))
        draw.rounded_rectangle([card_x, card_y, card_x+card_w, card_y+110], radius=28, fill=(17,17,17))
        draw.rectangle([card_x, card_y+80, card_x+card_w, card_y+110], fill=(17,17,17))
        try:
            if os.path.exists(LOGO_PATH):
                logo = Image.open(LOGO_PATH).convert("RGBA").resize((76,76), Image.LANCZOS)
                bg.paste(logo, (card_x+22, card_y+17), logo)
                draw.text((card_x+115,card_y+18),"RepairFix AI",font=_get_font(34,True),fill="white")
                draw.text((card_x+115,card_y+60),f"{ADDRESS}",font=_get_font(20),fill="#8A8A8A")
            else:
                draw.text((card_x+30,card_y+18),"RepairFix AI",font=_get_font(38,True),fill="white")
                draw.text((card_x+30,card_y+64),f"{ADDRESS}",font=_get_font(22),fill="#8A8A8A")
        except:
            draw.text((card_x+30,card_y+18),"RepairFix AI",font=_get_font(38,True),fill="white")
        draw.text((card_x+card_w-250,card_y+24),f"# {order['id'][-4:]}",font=_get_font(30,True),fill="#00FF88")
        y=card_y+140
        draw.text((card_x+30,y),order['id'],font=_get_font(52,True),fill="#111111"); y+=70
        draw.text((card_x+30,y),f"{order.get('model','')[:34]}",font=_get_font(28,True),fill="#222222"); y+=50
        draw.line([(card_x+30,y),(card_x+card_w-30,y)],fill="#E8E8E8",width=3); y+=25
        STATUSES={"ОФОРМЛЕН":("#B36B00","#FFF0CC"),"ПРИНЯТ":("#0059B3","#D6E9FF"),"В РАБОТЕ":("#B34D00","#FFE4D1"),"ГОТОВ":("#007A3D","#D6FFE9"),"ВЫДАН":("#111111","#E5E5E5")}
        fg,bgc=STATUSES.get(order.get('status','ОФОРМЛЕН'), STATUSES["ОФОРМЛЕН"])
        def badge(x,y,text,fg,bgc):
            w=len(text)*13+40
            draw.rounded_rectangle([x,y,x+w,y+50],radius=25,fill=bgc)
            draw.text((x+20,y+11),text,font=_get_font(19,True),fill=fg)
            return w
        bw=badge(card_x+30,y,order.get('status','ОФОРМЛЕН'),fg,bgc)
        if order.get('warranty_months'):
            badge(card_x+30+bw+15,y,f"{lt['card_warr']} {order['warranty_months']} МЕС","#5A4BD1","#EDE8FF")
        y+=75
        for label,val in [(lt['card_client'],order.get('phone','')),(lt['card_model'],order.get('model','')),(lt['card_issue'],order.get('issue','')),(lt['card_price'],order.get('price',lt['diag'])),(lt['card_date'],order.get('date',''))]:
            draw.text((card_x+30,y),label,font=_get_font(20),fill="#9A9A9A")
            draw.text((card_x+30,y+24),str(val)[:36],font=_get_font(28,True),fill="#111111"); y+=72
        if order.get('warranty_text'):
            draw.rounded_rectangle([card_x+20,y+5,card_x+card_w-20,y+85],radius=16,fill="#F5F1FF")
            draw.rectangle([card_x+20,y+5,card_x+24,y+85],fill="#6C5CFF")
            draw.text((card_x+40,y+10),lt['card_warr'],font=_get_font(17),fill="#9A9A9A")
            draw.text((card_x+40,y+30),order['warranty_text'][:44],font=_get_font(24,True),fill="#6C5CFF"); y+=100
        status = order.get('status','ОФОРМЛЕН')
        updated = order.get('updated', order.get('date',''))
        status_texts = {"ОФОРМЛЕН": lt['status_wait'],"ПРИНЯТ": lt['status_przy'].format(d=updated),"В РАБОТЕ": lt['status_work'].format(d=updated),"ГОТОВ": lt['status_got'].format(d=updated),"ВЫДАН": lt['status_wyd'].format(d=updated)}
        status_colors = {"ОФОРМЛЕН":"#777777","ПРИНЯТ":"#0059B3","В РАБОТЕ":"#B34D00","ГОТОВ":"#007A3D","ВЫДАН":"#111111"}
        draw.text((card_x+30,y), status_texts.get(status, lt['status_wait']), font=_get_font(22,True), fill=status_colors.get(status,"#555")); y+=40
        if order.get('photo_path') and os.path.exists(order['photo_path']):
            try:
                ph=Image.open(order['photo_path']).convert("RGB").resize((200,200), Image.LANCZOS)
                bg.paste(ph,(card_x+card_w-230,card_y+140))
                draw.rounded_rectangle([card_x+card_w-232,card_y+138,card_x+card_w-28,card_y+342],radius=12,outline="#111",width=2)
            except: pass
        qr_size=320; qr_x=card_x+(card_w-qr_size)//2; qr_y=card_y+card_h-qr_size-60
        draw.rounded_rectangle([qr_x-8,qr_y-8,qr_x+qr_size+8,qr_y+qr_size+8],radius=28,fill="#111111")
        draw.rounded_rectangle([qr_x-2,qr_y-2,qr_x+qr_size+2,qr_y+qr_size+2],radius=22,fill="white")
        qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
        link = f"https://t.me/{BOT_USERNAME}?start={order['id']}"
        qr.add_data(link); qr.make(fit=True)
        qr_img=qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((qr_size,qr_size), Image.NEAREST)
        bg.paste(qr_img,(qr_x,qr_y))
        draw.text((card_x+30,card_y+card_h-35), lt['scan'].format(bot=BOT_USERNAME), font=_get_font(15), fill="#8A8A8A")
        os.makedirs("cards", exist_ok=True)
        path=os.path.join("cards", f"{order['id']}.jpg")
        bg.save(path, "JPEG", quality=95)
        print(f"✅ Карточка {path} lang={lang} + logo")
        return path
    except Exception as e:
        import traceback; traceback.print_exc(); return None

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id < 0: return
    uid=update.effective_chat.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    path = f"device_{uid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    await file.download_to_drive(path)
    context.user_data['last_photo']=path

    # если ждали фото модели для pending заказа
    if context.user_data.get('pending_phone'):
        phone = context.user_data['pending_phone']
        issue = context.user_data.get('pending_issue','Диагностика')
        lang = context.user_data.get('last_lang') or 'ru'
        lt = LANG_TEXT.get(lang, LANG_TEXT['ru'])
        username=f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        order_id=generate_order_id()
        order={
            "id":order_id,"uid":uid,"phone":phone,"username":username,
            "model":"По фото - уточнить",
            "issue":issue[:60],
            "price": LANG_TEXT[lang]['diag'],
            "date":datetime.now().strftime("%d.%m.%Y %H:%M"),
            "updated":datetime.now().strftime("%d.%m.%Y %H:%M"),
            "status":"ОФОРМЛЕН",
            "photo_path":path,
            "lang": lang
        }
        save_order_db(order)
        try:
            from handlers.gsheet import sync_order_to_sheet
            sync_order_to_sheet(order)
        except: pass
        img=create_order_card(order)
        kb=get_status_keyboard(order_id)
        await save_lead(context.bot,f"{phone} | {order_id} | {order['model']} (по фото)",username,issue,f"Заказ {order_id}",uid,reply_markup=kb)
        if img and os.path.exists(img):
            await update.message.reply_photo(photo=open(img,"rb"),caption=lt['order_done'].format(id=order_id, model=order['model'], phone=phone, addr=ADDRESS),parse_mode="Markdown")
        context.user_data.clear()
        return

    lang = detect_lang(update.message.caption or "")
    lt = LANG_TEXT.get(lang, LANG_TEXT['ru'])
    await update.message.reply_text(lt['photo_saved'])

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id < 0: return
    text = update.message.text.strip()
    if text.lower() in ["меню","📋 меню","menu"]:
        await update.message.reply_text("Выбери 👇 / Wybierz 👇", reply_markup=main_menu()); return
    uid = update.effective_chat.id

    if looks_like_phone_attempt(text):
        lang = context.user_data.get('last_lang') or detect_lang(text) or 'ru'
        if lang == 'pl' and any('\u0400' <= c <= '\u04FF' for c in text):
            lang = 'ru'
    else:
        lang = detect_lang(text)
    lt = LANG_TEXT.get(lang, LANG_TEXT['ru'])

    if not looks_like_phone_attempt(text) and len(text)>3:
        context.user_data['last_issue']=text
        context.user_data['last_lang']=lang

    phone = find_phone_strong(text) if looks_like_phone_attempt(text) else None
    if phone:
        username=f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        raw_for_parse = context.user_data.get('last_issue', '') + " " + text
        model_parsed, issue_parsed = parse_model_issue(raw_for_parse)

        # если модель не понятна и нет фото
        is_generic = model_parsed == "Диагностика"
        if is_generic and not context.user_data.get('last_photo'):
            context.user_data['pending_phone'] = phone
            context.user_data['pending_issue'] = issue_parsed
            context.user_data['last_lang'] = lang
            await update.message.reply_text(lt['ask_model'], parse_mode="Markdown")
            return

        use_lang = context.user_data.get('last_lang') or lang or 'ru'
        order_id=generate_order_id()
        order={
            "id":order_id,"uid":uid,"phone":phone,"username":username,
            "model":model_parsed[:40],
            "issue":issue_parsed[:60],
            "price": LANG_TEXT[use_lang]['diag'],
            "date":datetime.now().strftime("%d.%m.%Y %H:%M"),
            "updated":datetime.now().strftime("%d.%m.%Y %H:%M"),
            "status":"ОФОРМЛЕН",
            "photo_path":context.user_data.get('last_photo'),
            "lang": use_lang
        }
        save_order_db(order)
        try:
            from handlers.gsheet import sync_order_to_sheet
            sync_order_to_sheet(order)
        except: pass
        img=create_order_card(order)
        kb=get_status_keyboard(order_id)
        try: await save_lead(context.bot,f"{phone} | {order_id} | {model_parsed} [{use_lang}]",username,issue_parsed,f"Заказ {order_id}",uid,reply_markup=kb)
        except: pass
        if img and os.path.exists(img):
            await update.message.reply_photo(photo=open(img,"rb"),caption=lt['order_done'].format(id=order_id, model=model_parsed, phone=phone, addr=ADDRESS),parse_mode="Markdown")
        else:
            await update.message.reply_text(lt['order_done'].format(id=order_id, model=model_parsed, phone=phone, addr=ADDRESS),parse_mode="Markdown")
        context.user_data['last_photo']=None
        context.user_data['last_issue']=None
        context.user_data.pop('pending_phone',None)
        return

    await context.bot.send_chat_action(uid,"typing")
    try:
        chat=await asyncio.to_thread(get_chat,uid)
        resp=await asyncio.to_thread(chat.send_message,text)
        ans=getattr(resp,'text','') or lt['diag'] + ' 🔧'
        await update.message.reply_text(ans,parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Связь глюкнула 🔧 {ADDRESS} 🙏")