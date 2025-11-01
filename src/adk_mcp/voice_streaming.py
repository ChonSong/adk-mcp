"""Voice streaming components for ADK-MCP."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any, AsyncIterator, Callable
from aiohttp import web
import websockets
from websockets.server import WebSocketServerProtocol

from .streaming import StreamMessage


@dataclass
class AudioChunk:
    """Represents an audio chunk for streaming."""
    
    data: bytes
    timestamp: datetime
    sequence_number: int
    sample_rate: int = 16000
    channels: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "data": self.data.hex(),  # Convert bytes to hex string
            "timestamp": self.timestamp.isoformat(),
            "sequence_number": self.sequence_number,
            "sample_rate": self.sample_rate,
            "channels": self.channels
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioChunk':
        """Create from dictionary."""
        return cls(
            data=bytes.fromhex(data["data"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sequence_number=data["sequence_number"],
            sample_rate=data.get("sample_rate", 16000),
            channels=data.get("channels", 1)
        )


@dataclass
class VoiceMessage:
    """Voice message in conversation history."""
    
    role: str  # "user" or "assistant"
    content: str
    audio_data: Optional[bytes] = None
    timestamp: datetime = None
    message_type: str = "voice"  # "voice", "code_request", "code_result"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "audio_data": self.audio_data.hex() if self.audio_data else None,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type
        }


class AudioBuffer:
    """Buffer for managing audio chunks."""
    
    def __init__(self, max_size: int = 1024 * 1024):  # 1MB default
        self.max_size = max_size
        self.buffer = bytearray()
        self.chunks: list[AudioChunk] = []
        self._lock = asyncio.Lock()
    
    async def add_chunk(self, chunk: AudioChunk):
        """Add audio chunk to buffer."""
        async with self._lock:
            self.buffer.extend(chunk.data)
            self.chunks.append(chunk)
            
            # Trim buffer if too large
            while len(self.buffer) > self.max_size and self.chunks:
                old_chunk = self.chunks.pop(0)
                self.buffer = self.buffer[len(old_chunk.data):]
    
    async def get_audio_data(self, max_length: Optional[int] = None) -> bytes:
        """Get audio data from buffer."""
        async with self._lock:
            if max_length is None:
                return bytes(self.buffer)
            return bytes(self.buffer[:max_length])
    
    async def clear(self):
        """Clear the buffer."""
        async with self._lock:
            self.buffer.clear()
            self.chunks.clear()


class VoiceSession:
    """Represents an active voice conversation session."""
    
    def __init__(
        self,
        session_id: str,
        websocket: WebSocketServerProtocol,
        user_id: Optional[str] = None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.websocket = websocket
        self.audio_buffer = AudioBuffer()
        self.is_speaking = False
        self.is_listening = False
        self.last_activity = datetime.now(timezone.utc)
        self.conversation_history: list[VoiceMessage] = []
        self.google_live_session = None
        self.sequence_number = 0
        self._lock = asyncio.Lock()
    
    async def add_message(self, message: VoiceMessage):
        """Add message to conversation history."""
        async with self._lock:
            self.conversation_history.append(message)
            self.last_activity = datetime.now(timezone.utc)
    
    async def get_next_sequence_number(self) -> int:
        """Get next sequence number for audio chunks."""
        async with self._lock:
            self.sequence_number += 1
            return self.sequence_number
    
    async def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "is_speaking": self.is_speaking,
            "is_listening": self.is_listening,
            "last_activity": self.last_activity.isoformat(),
            "conversation_length": len(self.conversation_history)
        }


class VoiceStreamManager:
    """Manages voice streaming sessions and audio processing."""
    
    def __init__(self):
        self.active_sessions: Dict[str, VoiceSession] = {}
        self.logger = logging.getLogger(__name__)
        self._cleanup_task = None
    
    async def start_voice_session(
        self, 
        websocket: WebSocketServerProtocol,
        user_id: Optional[str] = None
    ) -> VoiceSession:
        """Start a new voice session."""
        session_id = str(uuid.uuid4())
        session = VoiceSession(session_id, websocket, user_id)
        
        self.active_sessions[session_id] = session
        self.logger.info(f"Started voice session: {session_id}")
        
        # Start cleanup task if not running
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_sessions())
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Get voice session by ID."""
        return self.active_sessions.get(session_id)
    
    async def process_audio_chunk(
        self, 
        audio_data: bytes, 
        session: VoiceSession
    ) -> AudioChunk:
        """Process incoming audio chunk."""
        await session.update_activity()
        
        # Create audio chunk
        sequence_number = await session.get_next_sequence_number()
        chunk = AudioChunk(
            data=audio_data,
            timestamp=datetime.now(timezone.utc),
            sequence_number=sequence_number
        )
        
        # Add to session buffer
        await session.audio_buffer.add_chunk(chunk)
        
        self.logger.debug(
            f"Processed audio chunk for session {session.session_id}: "
            f"{len(audio_data)} bytes, seq {sequence_number}"
        )
        
        return chunk
    
    async def handle_interruption(self, session: VoiceSession):
        """Handle voice interruption during AI speech."""
        if session.is_speaking:
            session.is_speaking = False
            self.logger.info(f"Voice interruption detected in session {session.session_id}")
            
            # Send interruption signal to client
            interruption_message = {
                "type": "interruption",
                "session_id": session.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                await session.websocket.send(json.dumps(interruption_message))
            except Exception as e:
                self.logger.error(f"Failed to send interruption signal: {e}")
    
    async def end_voice_session(self, session: VoiceSession):
        """End a voice session and cleanup resources."""
        session_id = session.session_id
        
        # Cleanup session resources
        await session.audio_buffer.clear()
        session.conversation_history.clear()
        
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        self.logger.info(f"Ended voice session: {session_id}")
    
    async def _cleanup_sessions(self):
        """Background task to cleanup inactive sessions."""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                timeout_threshold = 30 * 60  # 30 minutes
                
                sessions_to_remove = []
                for session_id, session in self.active_sessions.items():
                    time_diff = (current_time - session.last_activity).total_seconds()
                    if time_diff > timeout_threshold:
                        sessions_to_remove.append(session)
                
                # Cleanup timed out sessions
                for session in sessions_to_remove:
                    await self.end_voice_session(session)
                    self.logger.info(f"Cleaned up inactive session: {session.session_id}")
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions."""
        return {
            "active_sessions": len(self.active_sessions),
            "sessions": [session.to_dict() for session in self.active_sessions.values()]
        }


class VoiceWebSocketHandler:
    """WebSocket handler for voice streaming."""
    
    def __init__(self, voice_manager: VoiceStreamManager):
        self.voice_manager = voice_manager
        self.logger = logging.getLogger(__name__)
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection for voice streaming."""
        session = None
        
        try:
            # Start voice session
            session = await self.voice_manager.start_voice_session(websocket)
            
            # Send session started message
            start_message = {
                "type": "session_started",
                "session_id": session.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(start_message))
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(message, session)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Voice WebSocket connection closed for session {session.session_id if session else 'unknown'}")
        except Exception as e:
            self.logger.error(f"Error in voice WebSocket handler: {e}")
        finally:
            if session:
                await self.voice_manager.end_voice_session(session)
    
    async def _handle_message(self, message: str, session: VoiceSession):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "audio_chunk":
                await self._handle_audio_chunk(data, session)
            elif message_type == "start_listening":
                await self._handle_start_listening(session)
            elif message_type == "stop_listening":
                await self._handle_stop_listening(session)
            elif message_type == "interruption":
                await self.voice_manager.handle_interruption(session)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in WebSocket message: {e}")
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_audio_chunk(self, data: Dict[str, Any], session: VoiceSession):
        """Handle incoming audio chunk."""
        try:
            # Extract audio data
            audio_hex = data.get("audio_data", "")
            audio_bytes = bytes.fromhex(audio_hex)
            
            # Process audio chunk
            chunk = await self.voice_manager.process_audio_chunk(audio_bytes, session)
            
            # Send acknowledgment
            ack_message = {
                "type": "audio_chunk_ack",
                "session_id": session.session_id,
                "sequence_number": chunk.sequence_number,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await session.websocket.send(json.dumps(ack_message))
            
        except Exception as e:
            self.logger.error(f"Error handling audio chunk: {e}")
    
    async def _handle_start_listening(self, session: VoiceSession):
        """Handle start listening request."""
        session.is_listening = True
        await session.update_activity()
        
        response = {
            "type": "listening_started",
            "session_id": session.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await session.websocket.send(json.dumps(response))
    
    async def _handle_stop_listening(self, session: VoiceSession):
        """Handle stop listening request."""
        session.is_listening = False
        await session.update_activity()
        
        response = {
            "type": "listening_stopped",
            "session_id": session.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await session.websocket.send(json.dumps(response))


# Audio processing utilities
def validate_audio_format(sample_rate: int, channels: int, bit_depth: int = 16) -> bool:
    """Validate audio format parameters."""
    return (
        sample_rate in [8000, 16000, 22050, 44100, 48000] and
        channels in [1, 2] and
        bit_depth in [8, 16, 24, 32]
    )


def calculate_chunk_duration(chunk_size: int, sample_rate: int, channels: int, bit_depth: int = 16) -> float:
    """Calculate duration of audio chunk in seconds."""
    bytes_per_sample = bit_depth // 8
    samples_per_chunk = chunk_size // (channels * bytes_per_sample)
    return samples_per_chunk / sample_rate


def get_optimal_chunk_size(target_duration_ms: int = 64, sample_rate: int = 16000, channels: int = 1, bit_depth: int = 16) -> int:
    """Calculate optimal chunk size for target duration."""
    bytes_per_sample = bit_depth // 8
    samples_per_second = sample_rate
    target_duration_seconds = target_duration_ms / 1000.0
    
    samples_needed = int(samples_per_second * target_duration_seconds)
    chunk_size = samples_needed * channels * bytes_per_sample
    
    # Round to nearest power of 2 for efficiency
    return 2 ** (chunk_size.bit_length() - 1)