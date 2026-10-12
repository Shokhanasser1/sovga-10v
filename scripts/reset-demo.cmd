@echo off
rem Перед уроком: учебный магазин как новый — история «на сегодня», свежие заказы снова свежие, таймеры не просрочены.
rem Всё, что ученики накликали, пропадёт. Пароли сотрудников прежние (backend\demo-accounts.txt).
rem Сначала закройте окна «Sovga — API» и «Sovga — витрина», если они открыты.
chcp 65001 >nul
setlocal
cd /d "%~dp0..\backend" || exit /b 1
if not exist .venv (
  echo Сначала запустите scripts\setup.cmd
  exit /b 1
)
rem Только учебная база SQLite: настоящий магазин этим скриптом не стереть
findstr /r /i /c:"^DEMO_MODE=true" .env >nul || (
  echo Сброс только для учебного магазина: в backend\.env должно быть DEMO_MODE=true
  exit /b 1
)
findstr /r /c:"^DATABASE_URL=." .env >nul && (
  echo В backend\.env указана своя база DATABASE_URL — этот скрипт сбрасывает только учебную базу db.sqlite3
  exit /b 1
)
for %%F in (db.sqlite3 db.sqlite3-journal db.sqlite3-wal db.sqlite3-shm) do if exist %%F del /q %%F 2>nul
if exist db.sqlite3 (
  echo Не удалось удалить базу: она открыта. Закройте окно «Sovga — API» и запустите сброс снова.
  exit /b 1
)
.venv\Scripts\python.exe manage.py migrate -v 0 || exit /b 1
.venv\Scripts\python.exe manage.py seed_demo || exit /b 1

echo.
echo Готово: учебный магазин как новый. Запуск — scripts\start.cmd
