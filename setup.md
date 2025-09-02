# Setup Guide for Sypha C - Hugging Face Whisper + Ollama

This guide will help you set up the hybrid AI environment for Sypha C using Hugging Face Whisper for speech-to-text and Ollama Gemma 2B for text generation.

## Prerequisites

### 1. Hugging Face Access Token
- Go to [Hugging Face Settings](https://huggingface.co/settings/tokens)
- Create a new access token with read permissions
- Copy the token (you'll need it for Whisper speech-to-text)

### 2. Ollama Installation

#### macOS/Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows
1. Download from [Ollama.ai](https://ollama.ai/download)
2. Run the installer
3. Add Ollama to your PATH

### 3. Install Required Models

```bash
# Start Ollama service
ollama serve

# In a new terminal, pull the required model
ollama pull gemma2b

# Verify installation
ollama list
```

**Note**: The first time you pull the Gemma 2B model, it may take several minutes depending on your internet connection and system performance.

## Application Setup

1. **Create .env file** in the project root:
```bash
# Create .env file
echo "HUGGING_FACE_ACCESS_TOKEN=your_access_token_here" > .env
echo "WHISPER_MODEL=openai/whisper-medium" >> .env
echo "GEMMA_MODEL=gemma2b" >> .env
```

2. **Install dependencies:**
```bash
npm install
```

3. **Start the app:**
```bash
npm start
```

4. **Ensure Ollama is running:**
```bash
ollama serve
```

5. **Start your session** and begin speaking!

## Verification Steps

### Check Ollama Status
```bash
# Should show available models
ollama list

# Should return model info for Gemma 2B
ollama show gemma2b
```

### Test Ollama API
```bash
curl http://localhost:11434/api/tags
```

### Test Hugging Face Token
```bash
# Test if your token works
curl -H "Authorization: Bearer YOUR_TOKEN" https://huggingface.co/api/models/openai/whisper-medium
```

## How It Works

1. **Audio Capture** → System audio captured in real-time
2. **Hugging Face Whisper** → Audio processed by Hugging Face Whisper API
3. **Local AI Generation** → Transcribed text sent to local Ollama Gemma 2B
4. **Response Display** → AI response shown on screen
5. **Local Storage** → Conversation history saved locally

## Troubleshooting

### Hugging Face Issues
- **Invalid token**: Verify your access token in .env file
- **Rate limiting**: Hugging Face has API rate limits for free accounts
- **Model not found**: Ensure the model name is correct in .env

### Ollama Issues
- **Service not running**: `ollama serve`
- **Model not found**: `ollama pull gemma2b`
- **Port conflicts**: Check if port 11434 is available
- **Out of memory**: Close other applications, reduce model size

### Audio Issues
- **No audio capture**: Check microphone permissions
- **System audio not working**: Ensure audio drivers are up to date
- **Whisper errors**: Verify Hugging Face token and internet connection

### Performance Issues
- **Slow responses**: Close other applications using GPU/CPU
- **High memory usage**: Reduce screenshot interval in settings
- **Audio lag**: Lower audio quality settings
- **Model loading**: First run may be slow as models load into memory

## Configuration

### Environment Variables (.env file)
```bash
HUGGING_FACE_ACCESS_TOKEN=your_token_here
WHISPER_MODEL=openai/whisper-medium
GEMMA_MODEL=gemma2b
```

### Audio Settings
- **Sample Rate**: 24kHz (optimal for Whisper)
- **Chunk Duration**: 0.1 seconds
- **Audio Mode**: Speaker, microphone, or both

### AI Settings
- **Whisper Model**: Hugging Face Whisper Medium (configurable)
- **Text Model**: Local Ollama Gemma 2B (configurable)
- **Temperature**: 0.7 (balanced)
- **Max Tokens**: 2048

### Model Options
You can use different models:
```bash
# Alternative Whisper models on Hugging Face
# Update WHISPER_MODEL in .env:
WHISPER_MODEL=openai/whisper-large-v3
WHISPER_MODEL=openai/whisper-small
WHISPER_MODEL=openai/whisper-base

# Alternative text models in Ollama
ollama pull llama2
ollama pull codellama
ollama pull mistral
```

## Support

If you encounter issues:
1. Check this setup guide
2. Verify your Hugging Face token
3. Review Ollama documentation
4. Check system resources (RAM, GPU)
5. Open an issue on GitHub

## Next Steps

Once everything is working:
1. Customize your profile settings
2. Adjust audio capture preferences
3. Explore different use cases
4. Try different Whisper models
5. Fine-tune AI response parameters

## Benefits of This Setup

- **High-Quality Whisper**: Uses the official OpenAI Whisper model via Hugging Face
- **Local AI Generation**: Gemma 2B runs locally for privacy
- **Hybrid Approach**: Best of both worlds - cloud Whisper + local LLM
- **Cost Effective**: Only pay for Whisper API calls, not for text generation
- **Privacy**: AI responses generated locally, only audio sent to Hugging Face
