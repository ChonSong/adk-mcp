/**
 * ADK-MCP Voice Client
 * Handles voice interaction, WebSocket communication, and audio processing
 */

class VoiceClient {
    constructor() {
        this.websocket = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.audioWorklet = null;
        this.isRecording = false;
        this.isConnected = false;
        this.sessionId = null;
        
        // Statistics
        this.stats = {
            messagesCount: 0,
            executionsCount: 0,
            sessionStart: null,
            connectionStatus: 'disconnected'
        };
        
        // Audio processing
        this.audioChunks = [];
        this.sequenceNumber = 0;
        
        // UI elements
        this.initializeElements();
        this.setupEventListeners();
        this.initializeAudioVisualizer();
        
        // Check browser compatibility
        this.checkBrowserSupport();
    }
    
    initializeElements() {
        // Voice controls
        this.startVoiceBtn = document.getElementById('startVoiceBtn');
        this.stopVoiceBtn = document.getElementById('stopVoiceBtn');
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
        
        // Conversation
        this.conversationArea = document.getElementById('conversationArea');
        
        // Code execution
        this.codeEditor = document.getElementById('codeEditor');
        this.codeOutput = document.getElementById('codeOutput');
        this.executeBtn = document.getElementById('executeBtn');
        this.clearCodeBtn = document.getElementById('clearCodeBtn');
        this.clearOutputBtn = document.getElementById('clearOutputBtn');
        this.speakOutputBtn = document.getElementById('speakOutputBtn');
        
        // Messages
        this.errorMessage = document.getElementById('errorMessage');
        this.successMessage = document.getElementById('successMessage');
        
        // Statistics
        this.messagesCountEl = document.getElementById('messagesCount');
        this.executionsCountEl = document.getElementById('executionsCount');
        this.sessionDurationEl = document.getElementById('sessionDuration');
        this.connectionStatusEl = document.getElementById('connectionStatus');
    }
    
