// Hugging Face Configuration
const fs = require('fs');
const path = require('path');

// Try to load from .env file if it exists
let hfAccessToken = null;
let whisperModel = 'openai/whisper-medium';
let gemmaModel = 'gemma2b';

try {
    // Check if .env file exists
    const envPath = path.join(__dirname, '../../.env');
    if (fs.existsSync(envPath)) {
        const envContent = fs.readFileSync(envPath, 'utf8');
        const lines = envContent.split('\n');
        
        for (const line of lines) {
            const [key, value] = line.split('=');
            if (key && value) {
                if (key === 'HUGGING_FACE_ACCESS_TOKEN') {
                    hfAccessToken = value.trim();
                } else if (key === 'WHISPER_MODEL') {
                    whisperModel = value.trim();
                } else if (key === 'GEMMA_MODEL') {
                    gemmaModel = value.trim();
                }
            }
        }
    }
} catch (error) {
    console.warn('Could not load .env file:', error.message);
}

// Fallback: check environment variables
if (!hfAccessToken) {
    hfAccessToken = process.env.HUGGING_FACE_ACCESS_TOKEN;
}

if (!hfAccessToken) {
    console.warn('Hugging Face access token not found. Please set HUGGING_FACE_ACCESS_TOKEN in .env file or environment variables.');
}

module.exports = {
    hfAccessToken,
    whisperModel,
    gemmaModel,
    isConfigured: !!hfAccessToken
};
