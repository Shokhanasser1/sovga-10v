@echo off
rem Фоновые задачи (прайсы, курс ЦБ, цены, просрочки, уведомления). Запускать каждые 15 минут:
rem   schtasks /create /tn "Sovga run_jobs" /sc minute /mo 15 /tr "\"%~f0\""
chcp 65001 >nul
cd /d "%~dp0..\backend" && .venv\Scripts\python.exe manage.py run_jobs
