@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Информационная система кинотеатра

echo ==============================================
echo      Информационная система кинотеатра
echo ==============================================
echo.

rem Ищем установленный Python.
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON=python"
    ) else (
        echo ОШИБКА: Python не найден.
        echo.
        echo Установите Python с сайта:
        echo https://www.python.org/downloads/windows/
        echo При установке обязательно включите Add Python to PATH.
        echo Затем снова запустите этот файл.
        echo.
        pause
        exit /b 1
    )
)

rem Виртуальное окружение создаётся только один раз.
if not exist ".venv\Scripts\python.exe" (
    echo Первый запуск: создаётся виртуальное окружение...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :error

    echo Устанавливаются зависимости...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

rem Проверяем зависимости на случай изменения requirements.txt.
".venv\Scripts\python.exe" -c "import flask, waitress" >nul 2>nul
if errorlevel 1 (
    echo Обновляются зависимости...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

echo.
echo Сайт запускается: http://127.0.0.1:5000
echo Для остановки сайта закройте это окно или нажмите Ctrl+C.
echo.

rem Браузер откроется после запуска сервера.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:5000'"

".venv\Scripts\python.exe" app.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Не удалось запустить сайт. Текст ошибки расположен выше.
echo Убедитесь, что есть интернет и Python установлен с поддержкой pip и venv.
echo.
pause
exit /b 1
