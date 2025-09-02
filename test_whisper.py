import whisper
import requests
import json
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import os

def ask_question_via_voice():
    """Complete workflow: record -> transcribe -> ask Gemma"""
    
    # Configuration
    duration = 5  # seconds
    fs = 16000    # sample rate
    
    # Language selection with validation loop
    while True:
        lang_choice = input("Language (en/hi): ").strip().lower()
        if lang_choice in ["en", "hi"]:
            break
        print("❌ Please enter 'en' for English or 'hi' for Hindi")
    
    lang_name = "English" if lang_choice == "en" else "Hindi"
    print(f"🎤 Speak your question in {lang_name} now! Recording for 5 seconds...")
    
    # Record audio
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    print("✅ Recording completed!")
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmpfile:
        write(tmpfile.name, fs, audio)
        temp_path = tmpfile.name
    
    try:
        # Transcribe
        print(f"🔄 Transcribing as {lang_name}...")
        model = whisper.load_model("medium")
        result = model.transcribe(temp_path, language=lang_choice)
        question = result["text"].strip()

        print(f"📝 You asked: '{question}'")

        if len(question) < 3:
            print("⚠️  Question too short or unclear.")
            return

        # Ask Gemma
        print("🤖 Gemma is thinking...")
        ollama_url = "http://localhost:11434/api/generate"
        payload = {
            "model": "gemma:2b",
            "prompt": f"Answer this question concisely: {question}",
            "stream": False  
        }

        response = requests.post(ollama_url, json=payload)
        response.raise_for_status()

        result = response.json()
        answer = result.get("response", "No response received")

        print("\n" + "="*50)
        print("🎯 ANSWER:")
        print("="*50)
        print(answer)
        print("="*50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass

if __name__ == "__main__":
    ask_question_via_voice()