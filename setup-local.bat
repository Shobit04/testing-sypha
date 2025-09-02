@echo off
echo 🚀 Setting up Sypha C Local AI for Windows...

REM Check if Ollama is already installed
where ollama >nul 2>nul
if %errorlevel% equ 0 (
    echo ✅ Ollama is already installed
) else (
    echo 📥 Please install Ollama from https://ollama.ai/download
    echo 📥 After installation, add Ollama to your PATH and restart this script
    pause
    exit /b 1
)

REM Start Ollama service
echo 🔄 Starting Ollama service...
start /B ollama serve

REM Wait for Ollama to start
echo ⏳ Waiting for Ollama to start...
timeout /t 5 /nobreak >nul

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>nul
if %errorlevel% equ 0 (
    echo ✅ Ollama service is running
) else (
    echo ❌ Failed to start Ollama service
    echo 💡 Make sure Ollama is in your PATH
    pause
    exit /b 1
)

REM Download required models
echo 📥 Downloading Whisper model...
ollama pull whisper

echo 📥 Downloading Gemma 2B model...
ollama pull gemma2b

REM Verify models are installed
echo 🔍 Verifying models...
ollama list

echo.
echo 🎉 Setup complete! You can now run Sypha C:
echo    npm install
echo    npm start
echo.
echo 💡 Make sure to keep Ollama running: ollama serve
echo 💡 You can stop Ollama by closing the terminal or using Task Manager
pause
