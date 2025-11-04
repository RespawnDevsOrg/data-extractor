@echo off
REM Startup script for Voter List OCR Web Application (Windows)

cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the Flask application
python app.py

pause

