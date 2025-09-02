#!/bin/bash

# Setup script for Sypha C Local AI
# This script will install Ollama and download the required models

echo "🚀 Setting up Sypha C Local AI..."

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

# Download required models
echo "📥 Downloading Whisper model..."
ollama pull whisper

echo "📥 Downloading Gemma 2B model..."
ollama pull gemma2b

# Verify models are installed
echo "🔍 Verifying models..."
ollama list

echo ""
echo "🎉 Setup complete! You can now run Sypha C:"
echo "   npm install"
echo "   npm start"
echo ""
echo "💡 Make sure to keep Ollama running: ollama serve"
echo "💡 You can stop Ollama with: pkill ollama"