    setupEventListeners() {
        // Voice controls
        this.startVoiceBtn.addEventListener('click', () => this.startVoiceSession());
        this.stopVoiceBtn.addEventListener('click', () => this.stopVoiceSession());
        
        // Code execution
        this.executeBtn.addEventListener('click', () => this.executeCode());
        this.clearCodeBtn.addEventListener('click', () => this.clearCode());
        this.clearOutputBtn.addEventListener('click', () => this.clearOutput());
        this.speakOutputBtn.addEventListener('click', () => this.speakOutput());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                this.executeCode();
            }
            if (e.key === 'F2') {
                e.preventDefault();
                if (this.isRecording) {
                    this.stopVoiceSession();
                } else {
                    this.startVoiceSession();
                }
            }
        });
        
        // Window events
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }
    
    initializeAudioVisualizer() {
        const audioBars = document.getElementById('audioBars');
        
        // Create audio visualization bars
        for (let i = 0; i < 20; i++) {
            const bar = document.createElement('div');
            bar.className = 'audio-bar';
            bar.style.height = '5px';
            audioBars.appendChild(bar);
        }
        
        this.audioBars = audioBars.children;
    }
    
    checkBrowserSupport() {
        const requirements = {
            webSocket: 'WebSocket' in window,
            webAudio: 'AudioContext' in window || 'webkitAudioContext' in window,
            mediaDevices: navigator.mediaDevices && navigator.mediaDevices.getUserMedia,
            audioWorklet: 'AudioWorklet' in window
        };
        
        const unsupported = Object.entries(requirements)
            .filter(([key, supported]) => !supported)
            .map(([key]) => key);
        
        if (unsupported.length > 0) {
            this.showError(`Browser missing support for: ${unsupported.join(', ')}`);
            this.startVoiceBtn.disabled = true;
        }
    }
    
    async startVoiceSession() {
        try {
            this.showSuccess('Starting voice session...');
            this.updateStatus('connecting', 'Connecting...');
            
            // Request microphone permission
            await this.requestMicrophoneAccess();
            
            // Initialize audio context
            await this.initializeAudioContext();
            
            // Connect to WebSocket
            await this.connectWebSocket();
            
            // Start recording
            await this.startRecording();
            
            this.updateUI(true);
            this.stats.sessionStart = new Date();
            this.startSessionTimer();
            
            this.showSuccess('Voice session started! You can now speak.');
            
        } catch (error) {
            console.error('Error starting voice session:', error);
            this.showError(`Failed to start voice session: ${error.message}`);
            this.updateStatus('disconnected', 'Disconnected');
        }
    }
    
    async stopVoiceSession() {
        try {
            this.updateStatus('disconnected', 'Stopping...');
            
            // Stop recording
            await this.stopRecording();
            
            // Close WebSocket
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }
            
            // Clean up audio context
            if (this.audioContext) {
                await this.audioContext.close();
                this.audioContext = null;
            }
            
            this.updateUI(false);
            this.stopSessionTimer();
            
            this.showSuccess('Voice session stopped.');
            
        } catch (error) {
            console.error('Error stopping voice session:', error);
            this.showError(`Error stopping session: ${error.message}`);
        }
    }
    
    async requestMicrophoneAccess() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
        } catch (error) {
            throw new Error('Microphone access denied or not available');
        }
    }
    
    async initializeAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
            
            // Resume context if suspended
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
        } catch (error) {
            throw new Error('Failed to initialize audio context');
        }
    }
    
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://${window.location.host}/voice/stream`;
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.updateStatus('connected', 'Connected');
                resolve();
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(event);
            };
            
            this.websocket.onclose = () => {
                this.isConnected = false;
                this.updateStatus('disconnected', 'Disconnected');
            };
            
            this.websocket.onerror = (error) => {
                reject(new Error('WebSocket connection failed'));
            };
            
            // Timeout after 10 seconds
            setTimeout(() => {
                if (!this.isConnected) {
                    reject(new Error('WebSocket connection timeout'));
                }
            }, 10000);
        });
    }
    
    async startRecording() {
        try {
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            // Create audio processor
            await this.audioContext.audioWorklet.addModule('audio-processor.js');
            this.audioWorklet = new AudioWorkletNode(this.audioContext, 'audio-processor');
            
            // Connect audio nodes
            source.connect(this.audioWorklet);
            this.audioWorklet.connect(this.audioContext.destination);
            
            // Handle audio data
            this.audioWorklet.port.onmessage = (event) => {
                this.handleAudioData(event.data);
            };
            
            this.isRecording = true;
            this.updateStatus('listening', 'Listening...');
            
        } catch (error) {
            // Fallback to ScriptProcessorNode for older browsers
            await this.startRecordingFallback();
        }
    }
    
    async startRecordingFallback() {
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        const processor = this.audioContext.createScriptProcessor(1024, 1, 1);
        
        processor.onaudioprocess = (event) => {
            const inputBuffer = event.inputBuffer;
            const inputData = inputBuffer.getChannelData(0);
            
            // Convert to 16-bit PCM
            const pcmData = this.floatTo16BitPCM(inputData);
            this.handleAudioData(pcmData);
        };
        
        source.connect(processor);
        processor.connect(this.audioContext.destination);
        
        this.audioProcessor = processor;
        this.isRecording = true;
        this.updateStatus('listening', 'Listening...');
    }
    
    async stopRecording() {
        this.isRecording = false;
        
        if (this.audioWorklet) {
            this.audioWorklet.disconnect();
            this.audioWorklet = null;
        }
        
        if (this.audioProcessor) {
            this.audioProcessor.disconnect();
            this.audioProcessor = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
    }
    
    handleAudioData(audioData) {
        if (!this.isRecording || !this.isConnected) return;
        
        // Update audio visualizer
        this.updateAudioVisualizer(audioData);
        
        // Send audio chunk to server
        this.sendAudioChunk(audioData);
    }
    
    sendAudioChunk(audioData) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) return;
        
        const message = {
            type: 'audio_chunk',
            audio_data: this.arrayBufferToHex(audioData),
            sequence_number: this.sequenceNumber++,
            timestamp: new Date().toISOString()
        };
        
        this.websocket.send(JSON.stringify(message));
    }
    
    handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'session_started':
                    this.sessionId = data.session_id;
                    this.addMessage('system', 'Voice session started');
                    break;
                    
                case 'transcription':
                    this.addMessage('user', data.text);
                    break;
                    
                case 'response':
                    this.addMessage('assistant', data.text);
                    if (data.audio_data) {
                        this.playAudioResponse(data.audio_data);
                    }
                    break;
                    
                case 'audio_chunk_ack':
                    // Audio chunk acknowledged
                    break;
                    
                case 'listening_started':
                    this.updateStatus('listening', 'Listening...');
                    break;
                    
                case 'listening_stopped':
                    this.updateStatus('connected', 'Connected');
                    break;
                    
                case 'interruption':
                    this.updateStatus('connected', 'Interrupted');
                    break;
                    
                case 'error':
                    this.showError(data.message);
                    break;
                    
                default:
                    console.log('Unknown message type:', data.type);
            }
            
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    async executeCode() {
        const code = this.codeEditor.value.trim();
        if (!code) {
            this.showError('Please enter some code to execute');
            return;
        }
        
        try {
            this.executeBtn.disabled = true;
            this.executeBtn.textContent = 'Executing...';
            
            const response = await fetch('/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.codeOutput.textContent = result.output || '(No output)';
                this.showSuccess('Code executed successfully');
            } else {
                this.codeOutput.textContent = `Error: ${result.error}`;
                this.showError('Code execution failed');
            }
            
            this.stats.executionsCount++;
            this.updateStats();
            
        } catch (error) {
            this.codeOutput.textContent = `Network Error: ${error.message}`;
            this.showError('Failed to execute code');
        } finally {
            this.executeBtn.disabled = false;
            this.executeBtn.textContent = 'Execute Code';
        }
    }
    
    clearCode() {
        this.codeEditor.value = '';
        this.codeEditor.focus();
    }
    
    clearOutput() {
        this.codeOutput.textContent = '';
    }
    
    speakOutput() {
        const output = this.codeOutput.textContent;
        if (!output || output === '(No output)') {
            this.showError('No output to speak');
            return;
        }
        
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(output);
            utterance.rate = 0.8;
            utterance.pitch = 1;
            speechSynthesis.speak(utterance);
        } else {
            this.showError('Speech synthesis not supported');
        }
    }
    
    addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.textContent = content;
        messageDiv.appendChild(contentDiv);
        
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'timestamp';
        timestampDiv.textContent = new Date().toLocaleTimeString();
        messageDiv.appendChild(timestampDiv);
        
        this.conversationArea.appendChild(messageDiv);
        this.conversationArea.scrollTop = this.conversationArea.scrollHeight;
        
        this.stats.messagesCount++;
        this.updateStats();
    }
    
    updateAudioVisualizer(audioData) {
        if (!this.audioBars) return;
        
        // Calculate RMS (Root Mean Square) for volume level
        let sum = 0;
        for (let i = 0; i < audioData.length; i++) {
            sum += audioData[i] * audioData[i];
        }
        const rms = Math.sqrt(sum / audioData.length);
        const volume = Math.min(rms * 1000, 100); // Scale and cap at 100
        
        // Update bars with random heights based on volume
        for (let i = 0; i < this.audioBars.length; i++) {
            const height = Math.random() * volume + 5;
            this.audioBars[i].style.height = `${height}px`;
        }
    }
    
    updateStatus(status, text) {
        this.statusDot.className = `status-dot ${status}`;
        this.statusText.textContent = text;
        this.stats.connectionStatus = status;
        this.updateStats();
    }
    
    updateUI(isActive) {
        if (isActive) {
            this.startVoiceBtn.style.display = 'none';
            this.stopVoiceBtn.style.display = 'inline-block';
        } else {
            this.startVoiceBtn.style.display = 'inline-block';
            this.stopVoiceBtn.style.display = 'none';
        }
    }
    
    updateStats() {
        this.messagesCountEl.textContent = this.stats.messagesCount;
        this.executionsCountEl.textContent = this.stats.executionsCount;
        
        const statusColors = {
            'connected': '#4CAF50',
            'listening': '#2196F3',
            'speaking': '#9C27B0',
            'connecting': '#ff9800',
            'disconnected': '#f44336'
        };
        
        this.connectionStatusEl.textContent = '●';
        this.connectionStatusEl.style.color = statusColors[this.stats.connectionStatus] || '#ccc';
    }
    
    startSessionTimer() {
        this.sessionTimer = setInterval(() => {
            if (this.stats.sessionStart) {
                const duration = new Date() - this.stats.sessionStart;
                const minutes = Math.floor(duration / 60000);
                const seconds = Math.floor((duration % 60000) / 1000);
                this.sessionDurationEl.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }
    
    stopSessionTimer() {
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
            this.sessionTimer = null;
        }
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        this.successMessage.style.display = 'none';
        
        setTimeout(() => {
            this.errorMessage.style.display = 'none';
        }, 5000);
    }
    
    showSuccess(message) {
        this.successMessage.textContent = message;
        this.successMessage.style.display = 'block';
        this.errorMessage.style.display = 'none';
        
        setTimeout(() => {
            this.successMessage.style.display = 'none';
        }, 3000);
    }
    
    // Utility functions
    floatTo16BitPCM(input) {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output;
    }
    
    arrayBufferToHex(buffer) {
        const bytes = new Uint8Array(buffer);
        return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
    }
    
    async playAudioResponse(audioData) {
        try {
            this.updateStatus('speaking', 'Speaking...');
            
            // Convert hex string back to audio data
            const bytes = new Uint8Array(audioData.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
            
            // Create audio buffer and play
            const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            
            source.onended = () => {
                this.updateStatus('listening', 'Listening...');
            };
            
            source.start();
            
        } catch (error) {
            console.error('Error playing audio response:', error);
            this.updateStatus('listening', 'Listening...');
        }
    }
    
    cleanup() {
        if (this.isRecording) {
            this.stopVoiceSession();
        }
        
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
        }
    }
}

// Initialize the voice client when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.voiceClient = new VoiceClient();
    
    // Add keyboard shortcut help
    console.log('ADK-MCP Voice Client loaded!');
    console.log('Keyboard shortcuts:');
    console.log('  Ctrl+Enter: Execute code');
    console.log('  F2: Toggle voice recording');
});