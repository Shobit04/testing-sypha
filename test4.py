import whisper
import requests
import sounddevice as sd
import numpy as np
import queue
import json
import time
import threading
from collections import deque
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import keyboard  # pip install keyboard
import sys
import traceback

# -------------------------------
# CONFIG
# -------------------------------
SAMPLE_RATE = 16000
BLOCKSIZE = 1024
SILENCE_THRESHOLD = 0.02  # Increased for better noise handling
MIN_SPEECH_DURATION = 1.5  # Reduced for faster response
PROCESSING_INTERVAL = 3.0  # Faster processing
HELP_HOTKEY = 'ctrl+h'
MAX_BUFFER_DURATION = 30  # Maximum seconds to keep in buffer

# Global variables
audio_queue = queue.Queue()
recent_speech = deque(maxlen=20)  # Reduced for better performance
is_listening = True
manual_help_requested = False
model = None
gui = None

# -------------------------------
# INITIALIZATION
# -------------------------------
def initialize_whisper():
    global model
    try:
        print("🔄 Loading Whisper model...")
        model = whisper.load_model("tiny")  # Using tiny for faster processing
        print("✅ Whisper model loaded successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to load Whisper model: {e}")
        return False

def test_ollama_connection():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=12)
        if response.status_code == 200:
            models = response.json().get("models", [])
            gemma_available = any("gemma" in model.get("name", "") for model in models)
            if gemma_available:
                print("✅ Ollama connection successful - Gemma model found")
                return True
            else:
                print("⚠️ Ollama connected but Gemma model not found")
                return False
        else:
            print(f"⚠️ Ollama responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        return False

class MeetingAssistantGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Meeting AI Assistant - Gemma Helper")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # Thread-safe update queue
        self.update_queue = queue.Queue()
        
        self.create_widgets()
        self.setup_update_checker()
        
    def create_widgets(self):
        self.selected_language = tk.StringVar(value="en")
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title and status
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(title_frame, text="🎤 Meeting AI Assistant", 
                               font=('Arial', 18, 'bold'))
        title_label.pack()

        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 15))

        self.status_label = ttk.Label(status_frame, text="🔄 Initializing...", 
                                     font=('Arial', 11))
        self.status_label.pack(side=tk.LEFT)

        # Control buttons and language dropdown
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.RIGHT)

        # Language dropdown (only en and hi)
        lang_label = ttk.Label(button_frame, text="Language:")
        lang_label.pack(side=tk.LEFT, padx=(0,2))
        lang_dropdown = ttk.Combobox(button_frame, textvariable=self.selected_language, state="readonly", width=6)
        lang_dropdown['values'] = ("en", "hi")
        lang_dropdown.pack(side=tk.LEFT, padx=2)

        self.help_button = ttk.Button(button_frame, text="🆘 Need Help (Ctrl+H)", 
                         command=self.request_help, state='disabled')
        self.help_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(button_frame, text="🧹 Clear", 
                          command=self.clear_conversation)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.test_button = ttk.Button(button_frame, text="🔧 Test Audio", 
                         command=self.test_audio)
        self.test_button.pack(side=tk.LEFT, padx=5)

        # Conversation display
        conv_frame = ttk.LabelFrame(main_frame, text="📝 Live Conversation", padding=10)
        conv_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.conversation_text = scrolledtext.ScrolledText(conv_frame, height=15, 
                                                          wrap=tk.WORD, font=('Consolas', 10))
        self.conversation_text.pack(fill=tk.BOTH, expand=True)

        # AI Response area
        ai_frame = ttk.LabelFrame(main_frame, text="🤖 AI Assistant Response", padding=10)
        ai_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.ai_response_text = scrolledtext.ScrolledText(ai_frame, height=8, 
                                                         wrap=tk.WORD, font=('Arial', 10),
                                                         bg='#e8f4fd')
        self.ai_response_text.pack(fill=tk.BOTH, expand=True)

        # Instructions
        instructions = """
📋 Quick Start:
• Make sure Ollama is running: ollama serve
• Make sure Gemma is installed: ollama pull gemma:2b
• Click 'Test Audio' to verify microphone
• Press Ctrl+H when you need help understanding something
        """

        inst_label = ttk.Label(main_frame, text=instructions, 
                              font=('Arial', 9), foreground='gray')
        inst_label.pack(pady=(5, 0))
        
    def setup_update_checker(self):
        """Setup thread-safe GUI updates"""
        def check_updates():
            try:
                while True:
                    update_func, args = self.update_queue.get(timeout=0.1)
                    update_func(*args)
            except queue.Empty:
                pass
            self.root.after(100, check_updates)
        
        self.root.after(100, check_updates)
    
    def thread_safe_update(self, func, *args):
        """Thread-safe way to update GUI"""
        self.update_queue.put((func, args))
    
    def _update_status(self, text, color='black'):
        self.status_label.config(text=text, foreground=color)
    
    def update_status(self, text, color='black'):
        self.thread_safe_update(self._update_status, text, color)
    
    def _add_conversation(self, speaker, text):
        timestamp = time.strftime("%H:%M:%S")
        self.conversation_text.insert(tk.END, f"[{timestamp}] {speaker}: {text}\n\n")
        self.conversation_text.see(tk.END)
    
    def add_conversation(self, speaker, text):
        self.thread_safe_update(self._add_conversation, speaker, text)
    
    def _show_ai_response(self, response):
        timestamp = time.strftime("%H:%M:%S")
        self.ai_response_text.delete(1.0, tk.END)
        self.ai_response_text.insert(tk.END, f"[{timestamp}] 🤖 AI Assistant:\n\n{response}")
    
    def show_ai_response(self, response):
        self.thread_safe_update(self._show_ai_response, response)
    
    def _enable_help_button(self):
        self.help_button.config(state='normal')
    
    def enable_help_button(self):
        self.thread_safe_update(self._enable_help_button)
    
    def request_help(self):
        global manual_help_requested
        manual_help_requested = True
        self.update_status("🔄 Processing recent conversation for help...", 'orange')
    
    def clear_conversation(self):
        self.conversation_text.delete(1.0, tk.END)
        self.ai_response_text.delete(1.0, tk.END)
        recent_speech.clear()
    
    def test_audio(self):
        """Test audio input"""
        def test():
            try:
                self.update_status("🎙️ Testing audio... Speak now!", 'blue')
                # Record 3 seconds of audio
                duration = 3
                recording = sd.rec(int(duration * SAMPLE_RATE), 
                                 samplerate=SAMPLE_RATE, channels=1, dtype=np.int16)
                sd.wait()
                
                # Check if audio was captured
                if np.max(np.abs(recording)) > 100:
                    self.update_status("✅ Audio test successful!", 'green')
                    
                    # Try transcription
                    if model:
                        audio_float = recording.flatten().astype(np.float32) / 32768.0
                        result = model.transcribe(audio_float, language="en")
                        text = result["text"].strip()
                        if text:
                            self.add_conversation("Test", f"Transcription: {text}")
                        else:
                            self.add_conversation("Test", "Audio captured but no speech detected")
                else:
                    self.update_status("⚠️ No audio detected - check microphone", 'red')
                    
            except Exception as e:
                self.update_status(f"❌ Audio test failed: {str(e)}", 'red')
        
        threading.Thread(target=test, daemon=True).start()

