@echo off
REM Voter List OCR - Windows Deployment Script
REM This script helps deploy the application using different methods

setlocal enabledelayedexpansion

echo ==============================================
echo   Voter List OCR - Windows Deployment Script
echo ==============================================

REM Function to check if command exists
where docker >nul 2>&1
set DOCKER_EXISTS=!errorlevel!

where docker-compose >nul 2>&1
set DOCKER_COMPOSE_EXISTS=!errorlevel!

where python >nul 2>&1
set PYTHON_EXISTS=!errorlevel!

where tesseract >nul 2>&1
set TESSERACT_EXISTS=!errorlevel!

where pdftoppm >nul 2>&1
set POPPLER_EXISTS=!errorlevel!

REM Main script logic
if "%1"=="" goto deploy_docker
if "%1"=="docker" goto deploy_docker
if "%1"=="native" goto deploy_native
if "%1"=="help" goto show_usage
if "%1"=="--help" goto show_usage
if "%1"=="-h" goto show_usage

echo ❌ Unknown option: %1
goto show_usage

:deploy_docker
echo 🐳 Deploying with Docker...

if !DOCKER_EXISTS! neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    echo    Visit: https://docs.docker.com/desktop/windows/
    pause
    exit /b 1
)

if !DOCKER_COMPOSE_EXISTS! neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

echo ✓ Docker and Docker Compose found

REM Stop any existing containers
echo 🛑 Stopping any existing containers...
docker-compose down >nul 2>&1

REM Build and start the application
echo 🔨 Building and starting the application...
docker-compose up --build -d

REM Wait for the application to start
echo ⏳ Waiting for application to start...
timeout /t 10 /nobreak >nul

REM Check if the application is running
curl -f http://localhost:8080/api/health >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Application deployed successfully!
    echo 🌐 Access the application at: http://localhost:8080
    echo 📊 View logs with: docker-compose logs -f
    echo 🛑 Stop with: docker-compose down
) else (
    echo ❌ Application failed to start. Check logs with: docker-compose logs
    pause
    exit /b 1
)

echo.
echo Press any key to exit...
pause >nul
goto :eof

:deploy_native
echo No support for native deployment. Contact Omkar Deshpande for this
@REM echo 💻 Deploying natively...

@REM if !PYTHON_EXISTS! neq 0 (
@REM     echo ❌ Python is not installed. Please install Python 3.8 or higher.
@REM     echo    Visit: https://www.python.org/downloads/
@REM     pause
@REM     exit /b 1
@REM )

@REM if !TESSERACT_EXISTS! neq 0 (
@REM     echo ❌ Tesseract OCR is not installed.
@REM     echo    Download from: https://github.com/UB-Mannheim/tesseract/wiki
@REM     echo    Make sure to add it to your PATH
@REM     pause
@REM     exit /b 1
@REM )

@REM if !POPPLER_EXISTS! neq 0 (
@REM     echo ❌ Poppler utilities are not installed.
@REM     echo    Download from: https://github.com/oschwartz10612/poppler-windows/releases
@REM     echo    Make sure to add it to your PATH
@REM     pause
@REM     exit /b 1
@REM )

@REM echo ✓ Python, Tesseract, and Poppler found

@REM REM Install Python dependencies
@REM echo 📦 Installing Python dependencies...
@REM pip install -r requirements.txt

REM Create necessary directories
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs

REM Start the application
echo 🚀 Starting the application...
echo 🌐 Application will be available at: http://localhost:8080
echo 🛑 Press Ctrl+C to stop
python app.py

goto :eof

:show_usage
echo Usage: %0 [docker^|native^|help]
echo.
echo Options:
echo   docker    Deploy using Docker (recommended)
echo   native    Deploy natively with Python
echo   help      Show this help message
echo.
echo Examples:
echo   %0 docker     # Deploy with Docker
echo   %0 native     # Deploy natively
echo.
echo Press any key to exit...
pause >nul
goto :eof