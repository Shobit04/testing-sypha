
# Sypha C - Hybrid AI Assistant

**Sypha C** is a **desktop AI assistant** that combines **Hugging Face Whisper** for high-quality speech-to-text with **local Ollama Gemma 2B** for text generation. This hybrid approach ensures professional-grade transcription while keeping AI responses private and local.

---

## Features

- **Speech-to-Text:** Accurate audio transcription via Hugging Face Whisper (`openai/whisper-medium`)
- **Local AI Responses:** Gemma 2B runs locally for text generation
- **Cross-Platform:** Supports Windows, macOS, and Linux
- **Privacy-Focused:** Only audio is sent to Hugging Face; responses stay local
- **Hybrid Operation:** Combines cloud Whisper + local LLM for optimal performance
- **Real-Time:** Live audio capture and response generation
- **Customizable:** Profiles for different use cases (interviews, sales, meetings, etc.)

---

## Prerequisites

### 1. Hugging Face Access Token
- Required for Whisper transcription
- Obtain your token: [Hugging Face Settings](https://huggingface.co/settings/tokens)
- Example `.env` variable:  
  ```bash
  HUGGING_FACE_ACCESS_TOKEN=your_access_token_here
  ```

### 2. Ollama with Gemma 2B
- Install Ollama locally:

**macOS/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**  
Download from [Ollama.ai](https://ollama.ai/download)

- Pull the Gemma 2B model:
```bash
# Start Ollama service
ollama serve

# Pull Gemma 2B model
ollama pull gemma2b

# Verify installation
ollama list
```

---

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Shobit04/testing-sypha.git
cd sypha_c
```

2. **Create `.env` file** with your Hugging Face token:
```bash
echo "HUGGING_FACE_ACCESS_TOKEN=your_access_token_here" > .env
echo "WHISPER_MODEL=openai/whisper-medium" >> .env
echo "GEMMA_MODEL=gemma2b" >> .env
```

3. **Install dependencies:**
```bash
npm install
```

4. **Start the application:**
```bash
npm start
```

---

## Usage

1. Launch the app and ensure your Hugging Face token is configured.
2. Ensure Ollama is running with the Gemma 2B model.
3. Select a profile (e.g., interview, sales, meeting).
4. Start the session and begin speaking.
5. The app will:
   - Capture your audio using Hugging Face Whisper
   - Transcribe speech to text
   - Generate AI responses using local Gemma 2B
   - Display responses on screen