# -------------------------------
# AUDIO PROCESSING
# -------------------------------
def is_silent(audio_data, threshold=SILENCE_THRESHOLD):
    if len(audio_data) == 0:
        return True
    return np.mean(np.abs(audio_data.astype(np.float32))) < threshold

def audio_callback(indata, frames, time, status):
    if status:
        print(f"Audio status: {status}")
    audio_queue.put(indata.copy())

def transcribe_audio(audio_data):
    try:
        if len(audio_data) == 0:
            return ""
            
        # Ensure audio_data is 1D and normalized
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()
        
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        # Add some padding to avoid edge effects
        if len(audio_float) < SAMPLE_RATE:  # Less than 1 second
            return ""
        
        # Only allow 'en' or 'hi' as language
        lang = gui.selected_language.get() if gui and hasattr(gui, 'selected_language') else 'en'
        if lang not in ("en", "hi"):
            lang = "en"
        result = model.transcribe(
            audio_float, 
            language=lang,
            fp16=False,
            no_speech_threshold=0.6,
            condition_on_previous_text=False,
            initial_prompt="This is a meeting conversation."
        )
        
        text = result["text"].strip()
        confidence = result.get("language", "")
        
        # Filter out very short or meaningless transcriptions
        if len(text) < 5 or text.lower() in ["thank you.", "thanks.", "hmm.", "uh.", "um."]:
            return ""
            
        return text
        
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""

