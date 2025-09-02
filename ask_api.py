from flask import Flask, request, jsonify
import whisper
import requests
import tempfile
import os

app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def ask():
    # Get language from form (default to English)
    lang = request.form.get('language', 'en')
    if lang not in ['en', 'hi']:
        return jsonify({'error': 'Invalid language'}), 400

    # Get audio file
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400
    audio_file = request.files['audio']

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmpfile:
        audio_file.save(tmpfile.name)
        temp_path = tmpfile.name

    try:
        # Transcribe
        model = whisper.load_model('base')
        result = model.transcribe(temp_path, language=lang)
        question = result['text'].strip()
        if len(question) < 3:
            return jsonify({'error': 'Transcription too short or unclear.'}), 400

        # Ask Gemma
        ollama_url = 'http://localhost:11434/api/generate'
        payload = {
            'model': 'gemma:2b',
            'prompt': f'Answer this question concisely: {question}',
            'stream': False
        }
        response = requests.post(ollama_url, json=payload)
        response.raise_for_status()
        result = response.json()
        answer = result.get('response', 'No response received')
        return jsonify({'question': question, 'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
