const { BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const { saveDebugAudio } = require('../audioUtils');
const { getSystemPrompt } = require('./prompts');
const { HfInference } = require('@huggingface/inference');
const hfConfig = require('../config/hf-config');

// Local AI configuration
const OLLAMA_BASE_URL = 'http://localhost:11434';
const GEMMA_MODEL = 'gemma2b'; // Ollama model name

// Conversation tracking variables
let currentSessionId = null;
let currentTranscription = '';
let conversationHistory = [];
let isInitializingSession = false;

// Audio capture variables
let systemAudioProc = null;
let messageBuffer = '';

// Hugging Face client for Whisper
let hfClient = null;

function formatSpeakerResults(results) {
    let text = '';
    for (const result of results) {
        if (result.transcript && result.speakerId) {
            const speakerLabel = result.speakerId === 1 ? 'Interviewer' : 'Candidate';
            text += `[${speakerLabel}]: ${result.transcript}\n`;
        }
    }
    return text;
}

module.exports.formatSpeakerResults = formatSpeakerResults;

function sendToRenderer(channel, data) {
    const windows = BrowserWindow.getAllWindows();
    if (windows.length > 0) {
        windows[0].webContents.send(channel, data);
    }
}

// Conversation management functions
function initializeNewSession() {
    currentSessionId = Date.now().toString();
    currentTranscription = '';
    conversationHistory = [];
    console.log('New conversation session started:', currentSessionId);
}

function saveConversationTurn(transcription, aiResponse) {
    if (!currentSessionId) {
        initializeNewSession();
    }

    const conversationTurn = {
        timestamp: Date.now(),
        transcription: transcription.trim(),
        ai_response: aiResponse.trim(),
    };

    conversationHistory.push(conversationTurn);
    console.log('Saved conversation turn:', conversationTurn);

    // Send to renderer to save in IndexedDB
    sendToRenderer('save-conversation-turn', {
        sessionId: currentSessionId,
        turn: conversationTurn,
        fullHistory: conversationHistory,
    });
}

function getCurrentSessionData() {
    return {
        sessionId: currentSessionId,
        history: conversationHistory,
    };
}

// Initialize Hugging Face client for Whisper
async function initializeHuggingFace() {
    if (!hfConfig.isConfigured) {
        throw new Error('Hugging Face access token not configured. Please set HUGGING_FACE_ACCESS_TOKEN in .env file.');
    }
    
    hfClient = new HfInference(hfConfig.hfAccessToken);
    console.log('Hugging Face client initialized for Whisper');
    return true;
}

// Transcribe audio using local Flask Whisper+Gemma API
async function transcribeAudio(audioBuffer, mimeType, language = 'en') {
    try {
        // Send audio to local Flask API
        const formData = new FormData();
        const audioBlob = new Blob([audioBuffer], { type: mimeType || 'audio/wav' });
        formData.append('audio', audioBlob, 'audio.wav');
        formData.append('language', language);

        const resp = await fetch('http://localhost:5000/ask', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        return data;
    } catch (error) {
        console.error('Error in audio transcription:', error);
        throw error;
    }
}

// Convert PCM buffer to WAV format
function convertPcmToWav(pcmBuffer) {
    const sampleRate = 24000;
    const channels = 1;
    const bitDepth = 16;
    
    const byteRate = sampleRate * channels * (bitDepth / 8);
    const blockAlign = channels * (bitDepth / 8);
    const dataSize = pcmBuffer.length;

    // Create WAV header
    const header = Buffer.alloc(44);

    // "RIFF" chunk descriptor
    header.write('RIFF', 0);
    header.writeUInt32LE(dataSize + 36, 4); // File size - 8
    header.write('WAVE', 8);

    // "fmt " sub-chunk
    header.write('fmt ', 12);
    header.writeUInt32LE(16, 16); // Subchunk1Size (16 for PCM)
    header.writeUInt16LE(1, 20); // AudioFormat (1 for PCM)
    header.writeUInt16LE(channels, 22); // NumChannels
    header.writeUInt32LE(sampleRate, 24); // SampleRate
    header.writeUInt32LE(byteRate, 28); // ByteRate
    header.writeUInt16LE(blockAlign, 32); // BlockAlign
    header.writeUInt16LE(bitDepth, 34); // BitsPerSample

    // "data" sub-chunk
    header.write('data', 36);
    header.writeUInt32LE(dataSize, 40); // Subchunk2Size

    // Combine header and PCM data
    return Buffer.concat([header, pcmBuffer]);
}

// Generate response using Ollama
async function generateResponse(prompt, conversationContext = []) {
    try {
        // Prepare the conversation context
        const messages = [
            {
                role: 'system',
                content: getSystemPrompt('interview', '', false) // Simplified system prompt
            }
        ];

        // Add conversation history
        conversationContext.forEach(turn => {
            messages.push({
                role: 'user',
                content: turn.transcription
            });
            messages.push({
                role: 'assistant',
                content: turn.ai_response
            });
        });

        // Add current prompt
        messages.push({
            role: 'user',
            content: prompt
        });

        // Make request to Ollama
        const response = await fetch(`${OLLAMA_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: GEMMA_MODEL,
                messages: messages,
                stream: false,
                options: {
                    temperature: 0.7,
                    top_p: 0.9,
                    max_tokens: 2048
                }
            })
        });

        if (!response.ok) {
            throw new Error(`Ollama API error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Ollama response:', data);
        
        return data.message?.content || 'No response generated';
    } catch (error) {
        console.error('Error generating response with Ollama:', error);
        throw error;
    }
}

// Check if Ollama is running and has required models
async function checkOllamaStatus() {
    try {
        const response = await fetch(`${OLLAMA_BASE_URL}/api/tags`);
        if (response.ok) {
            const data = await response.json();
            console.log('Ollama is running, available models:', data.models);
            
            // Check if Gemma model is available
            const hasGemma = data.models.some(model => model.name.includes('gemma'));
            
            if (!hasGemma) {
                console.warn('Gemma model not found. Run: ollama pull gemma2b');
            }
            
            return hasGemma;
        }
    } catch (error) {
        console.error('Ollama is not running:', error);
    }
    return false;
}

// Initialize local AI session (Hugging Face Whisper + Ollama Gemma)
async function initializeLocalAISession(customPrompt = '', profile = 'interview', language = 'en-US') {
    if (isInitializingSession) {
        console.log('Session initialization already in progress');
        return false;
    }

    isInitializingSession = true;
    sendToRenderer('session-initializing', true);

    try {
        // Initialize Hugging Face for Whisper
        await initializeHuggingFace();
        
        // Check if Ollama is running with required models
        const ollamaReady = await checkOllamaStatus();
        if (!ollamaReady) {
            throw new Error('Ollama is not running or missing required models. Please ensure Gemma 2B model is available.');
        }

        // Initialize new conversation session
        initializeNewSession();

        isInitializingSession = false;
        sendToRenderer('session-initializing', false);
        sendToRenderer('update-status', 'Local AI session ready - Hugging Face Whisper + Ollama Gemma 2B');
        
        return true;
    } catch (error) {
        console.error('Failed to initialize local AI session:', error);
        isInitializingSession = false;
        sendToRenderer('session-initializing', false);
        sendToRenderer('update-status', 'Error: ' + error.message);
        return false;
    }
}

// Process audio and generate response
async function processAudioAndRespond(audioBuffer, mimeType) {
    try {
        // Transcribe audio and get response from Flask API
        // Default to English if language is not set
        const language = 'en';
        const result = await transcribeAudio(audioBuffer, mimeType, language);
        if (result && result.question && result.answer) {
            currentTranscription = result.question;
            sendToRenderer('update-transcription', currentTranscription);
            messageBuffer = result.answer;
            sendToRenderer('update-response', messageBuffer);
            saveConversationTurn(currentTranscription, messageBuffer);
            currentTranscription = '';
            messageBuffer = '';
        }
    } catch (error) {
        console.error('Error processing audio and generating response:', error);
        sendToRenderer('update-status', 'Error: ' + error.message);
    }
}

// macOS audio capture functions (reused from original)
function killExistingSystemAudioDump() {
    return new Promise(resolve => {
        console.log('Checking for existing SystemAudioDump processes...');

        const killProc = spawn('pkill', ['-f', 'SystemAudioDump'], {
            stdio: 'ignore',
        });

        killProc.on('close', code => {
            if (code === 0) {
                console.log('Killed existing SystemAudioDump processes');
            } else {
                console.log('No existing SystemAudioDump processes found');
            }
            resolve();
        });

        killProc.on('error', err => {
            console.log('Error checking for existing processes (this is normal):', err.message);
            resolve();
        });

        setTimeout(() => {
            killProc.kill();
            resolve();
        }, 2000);
    });
}

async function startMacOSAudioCapture() {
    if (process.platform !== 'darwin') return false;

    await killExistingSystemAudioDump();

    console.log('Starting macOS audio capture with SystemAudioDump...');

    const { app } = require('electron');
    const path = require('path');

    let systemAudioPath;
    if (app.isPackaged) {
        systemAudioPath = path.join(process.resourcesPath, 'SystemAudioDump');
    } else {
        systemAudioPath = path.join(__dirname, '../assets', 'SystemAudioDump');
    }

    console.log('SystemAudioDump path:', systemAudioPath);

    const spawnOptions = {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: {
            ...process.env,
            PROCESS_NAME: 'AudioService',
            APP_NAME: 'System Audio Service',
        },
    };

    if (process.platform === 'darwin') {
        spawnOptions.detached = false;
        spawnOptions.windowsHide = false;
    }

    systemAudioProc = spawn(systemAudioPath, [], spawnOptions);

    if (!systemAudioProc.pid) {
        console.error('Failed to start SystemAudioDump');
        return false;
    }

    console.log('SystemAudioDump started with PID:', systemAudioProc.pid);

    const CHUNK_DURATION = 0.1;
    const SAMPLE_RATE = 24000;
    const BYTES_PER_SAMPLE = 2;
    const CHANNELS = 2;
    const CHUNK_SIZE = SAMPLE_RATE * BYTES_PER_SAMPLE * CHANNELS * CHUNK_DURATION;

    let audioBuffer = Buffer.alloc(0);

    systemAudioProc.stdout.on('data', data => {
        audioBuffer = Buffer.concat([audioBuffer, data]);

        while (audioBuffer.length >= CHUNK_SIZE) {
            const chunk = audioBuffer.slice(0, CHUNK_SIZE);
            audioBuffer = audioBuffer.slice(CHUNK_SIZE);

            const monoChunk = CHANNELS === 2 ? convertStereoToMono(chunk) : chunk;
            
            // Process audio with local AI instead of sending to Gemini
            processAudioAndRespond(monoChunk, 'audio/pcm;rate=24000');

            if (process.env.DEBUG_AUDIO) {
                console.log(`Processed audio chunk: ${chunk.length} bytes`);
                saveDebugAudio(monoChunk, 'system_audio');
            }
        }

        const maxBufferSize = SAMPLE_RATE * BYTES_PER_SAMPLE * 1;
        if (audioBuffer.length > maxBufferSize) {
            audioBuffer = audioBuffer.slice(-maxBufferSize);
        }
    });

    systemAudioProc.stderr.on('data', data => {
        console.error('SystemAudioDump stderr:', data.toString());
    });

    systemAudioProc.on('close', code => {
        console.log('SystemAudioDump process closed with code:', code);
        systemAudioProc = null;
    });

    systemAudioProc.on('error', err => {
        console.error('SystemAudioDump process error:', err);
        systemAudioProc = null;
    });

    return true;
}

function convertStereoToMono(stereoBuffer) {
    const samples = stereoBuffer.length / 4;
    const monoBuffer = Buffer.alloc(samples * 2);

    for (let i = 0; i < samples; i++) {
        const leftSample = stereoBuffer.readInt16LE(i * 4);
        monoBuffer.writeInt16LE(leftSample, i * 2);
    }

    return monoBuffer;
}

function stopMacOSAudioCapture() {
    if (systemAudioProc) {
        console.log('Stopping SystemAudioDump...');
        systemAudioProc.kill('SIGTERM');
        systemAudioProc = null;
    }
}

// Setup IPC handlers
function setupLocalAIIpcHandlers() {
    ipcMain.handle('initialize-local-ai', async (event, customPrompt, profile = 'interview', language = 'en-US') => {
        const success = await initializeLocalAISession(customPrompt, profile, language);
        return success;
    });

    ipcMain.handle('send-audio-content', async (event, { data, mimeType }) => {
        try {
            const audioBuffer = Buffer.from(data, 'base64');
            await processAudioAndRespond(audioBuffer, mimeType);
            return { success: true };
        } catch (error) {
            console.error('Error sending system audio:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('send-mic-audio-content', async (event, { data, mimeType }) => {
        try {
            const audioBuffer = Buffer.from(data, 'base64');
            await processAudioAndRespond(audioBuffer, mimeType);
            return { success: true };
        } catch (error) {
            console.error('Error sending mic audio:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('send-text-message', async (event, text) => {
        try {
            if (!text || typeof text !== 'string' || text.trim().length === 0) {
                return { success: false, error: 'Invalid text message' };
            }

            console.log('Sending text message:', text);
            const aiResponse = await generateResponse(text, conversationHistory);
            
            if (aiResponse) {
                sendToRenderer('update-response', aiResponse);
                saveConversationTurn(text, aiResponse);
            }
            
            return { success: true };
        } catch (error) {
            console.error('Error sending text:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('start-macos-audio', async event => {
        if (process.platform !== 'darwin') {
            return {
                success: false,
                error: 'macOS audio capture only available on macOS',
            };
        }

        try {
            const success = await startMacOSAudioCapture();
            return { success };
        } catch (error) {
            console.error('Error starting macOS audio capture:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('stop-macos-audio', async event => {
        try {
            stopMacOSAudioCapture();
            return { success: true };
        } catch (error) {
            console.error('Error stopping macOS audio capture:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('close-session', async event => {
        try {
            stopMacOSAudioCapture();

            // Cleanup any pending resources
            currentSessionId = null;
            currentTranscription = '';
            messageBuffer = '';
            conversationHistory = [];

            return { success: true };
        } catch (error) {
            console.error('Error closing session:', error);
            return { success: false, error: error.message };
        }
    });

    // Conversation history IPC handlers
    ipcMain.handle('get-current-session', async event => {
        try {
            return { success: true, data: getCurrentSessionData() };
        } catch (error) {
            console.error('Error getting current session:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('start-new-session', async event => {
        try {
            initializeNewSession();
            return { success: true, sessionId: currentSessionId };
        } catch (error) {
            console.error('Error starting new session:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('check-ollama-status', async event => {
        try {
            const status = await checkOllamaStatus();
            return { success: true, running: status };
        } catch (error) {
            console.error('Error checking Ollama status:', error);
            return { success: false, error: error.message };
        }
    });
}

module.exports = {
    initializeLocalAISession,
    processAudioAndRespond,
    transcribeAudio,
    generateResponse,
    checkOllamaStatus,
    sendToRenderer,
    initializeNewSession,
    saveConversationTurn,
    getCurrentSessionData,
    killExistingSystemAudioDump,
    startMacOSAudioCapture,
    convertStereoToMono,
    stopMacOSAudioCapture,
    setupLocalAIIpcHandlers,
    formatSpeakerResults,
};
