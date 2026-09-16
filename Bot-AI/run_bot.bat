@echo off
chcp 65001 > nul
title RepairFix Telegram Bot Launcher
color 0A

echo ====================================================
echo 🧹 Очистка старых фоновых процессов Python...
echo ====================================================
taskkill /F /IM python.exe 2>nul

echo.
echo ====================================================
echo 🚀 Запуск бота RepairFix...
echo ====================================================
python main_bot.py

pause