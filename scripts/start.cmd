@echo off
rem Запуск на Windows: каждая часть — в своём окне. Закрыть окно = остановить эту часть.
chcp 65001 >nul
set ROOT=%~dp0..

start "Sovga — API (Django)" /d "%ROOT%\backend" cmd /k ".venv\Scripts\python.exe manage.py runserver"
start "Sovga — витрина (Next.js)" /d "%ROOT%\frontend" cmd /k "npm start"
rem Бот — только если в backend\.env указан токен
findstr /r /c:"^TELEGRAM_BOT_TOKEN=." "%ROOT%\backend\.env" >nul && start "Sovga — Telegram-бот" /d "%ROOT%\backend" cmd /k ".venv\Scripts\python.exe manage.py run_bot"

echo Витрина:  http://localhost:3000
echo Админка:  http://localhost:8000/admin
echo Код входа без настроенных SMS/Telegram пишется в окне "Sovga — API".
