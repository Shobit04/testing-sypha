import whisper
import requests
import sounddevice as sd
import numpy as np
import queue
import json

# -------------------------------
# CONFIG
# -------------------------------
fs = 8000   # Sample rate (lowered for less CPU usage)
blocksize = 2048  # Increase blocksize for better buffering
model = whisper.load_model("tiny")  # use "tiny" or "base" for faster real-time
q = queue.Queue()

conversation_history = []  # keep track of Q/A

# -------------------------------
# AUDIO STREAM HANDLER
# -------------------------------
def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(indata.copy())

# -------------------------------
# STREAM RESPONSE FROM GEMMA
# -------------------------------
def stream_to_gemma(question):
    global conversation_history
    conversation_history.append({"role": "user", "content": question})

    # Combine history into a prompt
    prompt = ""
    for turn in conversation_history:
        role = turn["role"].capitalize()
        prompt += f"{role}: {turn['content']}\n"

    ollama_url = "http://localhost:11434/api/generate"
    payload = {
        "model": "gemma:2b",
        "prompt": prompt + "Assistant:",
        "stream": True
    }

    answer = ""
    print("🤖 A: ", end="", flush=True)
    with requests.post(ollama_url, json=payload, stream=True) as r:
        for line in r.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                piece = data.get("response", "")
                answer += piece
                print(piece, end="", flush=True)
        print()

    conversation_history.append({"role": "assistant", "content": answer})

# -------------------------------
# REALTIME LOOP
# -------------------------------
def realtime_chat():
    print("🎤 Speak naturally... (Ctrl+C to stop)")
    buffer = np.zeros((0, 1), dtype=np.int16)
    chunk_duration = 2  # seconds, process every 2 seconds for lower latency

    with sd.InputStream(samplerate=fs, channels=1, callback=audio_callback, blocksize=blocksize):
        try:
            while True:
                while not q.empty():
                    data = q.get()
                    buffer = np.concatenate((buffer, data))

                # Process every chunk_duration seconds of speech
                if buffer.shape[0] >= chunk_duration * fs:
                    audio = buffer.flatten().astype(np.float32) / 32768.0
                    result = model.transcribe(audio, language="en")
                    question = result["text"].strip()

                    if question:
                        print(f"\n📝 Q: {question}")
                        stream_to_gemma(question)

                    # reset buffer
                    buffer = np.zeros((0, 1), dtype=np.int16)

        except KeyboardInterrupt:
            print("\n🛑 Conversation stopped.")

# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    realtime_chat()
