# -*- coding: utf-8 -*-
import os, qrcode
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def get_font():
    try:
        if os.path.exists("C:/Windows/Fonts/arial.ttf"):
            pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
            return 'Arial', 'Arial-Bold'
    except: pass
    return 'Helvetica', 'Helvetica-Bold'

TRANSLATIONS = {
    'pl': {
        'title': 'RepairFix - Serwis Telefonow',
        'addr': 'Swiebodzice, ul. Kolejowa 12 | tel. +48 696 175 928 | Diagnostyka 0 zl',
        'gwar': 'GWARANCJA',
        'karta': 'Karta Gwarancyjna',
        'data_przy': 'Data przyjecia:',
        'data_wyd': 'Data wydania:',
        'model': 'Model:',
        'usterka': 'Usterka:',
        'cena': 'Cena:',
        'klient': 'Klient:',
        'status': 'Status:',
        'gwarancja': 'Gwarancja:',
        'warunki': 'Warunki gwarancji:',
        'c1': '1. Gwarancja obejmuje tylko wykonana usluge / wymieniona czesc.',
        'c2': '2. Nie obejmuje uszkodzen mechanicznych, zalania, ingerencji osob trzecich.',
        'c3': '3. Traci waznosc w przypadku zdjecia plomby / naklejki.',
        'c4': '4. Reklamacje rozpatrywane w terminie 14 dni.',
        'c5': '5. Paragon + karta wymagane do reklamacji.',
        'c6': '6. Zrob kopie danych! Serwis nie odpowiada za dane.',
        'scan': 'Zeskanuj aby sprawdzic status online',
        'pod_kl': 'Podpis klienta',
        'pod_ser': 'Podpis serwisu',
        'gen': 'Wygenerowano',
    },
    'ru': {
        'title': 'RepairFix - Ремонт Телефонов',
        'addr': 'Свебодзице, ул. Колейова 12 | тел. +48 696 175 928 | Диагностика 0 zl',
        'gwar': 'ГАРАНТИЯ',
        'karta': 'Гарантийный талон',
        'data_przy': 'Дата приема:',
        'data_wyd': 'Дата выдачи:',
        'model': 'Модель:',
        'usterka': 'Поломка:',
        'cena': 'Цена:',
        'klient': 'Клиент:',
        'status': 'Статус:',
        'gwarancja': 'Гарантия:',
        'warunki': 'Условия гарантии:',
        'c1': '1. Гарантия распространяется только на выполненную услугу / замененную деталь.',
        'c2': '2. Не покрывает механические повреждения, залитие, вмешательство третьих лиц.',
        'c3': '3. Теряет силу при снятии пломбы / наклейки сервиса.',
        'c4': '4. Рекламации рассматриваются в течение 14 дней.',
        'c5': '5. Чек + гарантийный талон обязательны для рекламации.',
        'c6': '6. Сделайте копию данных! Сервис не отвечает за данные.',
        'scan': 'Сканируй чтобы проверить статус онлайн',
        'pod_kl': 'Подпись клиента',
        'pod_ser': 'Подпись сервиса',
        'gen': 'Сгенерировано',
    },
    'uk': {
        'title': 'RepairFix - Ремонт Телефонiв',
        'addr': 'Свебодзiце, вул. Колейова 12 | тел. +48 696 175 928 | Дiагностика 0 zl',
        'gwar': 'ГАРАНТІЯ',
        'karta': 'Гарантійний талон',
        'data_przy': 'Дата прийому:',
        'data_wyd': 'Дата видачі:',
        'model': 'Модель:',
        'usterka': 'Поломка:',
        'cena': 'Ціна:',
        'klient': 'Клієнт:',
        'status': 'Статус:',
        'gwarancja': 'Гарантія:',
        'warunki': 'Умови гарантії:',
        'c1': '1. Гарантія поширюється тільки на виконану послугу / замінену деталь.',
        'c2': '2. Не покриває механічні пошкодження, залиття, втручання третіх осіб.',
        'c3': '3. Втрачає чинність при знятті пломби / наклейки сервісу.',
        'c4': '4. Рекламації розглядаються протягом 14 днів.',
        'c5': '5. Чек + гарантійний талон обовязкові для рекламації.',
        'c6': '6. Зробіть копію даних! Сервіс не відповідає за дані.',
        'scan': 'Скануй щоб перевірити статус онлайн',
        'pod_kl': 'Підпис клієнта',
        'pod_ser': 'Підпис сервісу',
        'gen': 'Згенеровано',
    }
}

def detect_lang(text):
    if not text: return 'pl'
    text = text.lower()
    if any(ch in text for ch in ['і', 'ї', 'є', 'ґ']):
        return 'uk'
    if any('\u0400' <= c <= '\u04FF' for c in text):
        return 'ru'
    return 'pl'

