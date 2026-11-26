@echo off
REM Arranca el sistema de impresion y abre el navegador.
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
start "" /b cmd /c "timeout /t 3 >nul && start http://127.0.0.1:8000"
python -m config.servir
