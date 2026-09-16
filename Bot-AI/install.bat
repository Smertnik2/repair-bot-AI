@echo off
chcp 65001
python -m pip install --upgrade pip
pip install python-telegram-bot google-genai Pillow qrcode python-dotenv
echo.
echo [OK] Все библиотеки установлены!
pause