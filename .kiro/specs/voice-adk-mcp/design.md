# Design Document

## Overview

The Voice-First ADK-MCP system extends the existing ADK-MCP server to support real-time, bidirectional voice communication using Google's ADK-Web integration. The system enables natural voice conversations with an AI agent capable of executing Python code and providing intelligent responses through streaming audio.

The architecture leverages the existing foundation while adding voice streaming capabilities, WebSocket-based real-time communication, and enhanced Google Cloud integration with the gemini-2.5-pro model.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    WebSocket/Audio    ┌─────────────────┐
│   Web Client    │◄─────────────────────►│   ADK-MCP       │
│   (Browser)     │                       │   Server        │
└─────────────────┘                       └─────────────────┘
                                                    │
┌─────────────────┐    WebSocket/Audio              │ Google Cloud APIs
│  Android Client │◄─────────────────────────────────┤
│   (WebView)     │                                 │
└─────────────────┘                                 ▼
                                          ┌─────────────────┐
                                          │  Google Cloud   │
                                          │  - Vertex AI    │
                                          │  - Live API     │
                                          │  - STT/TTS      │
                                          └─────────────────┘
```

### System Components

1. **Enhanced ADK-MCP Server** (Python/FastAPI)
   - Existing HTTP/WebSocket server
   - New voice streaming endpoints
   - Google ADK-Web integration
   - Code execution engine

2. **Voice-Enabled Web Client** (HTML5/JavaScript)
   - Web Audio API integration
   - WebSocket client for audio streaming
   - Real-time audio playback
   - Minimal UI for voice control

3. **Android WebView Wrapper**
   - Native Android app container
   - Microphone permission handling
   - WebView with audio capabilities

4. **Google Cloud Integration**
   - Vertex AI with gemini-2.5-pro
   - Live API for real-time voice
   - Speech-to-Text and Text-to-Speech services

## Components and Interfaces

### 1. Voice Streaming Engine

**Purpose**: Manages real-time audio streaming and processing

**Key Classes**:
```python
class VoiceStreamManager:
    """Manages voice streaming sessions and audio processing"""
    
    async def start_voice_session(self, websocket: WebSocket) -> VoiceSession
    async def process_audio_chunk(self, audio_data: bytes, session: VoiceSession)
    async def handle_interruption(self, session: VoiceSession)
    async def end_voice_session(self, session: VoiceSession)

class VoiceSession:
    """Represents an active voice conversation session"""
    
    session_id: str
    websocket: WebSocket
    conversation_context: ConversationContext
    audio_buffer: AudioBuffer
    is_speaking: bool
    last_activity: datetime
```

**Interfaces**:
- WebSocket endpoint: `/voice/stream`
- Audio format: 16kHz, 16-bit, mono PCM
- Chunk size: 1024 bytes (64ms at 16kHz)

### 2. Google ADK-Web Integration

**Purpose**: Interfaces with Google's Live API for real-time voice processing

**Key Classes**:
```python
class GoogleADKVoiceAgent:
    """Enhanced Google ADK agent with voice capabilities"""
    
    async def initialize_live_session(self) -> LiveSession
    async def process_voice_input(self, audio_chunk: bytes) -> Optional[str]
    async def generate_voice_response(self, text: str) -> AsyncIterator[bytes]
    async def handle_interruption(self, session: LiveSession)

class LiveRequestQueue:
    """Manages real-time requests to Google Live API"""
    
    async def send_audio_chunk(self, audio: bytes)
    async def receive_transcription(self) -> Optional[str]
    async def send_text_response(self, text: str)
    async def receive_audio_response(self) -> AsyncIterator[bytes]
```

### 3. Enhanced Code Execution Tool

**Purpose**: Executes Python code safely with voice integration

**Key Classes**:
```python
class VoiceCodeExecutor:
    """Code execution with voice response capabilities"""
    
    async def execute_code_from_voice(self, code: str, session: VoiceSession) -> ExecutionResult
    async def speak_execution_result(self, result: ExecutionResult, session: VoiceSession)
    
class SafeExecutionEnvironment:
    """Sandboxed environment for code execution"""
    
    def execute_with_timeout(self, code: str, timeout: int = 30) -> ExecutionResult
    def sanitize_output(self, output: str) -> str
    def check_security_constraints(self, code: str) -> bool
```

### 4. Web Audio Client

**Purpose**: Handles audio capture and playback in the browser

**Key Components**:
```javascript
class VoiceClient {
    constructor(websocketUrl) {
        this.websocket = new WebSocket(websocketUrl);
        this.audioContext = new AudioContext();
        this.mediaStream = null;
        this.audioWorklet = null;
    }
    
    async startVoiceSession() {
        // Request microphone access
        // Initialize AudioWorklet for low-latency processing
        // Start WebSocket connection
    }
    
    async processAudioChunk(audioData) {
        // Send audio chunk to server via WebSocket
    }
    
    async playAudioResponse(audioData) {
        // Play received audio through speakers
    }
}