def create_warranty_pdf(order, bot_username="repairfix_help_bot", lang=None):
    if not lang:
        lang = detect_lang(f"{order.get('issue','')} {order.get('model','')}")
    if lang not in TRANSLATIONS: lang = 'pl'
    t = TRANSLATIONS[lang]

    font_reg, font_bold = get_font()
    filename = f"WARRANTY_{order['id']}_{lang}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    W, H = A4

    BLACK = HexColor("#111111"); GRAY = HexColor("#777777"); GREEN = HexColor("#00A86B"); LIGHT_BG = HexColor("#F5F5F5")

    c.setFillColor(BLACK); c.rect(0, H-110, W, 110, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont(font_bold, 20); c.drawString(20, H-50, t['title'])
    c.setFont(font_reg, 9); c.drawString(20, H-70, t['addr'])
    c.setFont(font_bold, 14); c.drawRightString(W-20, H-50, t['gwar'])

    y = H - 140
    c.setFillColor(BLACK); c.setFont(font_bold, 16); c.drawString(20, y, f"{t['karta']} #{order['id']}"); y-=20; c.line(20, y, W-20, y); y-=20
    c.setFillColor(LIGHT_BG); c.roundRect(20, y-90, W-40, 90, 4, fill=1, stroke=0)
    c.setFillColor(BLACK)
    data = [(t['data_przy'], order.get('date','')), (t['data_wyd'], order.get('updated','')), (t['model'], order.get('model','')), (t['usterka'], order.get('issue','')), (t['cena'], order.get('price','')), (t['klient'], f"{order.get('phone','')} {order.get('username','')}")]
    ty = y-12
    for label, val in data:
        c.setFont(font_reg, 9); c.setFillColor(GRAY); c.drawString(25, ty, label)
        c.setFont(font_bold, 10); c.setFillColor(BLACK); c.drawString(130, ty, str(val)[:60]); ty-=13
    y-=110
    c.setFont(font_bold, 12); c.setFillColor(GREEN)
    status_line = f"{t['status']} {order.get('status','')}"
    if order.get('warranty_text'): status_line += f" | {t['gwarancja']} {order.get('warranty_text')}"
    c.drawString(20, y, status_line); y-=25
    c.setFillColor(BLACK); c.setFont(font_bold, 11); c.drawString(20, y, t['warunki']); y-=15
    c.setFont(font_reg, 8.5)
    for key in ['c1','c2','c3','c4','c5','c6']:
        c.drawString(20, y, t[key]); y-=11

    link = f"https://t.me/{bot_username}?start={order['id']}"
    qr = qrcode.QRCode(box_size=10, border=1); qr.add_data(link); qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white"); qr_path = f"qr_{order['id']}.png"; qr_img.save(qr_path)
    c.drawImage(qr_path, W-140, y-60, width=100, height=100)
    c.setFont(font_reg, 7); c.setFillColor(GRAY); c.drawString(W-140, y-70, t['scan']); c.setFont(font_bold, 7); c.drawString(W-140, y-80, link)
    y=100; c.setStrokeColor(BLACK); c.line(20, y, 200, y); c.line(W-200, y, W-20, y)
    c.setFont(font_reg, 9); c.setFillColor(BLACK); c.drawString(25, y-15, t['pod_kl']); c.drawRightString(W-25, y-15, t['pod_ser'])
    c.setFont(font_reg, 6); c.setFillColor(GRAY); c.drawCentredString(W/2, 25, f"{t['gen']} {datetime.now().strftime('%d.%m.%Y %H:%M')} | RepairFix Swiebodzice | {order['id']} | {lang.upper()}")
    c.save()
    if os.path.exists(qr_path): os.remove(qr_path)
    return filename

def create_receipt_pdf(order, lang=None):
    if not lang:
        lang = detect_lang(f"{order.get('issue','')} {order.get('model','')}")
    if lang not in TRANSLATIONS: lang = 'pl'
    t = TRANSLATIONS[lang]
    font_reg, font_bold = get_font()
    filename = f"RECEIPT_{order['id']}_{lang}.pdf"
    c = canvas.Canvas(filename, pagesize=A4); W, H = A4
    c.setFont(font_bold, 16); c.drawString(20, H-80, f"POTWIERDZENIE / {t['gwar']} / ЧЕК")
    c.setFont(font_reg, 9); c.drawString(20, H-100, t['addr'])
    y=H-160
    c.setFont(font_reg, 11); c.drawString(20, y, f"Nr: {order['id']}"); y-=20
    c.drawString(20, y, f"Data: {order.get('updated', order.get('date',''))}"); y-=20
    c.drawString(20, y, f"{t['klient']} {order.get('phone','')} {order.get('username','')}"); y-=40
    c.setFont(font_bold, 11); c.drawString(20, y, "Lp"); c.drawString(50, y, f"{t['model']} / {t['usterka']}"); c.drawRightString(W-20, y, t['cena']); y-=10; c.line(20,y,W-20,y); y-=20
    c.setFont(font_reg, 11); c.drawString(20, y, "1."); c.drawString(50, y, f"{order.get('model','')} - {order.get('issue','')[:40]}"); c.drawRightString(W-20, y, order.get('price','0 zl')); y-=40; c.line(20,y,W-20,y); y-=30
    c.setFont(font_bold, 13); c.drawRightString(W-20, y, f"RAZEM / TOTAL: {order.get('price','0 zl')}")
    c.save(); return filename