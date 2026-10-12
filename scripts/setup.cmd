@echo off
rem Первая установка на Windows. Нужны Python 3.12+ (python.org, галочка "Add to PATH") и Node.js 20+ (nodejs.org).
chcp 65001 >nul
setlocal
set ROOT=%~dp0..

cd /d "%ROOT%\backend" || exit /b 1
if not exist .venv (
  python -m venv .venv || (echo Не найден Python. Установите Python 3.12+ с python.org & exit /b 1)
)
.venv\Scripts\python.exe -m pip install -r requirements.txt || exit /b 1
if not exist .env (
  rem .env из образца, со своим случайным секретным ключом
  .venv\Scripts\python.exe -c "import pathlib, secrets; t = pathlib.Path('.env.example').read_text(encoding='utf-8'); pathlib.Path('.env').write_text(t.replace('SECRET_KEY=change-me', 'SECRET_KEY=' + secrets.token_urlsafe(50)), encoding='utf-8')" || exit /b 1
)
.venv\Scripts\python.exe manage.py migrate || exit /b 1
.venv\Scripts\python.exe manage.py seed_demo || exit /b 1

cd /d "%ROOT%\frontend" || exit /b 1
if not exist .env.local copy .env.example .env.local >nul
call npm install || exit /b 1
call npm run build || exit /b 1

echo.
echo Готово. Логины и пароли сотрудников — выше и в файле backend\demo-accounts.txt
echo   Запуск:        scripts\start.cmd
echo   Перед уроком:  scripts\reset-demo.cmd — магазин как новый
echo   Настоящий магазин (DEMO_MODE=false в backend\.env): администратор —
echo   cd backend  и  .venv\Scripts\python.exe manage.py createsuperuser