class AudioProcessor extends AudioWorkletProcessor {
    process(inputs, outputs, parameters) {
        // Low-latency audio processing
        // Send audio chunks to main thread
    }
}
```

## Data Models

### Voice Session Model
```python
@dataclass
class VoiceSession:
    session_id: str
    user_id: Optional[str]
    websocket: WebSocket
    conversation_context: ConversationContext
    audio_buffer: AudioBuffer
    is_speaking: bool
    is_listening: bool
    last_activity: datetime
    google_live_session: Optional[LiveSession]
    
@dataclass
class AudioChunk:
    data: bytes
    timestamp: datetime
    sequence_number: int
    sample_rate: int = 16000
    channels: int = 1
```

### Enhanced Conversation Context
```python
@dataclass
class ConversationContext:
    session_id: str
    conversation_history: List[VoiceMessage]
    code_execution_history: List[ExecutionResult]
    current_topic: Optional[str]
    user_preferences: Dict[str, Any]
    
@dataclass
class VoiceMessage:
    role: str  # "user" or "assistant"
    content: str
    audio_data: Optional[bytes]
    timestamp: datetime
    message_type: str  # "voice", "code_request", "code_result"
```

### Code Execution Models
```python
@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str]
    execution_time: float
    code: str
    timestamp: datetime
    
@dataclass
class CodeExecutionRequest:
    code: str
    session_id: str
    requested_via_voice: bool
    timeout: int = 30
```

## Error Handling

### Voice Streaming Errors
1. **Audio Processing Failures**
   - Graceful degradation to text mode
   - Error logging with session context
   - User notification via voice or text

2. **Google Cloud API Errors**
   - Retry logic with exponential backoff
   - Fallback to cached responses when appropriate
   - Clear error communication to user

3. **WebSocket Connection Issues**
   - Automatic reconnection attempts
   - Session state preservation
   - Buffer management during disconnections

### Code Execution Security
1. **Malicious Code Detection**
   - Static analysis for dangerous operations
   - Runtime monitoring for resource usage
   - Timeout enforcement for long-running code

2. **Sandboxing Strategy**
   - Restricted Python environment
   - Limited file system access
   - Network access controls
   - Memory and CPU limits

## Testing Strategy

### Unit Tests
- Voice streaming components
- Google ADK-Web integration
- Code execution safety measures
- Audio processing utilities

### Integration Tests
- End-to-end voice conversations
- WebSocket connection handling
- Google Cloud API integration
- Cross-platform compatibility

### Performance Tests
- Audio latency measurements
- Concurrent session handling
- Memory usage under load
- Network bandwidth optimization

### Security Tests
- Code execution sandboxing
- Input validation and sanitization
- Authentication and authorization
- Data privacy compliance

## Performance Considerations

### Audio Latency Optimization
- Target: <500ms end-to-end latency
- Audio chunk size: 64ms (1024 bytes at 16kHz)
- WebSocket message batching
- Predictive audio buffering

### Scalability Design
- Session-based architecture for multiple concurrent users
- Efficient memory management for audio buffers
- Connection pooling for Google Cloud APIs
- Horizontal scaling capabilities

### Resource Management
- Audio buffer size limits
- Session timeout handling
- Memory cleanup for ended sessions
- CPU usage monitoring

## Security Architecture

### Authentication Flow
1. Google Cloud service account authentication
2. Session-based user identification
3. WebSocket connection validation
4. API rate limiting and quotas

### Code Execution Security
1. **Immediate (MVP) Approach**:
   - Basic subprocess execution with timeout
   - Output sanitization
   - Resource monitoring
   - Security warnings in logs

2. **Future Enhancement**:
   - Docker-based sandboxing
   - Restricted Python interpreter
   - File system isolation
   - Network access controls

### Data Privacy
- Voice data encryption in transit
- Temporary audio storage only
- Conversation context cleanup
- GDPR compliance considerations

## Deployment Architecture

### Development Environment
- Local ADK-MCP server with Google Cloud credentials
- Web client served from local server
- Android emulator for mobile testing
- Real Google Cloud services (no mocking possible)

### Production Considerations
- HTTPS/WSS for secure connections
- Load balancing for multiple instances
- Audio CDN for global performance
- Monitoring and alerting systems

## Migration from Current System

### Phase 1: Voice Foundation
- Add voice streaming endpoints to existing server
- Implement basic Google ADK-Web integration
- Create minimal web client with voice capabilities

### Phase 2: Enhanced Features
- Add interruption handling
- Implement conversation context management
- Enhance code execution with voice integration

### Phase 3: Production Readiness
- Add comprehensive security measures
- Implement monitoring and logging
- Optimize performance and scalability
- Add Android WebView wrapper

## Technology Stack

### Backend
- **Framework**: FastAPI (existing)
- **WebSocket**: FastAPI WebSocket support
- **Google Integration**: google-adk Python package
- **Audio Processing**: PyAudio, wave libraries
- **Code Execution**: subprocess (MVP), Docker (future)

### Frontend
- **Web**: Vanilla JavaScript with Web Audio API
- **Mobile**: Android WebView with native permissions
- **Audio**: AudioWorklet for low-latency processing
- **Communication**: WebSocket API

### Infrastructure
- **Cloud**: Google Cloud Platform
- **APIs**: Vertex AI, Live API, Speech APIs
- **Authentication**: Service Account credentials
- **Model**: gemini-2.5-pro