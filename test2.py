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
from tkinter import scrolledtext, ttk
import keyboard  # pip install keyboard

# -------------------------------
# CONFIG
# -------------------------------
SAMPLE_RATE = 16000
BLOCKSIZE = 1024
CONTINUOUS_LISTENING = True
SILENCE_THRESHOLD = 0.015
MIN_SPEECH_DURATION = 2.0  # Minimum seconds of speech to process
PROCESSING_INTERVAL = 4.0  # Process speech every 4 seconds
HELP_HOTKEY = 'ctrl+h'  # Hotkey to trigger AI assistance

print("Loading Whisper model...")
model = whisper.load_model("base")  # Better accuracy for meeting scenarios
print("✅ Whisper model loaded!")

# Queues and state
audio_queue = queue.Queue()
conversation_context = []
recent_speech = deque(maxlen=50)  # Store recent conversations
is_listening = True
manual_help_requested = False

class MeetingAssistantGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Meeting AI Assistant - Gemma Helper")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎤 Meeting AI Assistant", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="🎧 Listening to conversation...", 
                                     foreground='green')
        self.status_label.pack(side=tk.LEFT)
        
        # Control buttons
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.help_button = ttk.Button(button_frame, text="🆘 Need Help (Ctrl+H)", 
                                     command=self.request_help)
        self.help_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="🧹 Clear", 
                                      command=self.clear_conversation)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Conversation display
        conv_label = ttk.Label(main_frame, text="📝 Live Conversation:", 
                              font=('Arial', 12, 'bold'))
        conv_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.conversation_text = scrolledtext.ScrolledText(main_frame, height=15, 
                                                          wrap=tk.WORD, font=('Arial', 10))
        self.conversation_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # AI Response area
        ai_label = ttk.Label(main_frame, text="🤖 AI Assistant Response:", 
                            font=('Arial', 12, 'bold'))
        ai_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.ai_response_text = scrolledtext.ScrolledText(main_frame, height=8, 
                                                         wrap=tk.WORD, font=('Arial', 10),
                                                         bg='#e8f4fd')
        self.ai_response_text.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        instructions = """
📋 Instructions:
• This AI assistant listens to your meeting/conversation continuously
• When someone asks a confusing question, press Ctrl+H or click "Need Help"
• The AI will analyze the recent conversation and provide helpful context
• Perfect for Zoom calls, meetings, or any discussion where you need clarification
        """
        
        inst_label = ttk.Label(main_frame, text=instructions, 
                              font=('Arial', 9), foreground='gray')
        inst_label.pack(pady=(10, 0))
        
    def update_status(self, text, color='black'):
        self.status_label.config(text=text, foreground=color)
        self.root.update()
    
    def add_conversation(self, speaker, text):
        timestamp = time.strftime("%H:%M:%S")
        self.conversation_text.insert(tk.END, f"[{timestamp}] {speaker}: {text}\n\n")
        self.conversation_text.see(tk.END)
        self.root.update()
    
    def show_ai_response(self, response):
        timestamp = time.strftime("%H:%M:%S")
        self.ai_response_text.delete(1.0, tk.END)
        self.ai_response_text.insert(tk.END, f"[{timestamp}] 🤖 AI Assistant:\n\n{response}")
        self.root.update()
    
    def request_help(self):
        global manual_help_requested
        manual_help_requested = True
        self.update_status("🔄 Processing recent conversation for help...", 'orange')
    
    def clear_conversation(self):
        self.conversation_text.delete(1.0, tk.END)
        self.ai_response_text.delete(1.0, tk.END)
        recent_speech.clear()
        conversation_context.clear()

# Create GUI instance
gui = MeetingAssistantGUI()

# -------------------------------
# AUDIO PROCESSING
# -------------------------------
def is_silent(audio_data, threshold=SILENCE_THRESHOLD):
    return np.mean(np.abs(audio_data)) < threshold

def audio_callback(indata, frames, time, status):
    if status:
        print(f"Audio status: {status}")
    audio_queue.put(indata.copy())

def transcribe_audio(audio_data):
    try:
        # Ensure audio_data is 1D
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()
        
        audio_float = audio_data.astype(np.float32) / 32768.0
        result = model.transcribe(
            audio_float, 
            language="en",
            fp16=False,
            no_speech_threshold=0.6,
            condition_on_previous_text=False
        )
        return result["text"].strip()
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""