# -------------------------------
# AI ASSISTANCE
# -------------------------------
def get_ai_help(context_messages):
    if not context_messages:
        return "No recent conversation to analyze."
    
    # Build context from recent messages
    context = "Recent meeting conversation:\n"
    for msg in context_messages[-8:]:  # Last 8 messages for context
        context += f"• {msg}\n"
    
    prompt = f"""You are an AI meeting assistant helping someone who got confused during a conversation.

{context}

Please provide a helpful response that:
1. Briefly summarizes what was just discussed
2. Explains any technical terms or complex topics mentioned
3. Suggests what the person might say or ask for clarification
4. Keep it concise (2-3 sentences max)

Be helpful and practical, like a knowledgeable colleague whispering advice."""
    
    ollama_url = "http://localhost:11434/api/generate"
    payload = {
        "model": "gemma:2b",
        "prompt": prompt,
        "stream": False,  # Non-streaming for reliability
        "options": {
            "temperature": 0.3,  # Lower temperature for more focused responses
            "max_tokens": 200,
            "top_p": 0.9
        }
    }
    
    try:
        response = requests.post(ollama_url, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get("response", "").strip()
            return ai_response if ai_response else "Sorry, couldn't generate a helpful response."
        else:
            return f"Error: Ollama returned status {response.status_code}"
    except requests.exceptions.Timeout:
        return "Error: Request timed out. Ollama might be busy."
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

# -------------------------------
# MAIN AUDIO LOOP
# -------------------------------
def audio_processing_loop():
    global manual_help_requested, is_listening
    
    buffer = np.array([], dtype=np.int16)
    last_activity_time = time.time()
    speaker_count = 1
    
    gui.update_status("🎤 Starting audio stream...", 'blue')
    
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=audio_callback, 
                           blocksize=BLOCKSIZE, dtype=np.int16):
            
            gui.update_status("🎧 Listening to conversation...", 'green')
            gui.enable_help_button()
            
            while is_listening:
                try:
                    # Collect audio data from queue
                    audio_collected = False
                    while not audio_queue.empty():
                        data = audio_queue.get_nowait()
                        data_flat = data.flatten()
                        buffer = np.concatenate((buffer, data_flat))
                        audio_collected = True
                    
                    current_time = time.time()
                    buffer_duration = len(buffer) / SAMPLE_RATE
                    
                    # Process speech detection and transcription
                    if buffer_duration >= MIN_SPEECH_DURATION:
                        if not is_silent(buffer):
                            gui.update_status("🎙️ Speech detected, processing...", 'orange')
                            
                            # Transcribe the audio
                            transcript = transcribe_audio(buffer)
                            
                            if transcript:
                                speaker_name = f"Speaker {speaker_count}"
                                gui.add_conversation(speaker_name, transcript)
                                recent_speech.append(f"{speaker_name}: {transcript}")

                                speaker_count = (speaker_count % 2) + 1  # Cycle through 2 speakers
                                last_activity_time = current_time
                            
                            # Clear buffer after processing
                            buffer = np.array([], dtype=np.int16)
                            gui.update_status("🎧 Listening to conversation...", 'green')
                        
                        elif buffer_duration > 10:  # Clear old silent audio
                            buffer = buffer[-int(2 * SAMPLE_RATE):]  # Keep last 2 seconds
                    
                    # Handle manual help request
                    if manual_help_requested:
                        if recent_speech:
                            gui.update_status("🤖 Getting AI help...", 'blue')
                            ai_response = get_ai_help(list(recent_speech))
                            gui.show_ai_response(ai_response)
                            gui.update_status("🎧 Listening to conversation...", 'green')
                        else:
                            gui.show_ai_response("No recent conversation to analyze. Start speaking to capture audio.")
                        
                        manual_help_requested = False
                    
                    # Prevent memory overflow
                    if buffer_duration > MAX_BUFFER_DURATION:
                        buffer = buffer[-int(10 * SAMPLE_RATE):]  # Keep last 10 seconds
                    
                    time.sleep(0.05)  # Reduced sleep for better responsiveness
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Audio loop error: {e}")
                    time.sleep(0.1)
                    
    except Exception as e:
        print(f"Audio stream error: {e}")
        gui.update_status(f"❌ Audio error: {str(e)}", 'red')

# -------------------------------
# HOTKEY HANDLER
# -------------------------------
def setup_hotkeys():
    try:
        def on_help_request():
            global manual_help_requested
            manual_help_requested = True
        
        keyboard.add_hotkey(HELP_HOTKEY, on_help_request, suppress=False)
        print(f"✅ Hotkey {HELP_HOTKEY} registered")
        return True
    except Exception as e:
        print(f"⚠️ Hotkey setup failed: {e}")
        return False

# -------------------------------
# MAIN FUNCTION
# -------------------------------
def main():
    global is_listening, gui
    
    print("🚀 Starting Meeting AI Assistant")
    print("="*50)
    
    # Initialize GUI
    gui = MeetingAssistantGUI()
    
    # Initialize Whisper
    if not initialize_whisper():
        messagebox.showerror("Error", "Failed to load Whisper model. Please install it:\npip install openai-whisper")
        return
    
    # Test Ollama
    if not test_ollama_connection():
        response = messagebox.askyesno("Ollama Not Ready", 
                                     "Ollama is not running or Gemma model not found.\n\n"
                                     "Do you want to continue anyway?\n"
                                     "(You can still test audio transcription)")
        if not response:
            return
    
    # Setup hotkeys
    hotkey_success = setup_hotkeys()
    if not hotkey_success:
        gui.update_status("⚠️ Hotkeys unavailable - use button instead", 'orange')
    
    # Start audio processing
    audio_thread = threading.Thread(target=audio_processing_loop, daemon=True)
    audio_thread.start()
    
    try:
        print("✅ All systems ready!")
        gui.update_status("✅ Ready! Press Ctrl+H for help or click 'Test Audio'", 'green')
        gui.root.mainloop()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
    finally:
        is_listening = False
        print("👋 Meeting Assistant stopped")

if __name__ == "__main__":
    main()