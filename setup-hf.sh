#!/bin/bash

# Setup script for Sypha C - Hugging Face Whisper + Ollama
# This script will install Ollama and help configure Hugging Face

echo "🚀 Setting up Sypha C - Hugging Face Whisper + Ollama..."

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is already installed"
else
    echo "📥 Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    
    # Add Ollama to PATH for current session
    export PATH=$PATH:$HOME/.local/bin
    
    echo "✅ Ollama installed successfully"
fi

# Start Ollama service
echo "🔄 Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to start
echo "⏳ Waiting for Ollama to start..."
sleep 5

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama service is running"
else
    echo "❌ Failed to start Ollama service"
    exit 1
fi

# Download required model
echo "📥 Downloading Gemma 2B model..."
ollama pull gemma2b

# Verify model is installed
echo "🔍 Verifying model..."
ollama list

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file..."
    echo "HUGGING_FACE_ACCESS_TOKEN=your_access_token_here" > .env
    echo "WHISPER_MODEL=openai/whisper-medium" >> .env
    echo "GEMMA_MODEL=gemma2b" >> .env
    echo "✅ .env file created"
    echo "⚠️  Please edit .env and add your Hugging Face access token"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup complete! You can now run Sypha C:"
echo "   npm install"
echo "   npm start"
echo ""
echo "💡 Make sure to:"
echo "   1. Edit .env file with your Hugging Face access token"
echo "   2. Keep Ollama running: ollama serve"
echo "   3. Get your token from: https://huggingface.co/settings/tokens"
echo ""
echo "💡 You can stop Ollama with: pkill ollama"