# -------------------------------
# AI ASSISTANCE
# -------------------------------
def get_ai_help(context_messages):
    """Get AI help based on recent conversation context"""
    
    # Build context from recent messages
    context = "Recent conversation context:\n"
    for msg in context_messages[-10:]:  # Last 10 messages
        context += f"- {msg}\n"
    
    prompt = f"""You are an AI meeting assistant. A person is confused during a conversation/meeting and needs help understanding what was discussed. 

{context}

Please provide a helpful response that:
1. Summarizes the key points discussed
2. Explains any confusing questions or topics mentioned
3. Suggests potential answers or responses if appropriate
4. Keeps the response concise but informative

Focus on being helpful and clear, as if you're a knowledgeable colleague providing assistance during a meeting.

Response:"""
    
    # Call Gemma 2B via Ollama
    ollama_url = "http://localhost:11434/api/generate"
    payload = {
        "model": "gemma:2b",
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "max_tokens": 300
        }
    }
    
    response = ""
    try:
        with requests.post(ollama_url, json=payload, stream=True, timeout=30) as r:
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode("utf-8"))
                        piece = data.get("response", "")
                        response += piece
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        return response.strip() if response.strip() else "No response generated."
    except Exception as e:
        return f"[AI Error: {str(e)}. Make sure Ollama is running with gemma:2b model.]"

# -------------------------------
# MAIN AUDIO LOOP
# -------------------------------
def audio_processing_loop():
    global manual_help_requested, is_listening
    
    buffer = np.array([], dtype=np.int16)
    last_process_time = time.time()
    speech_start_time = None
    speaker_count = 1
    
    print("🎤 Starting audio stream...")
    
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=audio_callback, 
                           blocksize=BLOCKSIZE, dtype=np.int16):
            
            gui.update_status("🎧 Listening to conversation...", 'green')
            
            while is_listening:
                # Collect audio data from queue
                while not audio_queue.empty():
                    data = audio_queue.get()
                    # Flatten the data to ensure 1D array
                    data_flat = data.flatten()
                    buffer = np.concatenate((buffer, data_flat))
                
                current_time = time.time()
                buffer_duration = len(buffer) / SAMPLE_RATE
                
                # Process audio if we have enough data and it's not silent
                if buffer_duration >= MIN_SPEECH_DURATION:
                    if not is_silent(buffer):
                        if speech_start_time is None:
                            speech_start_time = current_time
                            gui.update_status("🎙️ Speech detected, processing...", 'orange')
                        
                        # Process if we have enough speech
                        if current_time - speech_start_time >= MIN_SPEECH_DURATION:
                            transcript = transcribe_audio(buffer)
                            
                            if transcript and len(transcript.strip()) > 3:
                                speaker_name = f"Speaker {speaker_count}"
                                gui.add_conversation(speaker_name, transcript)
                                recent_speech.append(f"{speaker_name}: {transcript}")
                                conversation_context.append({"role": "user", "content": transcript})
                                
                                speaker_count += 1
                                if speaker_count > 10:
                                    speaker_count = 1
                            
                            # Clear buffer after processing
                            buffer = np.array([], dtype=np.int16)
                            speech_start_time = None
                            gui.update_status("🎧 Listening to conversation...", 'green')
                    
                    else:
                        # Reset if we encounter silence
                        speech_start_time = None
                        # Keep some buffer but not too much
                        if buffer_duration > 10:  # Keep last 6 seconds if too long
                            keep_samples = int(6 * SAMPLE_RATE)
                            buffer = buffer[-keep_samples:]
                
                # Handle manual help request
                if manual_help_requested:
                    if recent_speech:
                        gui.update_status("🤖 Getting AI help...", 'blue')
                        ai_response = get_ai_help(list(recent_speech))
                        gui.show_ai_response(ai_response)
                        gui.update_status("🎧 Listening to conversation...", 'green')
                    else:
                        gui.show_ai_response("No recent conversation to analyze. Please speak something first.")
                    
                    manual_help_requested = False
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.1)
                
    except Exception as e:
        print(f"Audio processing error: {e}")
        gui.update_status(f"❌ Audio error: {str(e)}", 'red')

# -------------------------------
# HOTKEY HANDLER
# -------------------------------
def hotkey_listener():
    try:
        keyboard.add_hotkey(HELP_HOTKEY, gui.request_help)
        print(f"✅ Hotkey {HELP_HOTKEY} registered")
        # Keep the hotkey listener alive
        while is_listening:
            time.sleep(0.1)
    except Exception as e:
        print(f"Hotkey error: {e}")

# -------------------------------
# MAIN ENTRY
# -------------------------------
def main():
    global is_listening
    
    print("🚀 Starting Meeting AI Assistant")
    
    # Test Ollama connection
    try:
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if test_response.status_code == 200:
            print("✅ Ollama connection successful")
        else:
            print("⚠️ Ollama connection issue - make sure it's running")
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
    
    # Start threads
    audio_thread = threading.Thread(target=audio_processing_loop, daemon=True)
    hotkey_thread = threading.Thread(target=hotkey_listener, daemon=True)
    
    audio_thread.start()
    hotkey_thread.start()
    
    try:
        # Run GUI main loop
        gui.root.mainloop()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        is_listening = False
        print("👋 Meeting Assistant stopped")

if __name__ == "__main__":
    main()


