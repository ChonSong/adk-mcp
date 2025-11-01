"""Enhanced Google ADK Voice Agent with Runner.run_live() integration."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, AsyncIterator, Callable
from dataclasses import dataclass, asdict

try:
    from google.adk.agents import LlmAgent
    from google.adk.runtime import Runner, RunConfig
    from google.adk.sessions import SessionService, InMemorySessionService
    from google.adk.tools import BuiltInCodeExecutor, FunctionTool
    from google.adk.artifacts import ArtifactService, InMemoryArtifactService
    ADK_AVAILABLE = True
except ImportError:
    # Fallback for when google-adk is not available
    ADK_AVAILABLE = False
    logging.warning("google-adk package not available, using fallback implementation")

from .google_adk import GoogleADKWebAgent, ADKWebConfig
from .voice_code_executor import VoiceCodeExecutor


@dataclass
class AudioChunk:
    """Represents an audio chunk for streaming."""
    data: bytes
    timestamp: datetime
    sequence_number: int
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class VoiceMessage:
    """Voice message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    audio_data: Optional[bytes] = None
    timestamp: datetime = None
    message_type: str = "voice"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class ADKVoiceSession:
    """Voice session integrated with ADK SessionService."""
    
    def __init__(self, session_id: str, websocket, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.websocket = websocket
        self.adk_session = None
        self.is_speaking = False
        self.is_listening = False
        self.last_activity = datetime.now(timezone.utc)
        self.conversation_history: List[VoiceMessage] = []
        self.sequence_number = 0
        self.runner = None
        self.live_session = None
        
    async def initialize_adk_session(self, session_service: SessionService):
        """Initialize ADK session for persistent context."""
        if ADK_AVAILABLE:
            self.adk_session = await session_service.create_session(self.session_id)
            # Initialize state with user preferences
            if self.user_id:
                self.adk_session.state[f"user:{self.user_id}:preferred_language"] = "python"
        
    async def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log event to session for debugging and context."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        if self.adk_session and ADK_AVAILABLE:
            # Store events in session state
            events = self.adk_session.state.get("events", [])
            events.append(event)
            self.adk_session.state["events"] = events[-50]  # Keep last 50 events
    
    async def add_message(self, message: VoiceMessage):
        """Add message to conversation history."""
        self.conversation_history.append(message)
        self.last_activity = datetime.now(timezone.utc)
        
        # Store in ADK session state
        if self.adk_session and ADK_AVAILABLE:
            messages = self.adk_session.state.get("conversation_history", [])
            messages.append({
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "message_type": message.message_type
            })
            self.adk_session.state["conversation_history"] = messages[-20]  # Keep last 20 messages
    
    async def get_next_sequence_number(self) -> int:
        """Get next sequence number for audio chunks."""
        self.sequence_number += 1
        return self.sequence_number


class VoiceCodeExecutionTool:
    """Voice-aware code execution tool using ADK BuiltInCodeExecutor."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if ADK_AVAILABLE:
            self.code_executor = BuiltInCodeExecutor()
        else:
            self.code_executor = None
    
    @FunctionTool
    async def execute_code_with_voice_response(self, code: str, session_id: str) -> dict:
        """Execute Python code and format results for voice response.
        
        Args:
            code: Python code to execute
            session_id: Current voice session identifier
            
        Returns:
            dict: Execution result with voice-friendly formatting
        """
        try:
            if not self.code_executor:
                return {
                    "status": "error",
                    "output": "Code execution not available",
                    "voice_summary": "Code execution is not available in this environment"
                }
            
            # Execute code using ADK's BuiltInCodeExecutor
            result = await self.code_executor.execute(code)
            
            # Format for voice response
            if result.success:
                voice_summary = self._format_output_for_speech(result.output)
                return {
                    "status": "success",
                    "output": result.output,
                    "voice_summary": voice_summary
                }
            else:
                voice_summary = f"Code execution failed with error: {result.error}"
                return {
                    "status": "error",
                    "output": result.error,
                    "voice_summary": voice_summary
                }
                
        except Exception as e:
            self.logger.error(f"Code execution failed: {e}")
            return {
                "status": "error",
                "output": str(e),
                "voice_summary": f"An error occurred during code execution: {str(e)}"
            }
    
    def _format_output_for_speech(self, output: str) -> str:
        """Format code output for natural speech."""
        if not output or output.strip() == "":
            return "The code executed successfully with no output"
        
        # Limit output length for speech
        if len(output) > 200:
            return f"The code executed successfully. Output: {output[:200]}... and more"
        
        return f"The code executed successfully. Output: {output}"


class ADKLiveRunner:
    """Manages ADK Runner.run_live() sessions for voice streaming."""
    
    def __init__(self, config: ADKWebConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session_service = InMemorySessionService() if ADK_AVAILABLE else None
        self.artifact_service = InMemoryArtifactService() if ADK_AVAILABLE else None
        
        # Initialize voice-enabled agent
        if ADK_AVAILABLE:
            self.voice_agent = self._create_voice_agent()
            self.runner = Runner(agent=self.voice_agent)
        else:
            self.voice_agent = None
            self.runner = None
    
    def _create_voice_agent(self) -> LlmAgent:
        """Create LlmAgent with voice capabilities and code execution."""
        if not ADK_AVAILABLE:
            return None
        
        # Create voice-aware code execution tool
        code_tool = VoiceCodeExecutionTool()
        
        # Create the main voice agent
        agent = LlmAgent(
            name="voice_assistant",
            model="gemini-2.5-pro",
            instruction="""You are a voice-enabled AI assistant specialized in Android development.
            
            You can:
            - Execute Python code using the execute_code_with_voice_response tool
            - Provide Android development guidance and troubleshooting
            - Maintain conversation context across voice interactions
            
            When users ask you to run code, use the execute_code_with_voice_response tool.
            Always provide clear, concise responses suitable for voice interaction.
            Keep responses under 200 words when possible for better voice experience.""",
            tools=[code_tool.execute_code_with_voice_response]
        )
        
        return agent
    
    async def start_live_session(self, session: ADKVoiceSession) -> bool:
        """Start ADK Runner.run_live() session."""
        if not ADK_AVAILABLE or not self.runner:
            self.logger.warning("ADK not available, cannot start live session")
            return False
        
        try:
            # Initialize ADK session
            await session.initialize_adk_session(self.session_service)
            
            # Configure RunConfig for BIDI streaming with AUDIO modality
            run_config = RunConfig(
                streaming_mode="BIDI",
                response_modalities=["TEXT", "AUDIO"],
                speech_config={
                    "voice": "en-US-Standard-A",
                    "language_code": "en-US"
                },
                max_llm_calls=100,  # Cost governance
                save_input_blobs_as_artifacts=True
            )
            
            # Start live session
            session.live_session = await self.runner.run_live(
                session=session.adk_session,
                config=run_config
            )
            
            await session.log_event("live_session_started", {
                "session_id": session.session_id,
                "streaming_mode": "BIDI",
                "response_modalities": ["TEXT", "AUDIO"]
            })
            
            self.logger.info(f"Started ADK live session: {session.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start live session: {e}")
            await session.log_event("live_session_error", {"error": str(e)})
            return False
    
    async def process_audio_chunk(self, session: ADKVoiceSession, audio_chunk: AudioChunk) -> Optional[str]:
        """Process audio chunk through ADK LiveRequestQueue."""
        if not session.live_session:
            return None
        
        try:
            # Send audio to LiveRequestQueue
            await session.live_session.send_audio(audio_chunk.data)
            
            # Check for transcription
            transcription = await session.live_session.get_transcription()
            
            if transcription:
                await session.log_event("transcription_received", {
                    "transcription": transcription,
                    "audio_size": len(audio_chunk.data)
                })
                
                # Add to conversation history
                voice_message = VoiceMessage(
                    role="user",
                    content=transcription,
                    audio_data=audio_chunk.data
                )
                await session.add_message(voice_message)
            
            return transcription
            
        except Exception as e:
            self.logger.error(f"Error processing audio chunk: {e}")
            return None
    
    async def generate_response(self, session: ADKVoiceSession, text: str) -> AsyncIterator[bytes]:
        """Generate voice response using ADK's AUDIO modality."""
        if not session.live_session:
            return
        
        try:
            # Send text to agent for processing
            response = await session.live_session.send_message(text)
            
            # Add assistant response to conversation history
            voice_message = VoiceMessage(
                role="assistant",
                content=response.text if hasattr(response, 'text') else str(response)
            )
            await session.add_message(voice_message)
            
            # Stream audio response
            if hasattr(response, 'audio_stream'):
                async for audio_chunk in response.audio_stream:
                    if audio_chunk:
                        yield audio_chunk
            else:
                # Fallback: generate mock audio
                yield self._generate_mock_audio(str(response))
                
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            yield self._generate_mock_audio("I encountered an error processing your request.")
    
    async def handle_interruption(self, session: ADKVoiceSession):
        """Handle voice interruption using ADK's interruption support."""
        if not session.live_session:
            return
        
        try:
            # Use ADK's graceful stream stopping
            await session.live_session.interrupt()
            session.is_speaking = False
            
            await session.log_event("interruption_handled", {
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error handling interruption: {e}")
    
    async def close_live_session(self, session: ADKVoiceSession):
        """Close ADK live session and cleanup."""
        if session.live_session:
            try:
                await session.live_session.close()
                session.live_session = None
                
                await session.log_event("live_session_closed", {
                    "session_id": session.session_id
                })
                
                self.logger.info(f"Closed ADK live session: {session.session_id}")
                
            except Exception as e:
                self.logger.error(f"Error closing live session: {e}")
    
    def _generate_mock_audio(self, text: str) -> bytes:
        """Generate mock audio for fallback."""
        # Generate 1 second of silence at 16kHz, 16-bit, mono
        duration_seconds = min(len(text) * 0.1, 3.0)  # Max 3 seconds
        sample_rate = 16000
        samples = int(duration_seconds * sample_rate)
        return b'\x00\x00' * samples


class GoogleADKVoiceAgent:
    """Google ADK Voice Agent with Runner.run_live() integration."""
    
    def __init__(self, config: ADKWebConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, ADKVoiceSession] = {}
        
        # Initialize ADK Live Runner
        self.live_runner = ADKLiveRunner(config)
        
        # Voice code executor for fallback
        self.voice_code_executor = VoiceCodeExecutor() if hasattr(self, 'VoiceCodeExecutor') else None
    
    async def initialize(self):
        """Initialize the voice agent."""
        try:
            if ADK_AVAILABLE:
                self.logger.info("Initializing Google ADK Voice Agent with Runner.run_live()")
            else:
                self.logger.warning("ADK not available, using fallback implementation")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize voice agent: {e}")
    
    async def create_voice_session(
        self, 
        websocket, 
        user_id: Optional[str] = None
    ) -> ADKVoiceSession:
        """Create new ADK voice session."""
        session_id = str(uuid.uuid4())
        session = ADKVoiceSession(session_id, websocket, user_id)
        
        # Start ADK live session
        success = await self.live_runner.start_live_session(session)
        if not success:
            self.logger.warning(f"Failed to start live session for {session_id}, using fallback")
        
        self.active_sessions[session_id] = session
        
        self.logger.info(f"Created ADK voice session: {session_id}")
        return session
    
    async def handle_voice_websocket(self, websocket, session: ADKVoiceSession):
        """Handle WebSocket messages for voice streaming."""
        try:
            # Send session started message
            start_message = {
                "type": "session_started",
                "session_id": session.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(start_message))
            
            # Handle incoming messages
            async for message in websocket:
                if message.type == 'text':
                    await self._handle_websocket_message(message.data, session, websocket)
                elif message.type == 'error':
                    self.logger.error(f"WebSocket error: {message.data}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Error in voice WebSocket handler: {e}")
        finally:
            await self.close_voice_session(session)
    
    async def _handle_websocket_message(self, message_data: str, session: ADKVoiceSession, websocket):
        """Handle individual WebSocket message."""
        try:
            data = json.loads(message_data)
            message_type = data.get("type")
            
            if message_type == "audio_chunk":
                await self._handle_audio_chunk(data, session, websocket)
            elif message_type == "start_listening":
                await self._handle_start_listening(session, websocket)
            elif message_type == "stop_listening":
                await self._handle_stop_listening(session, websocket)
            elif message_type == "interruption":
                await self._handle_interruption(session, websocket)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in WebSocket message: {e}")
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_audio_chunk(self, data: Dict[str, Any], session: ADKVoiceSession, websocket):
        """Handle incoming audio chunk."""
        try:
            # Extract audio data
            audio_hex = data.get("audio_data", "")
            audio_bytes = bytes.fromhex(audio_hex)
            sequence_number = data.get("sequence_number", 0)
            
            # Create audio chunk
            audio_chunk = AudioChunk(
                data=audio_bytes,
                timestamp=datetime.now(timezone.utc),
                sequence_number=sequence_number
            )
            
            # Process through ADK LiveRequestQueue
            transcription = await self.live_runner.process_audio_chunk(session, audio_chunk)
            
            # Send acknowledgment
            ack_message = {
                "type": "audio_chunk_ack",
                "session_id": session.session_id,
                "sequence_number": sequence_number,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(ack_message))
            
            # If we got a transcription, generate response
            if transcription:
                await self._send_transcription(transcription, session, websocket)
                await self._generate_and_send_response(transcription, session, websocket)
            
        except Exception as e:
            self.logger.error(f"Error handling audio chunk: {e}")
    
    async def _send_transcription(self, transcription: str, session: ADKVoiceSession, websocket):
        """Send transcription to client."""
        transcription_message = {
            "type": "transcription",
            "text": transcription,
            "session_id": session.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send(json.dumps(transcription_message))
    
    async def _generate_and_send_response(self, text: str, session: ADKVoiceSession, websocket):
        """Generate and send voice response."""
        try:
            session.is_speaking = True
            
            # Generate response using ADK
            response_text = ""
            audio_chunks = []
            
            async for audio_chunk in self.live_runner.generate_response(session, text):
                if audio_chunk:
                    audio_chunks.append(audio_chunk)
            
            # Get the text response from session history
            if session.conversation_history:
                last_message = session.conversation_history[-1]
                if last_message.role == "assistant":
                    response_text = last_message.content
            
            # Send response with audio
            response_message = {
                "type": "response",
                "text": response_text,
                "audio_data": b''.join(audio_chunks).hex() if audio_chunks else None,
                "session_id": session.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(response_message))
            
            session.is_speaking = False
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            session.is_speaking = False
    
    async def _handle_start_listening(self, session: ADKVoiceSession, websocket):
        """Handle start listening request."""
        session.is_listening = True
        
        response = {
            "type": "listening_started",
            "session_id": session.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send(json.dumps(response))
    
    async def _handle_stop_listening(self, session: ADKVoiceSession, websocket):
        """Handle stop listening request."""
        session.is_listening = False
        
        response = {
            "type": "listening_stopped",
            "session_id": session.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send(json.dumps(response))
    
    async def _handle_interruption(self, session: ADKVoiceSession, websocket):
        """Handle voice interruption."""
        await self.live_runner.handle_interruption(session)
        
        response = {
            "type": "interruption_handled",
            "session_id": session.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send(json.dumps(response))
    
    async def close_voice_session(self, session: ADKVoiceSession):
        """Close voice session and cleanup resources."""
        session_id = session.session_id
        
        # Close ADK live session
        await self.live_runner.close_live_session(session)
        
        # Cleanup resources
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        self.logger.info(f"Closed voice session: {session_id}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active voice sessions."""
        return {
            "active_sessions": len(self.active_sessions),
            "adk_available": ADK_AVAILABLE,
            "sessions": [
                {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "is_speaking": session.is_speaking,
                    "is_listening": session.is_listening,
                    "conversation_length": len(session.conversation_history),
                    "last_activity": session.last_activity.isoformat()
                }
                for session in self.active_sessions.values()
            ]
        }