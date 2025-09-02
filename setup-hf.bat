@echo off
echo 🚀 Setting up Sypha C - Hugging Face Whisper + Ollama for Windows...

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

REM Download required model
echo 📥 Downloading Gemma 2B model...
ollama pull gemma2b

REM Verify model is installed
echo 🔍 Verifying model...
ollama list

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo.
    echo 📝 Creating .env file...
    echo HUGGING_FACE_ACCESS_TOKEN=your_access_token_here > .env
    echo WHISPER_MODEL=openai/whisper-medium >> .env
    echo GEMMA_MODEL=gemma2b >> .env
    echo ✅ .env file created
    echo ⚠️  Please edit .env and add your Hugging Face access token
) else (
    echo ✅ .env file already exists
)

echo.
echo 🎉 Setup complete! You can now run Sypha C:
echo    npm install
echo    npm start
echo.
echo 💡 Make sure to:
echo    1. Edit .env file with your Hugging Face access token
echo    2. Keep Ollama running: ollama serve
echo    3. Get your token from: https://huggingface.co/settings/tokens
echo.
echo 💡 You can stop Ollama by closing the terminal or using Task Manager
pause
