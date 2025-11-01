/**
 * AudioWorklet processor for low-latency audio processing
 * Handles real-time audio capture and processing for voice streaming
 */

class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        
        // Audio processing parameters
        this.bufferSize = 1024; // 64ms at 16kHz
        this.sampleRate = 16000;
        this.channels = 1;
        
        // Internal buffer for accumulating samples
        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
        
        // Voice activity detection
        this.vadThreshold = 0.01;
        this.vadSamples = 0;
        this.vadRequired = 160; // 10ms at 16kHz
        
        // Audio processing state
        this.isActive = false;
        this.sequenceNumber = 0;
        
        console.log('AudioProcessor initialized');
    }
    
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        if (input.length === 0) {
            return true; // Keep processor alive
        }
        
        const inputChannel = input[0];
        
        if (inputChannel.length === 0) {
            return true;
        }
        
        // Process audio samples
        this.processAudioSamples(inputChannel);
        
        return true; // Keep processor alive
    }
    
    processAudioSamples(samples) {
        for (let i = 0; i < samples.length; i++) {
            // Add sample to buffer
            this.buffer[this.bufferIndex] = samples[i];
            this.bufferIndex++;
            
            // Check if buffer is full
            if (this.bufferIndex >= this.bufferSize) {
                this.processBuffer();
                this.bufferIndex = 0;
            }
        }
    }
    
    processBuffer() {
        // Voice Activity Detection
        const hasVoiceActivity = this.detectVoiceActivity(this.buffer);
        
        if (hasVoiceActivity || this.isActive) {
            // Convert to 16-bit PCM
            const pcmData = this.floatTo16BitPCM(this.buffer);
            
            // Send audio data to main thread
            this.port.postMessage({
                type: 'audioData',
                data: pcmData,
                sequenceNumber: this.sequenceNumber++,
                timestamp: currentTime,
                hasVoiceActivity: hasVoiceActivity
            });
            
            this.isActive = hasVoiceActivity;
        }
    }
    
    detectVoiceActivity(buffer) {
        // Calculate RMS (Root Mean Square) energy
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
            sum += buffer[i] * buffer[i];
        }
        const rms = Math.sqrt(sum / buffer.length);
        
        // Simple voice activity detection based on energy threshold
        if (rms > this.vadThreshold) {
            this.vadSamples++;
            if (this.vadSamples >= this.vadRequired) {
                return true;
            }
        } else {
            this.vadSamples = Math.max(0, this.vadSamples - 1);
        }
        
        return false;
    }
    
    floatTo16BitPCM(input) {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            // Clamp to [-1, 1] range
            const sample = Math.max(-1, Math.min(1, input[i]));
            // Convert to 16-bit signed integer
            output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }
        return output;
    }
    
    // Handle messages from main thread
    static get parameterDescriptors() {
        return [
            {
                name: 'vadThreshold',
                defaultValue: 0.01,
                minValue: 0.001,
                maxValue: 0.1
            },
            {
                name: 'bufferSize',
                defaultValue: 1024,
                minValue: 256,
                maxValue: 4096
            }
        ];
    }
}

// Register the processor
registerProcessor('audio-processor', AudioProcessor);