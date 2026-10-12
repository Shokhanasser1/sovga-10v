@echo off
rem Запуск на Windows: каждая часть — в своём окне. Закрыть окно = остановить эту часть.
chcp 65001 >nul
setlocal
set ROOT=%~dp0..

start "Sovga — API (Django)" /d "%ROOT%\backend" cmd /k ".venv\Scripts\python.exe manage.py runserver"
start "Sovga — витрина (Next.js)" /d "%ROOT%\frontend" cmd /k "npm start"
rem Бот — только если в backend\.env указан токен
findstr /r /c:"^TELEGRAM_BOT_TOKEN=." "%ROOT%\backend\.env" >nul && start "Sovga — Telegram-бот" /d "%ROOT%\backend" cmd /k ".venv\Scripts\python.exe manage.py run_bot"

echo Запускаем магазин — витрина и админка откроются в браузере сами...
rem Ждём до двух минут: сначала API, потом витрину (она берёт данные из API)
set TRIES=0
:wait
curl -sf -o nul http://127.0.0.1:8000/api/health/ && curl -sf -o nul http://localhost:3000/ru && goto ready
set /a TRIES+=1
if %TRIES% geq 120 goto slow
ping -n 2 127.0.0.1 >nul
goto wait

:ready
start "" http://localhost:3000/ru
start "" http://localhost:8000/admin/
goto info

:slow
echo Магазин не ответил за две минуты — посмотрите сообщения в окнах «Sovga — API» и «Sovga — витрина».

:info
echo.
echo Витрина:  http://localhost:3000
echo Админка:  http://localhost:8000/admin
if exist "%ROOT%\backend\demo-accounts.txt" echo Логины и пароли сотрудников:  backend\demo-accounts.txt
echo Код входа без настроенных SMS/Telegram пишется в окне "Sovga — API".
