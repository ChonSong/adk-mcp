"""Google Live API integration for real-time speech processing."""

import asyncio
import json
import logging
import wave
import io
from typing import Dict, Any, Optional, AsyncIterator, Callable
from datetime import datetime, timezone

try:
    from google_adk import run_live, LiveRequestQueue
    from google.cloud import aiplatform
    from vertexai.generative_models import GenerativeModel
    ADK_LIVE_AVAILABLE = True
except ImportError:
    ADK_LIVE_AVAILABLE = False
    logging.warning("Google ADK Live API not available")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logging.warning("PyAudio not available for audio processing")

from .voice_streaming import AudioChunk, VoiceMessage
# Remove circular import - will use TYPE_CHECKING for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adk_voice_agent import EnhancedVoiceSession


class AudioFormatConverter:
    """Utility class for audio format conversion."""
    
    @staticmethod
    def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, bit_depth: int = 16) -> bytes:
        """Convert PCM data to WAV format."""
        try:
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(bit_depth // 8)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_data)
            
            wav_buffer.seek(0)
            return wav_buffer.read()
            
        except Exception as e:
            logging.error(f"Error converting PCM to WAV: {e}")
            return pcm_data
    
    @staticmethod
    def wav_to_pcm(wav_data: bytes) -> tuple[bytes, int, int, int]:
        """Convert WAV data to PCM and extract format info."""
        try:
            wav_buffer = io.BytesIO(wav_data)
            
            with wave.open(wav_buffer, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_rate = wav_file.getframerate()
                bit_depth = wav_file.getsampwidth() * 8
                pcm_data = wav_file.readframes(wav_file.getnframes())
            
            return pcm_data, sample_rate, channels, bit_depth
            
        except Exception as e:
            logging.error(f"Error converting WAV to PCM: {e}")
            return wav_data, 16000, 1, 16
    
    @staticmethod
    def resample_audio(audio_data: bytes, from_rate: int, to_rate: int, channels: int = 1) -> bytes:
        """Resample audio data (basic implementation)."""
        if from_rate == to_rate:
            return audio_data
        
        # Simple resampling by dropping/duplicating samples
        # For production, use a proper resampling library like librosa
        ratio = to_rate / from_rate
        
        if ratio > 1:
            # Upsample by duplicating samples
            result = bytearray()
            for i in range(0, len(audio_data), 2):  # Assuming 16-bit samples
                sample = audio_data[i:i+2]
                for _ in range(int(ratio)):
                    result.extend(sample)
            return bytes(result)
        else:
            # Downsample by dropping samples
            step = int(1 / ratio)
            result = bytearray()
            for i in range(0, len(audio_data), step * 2):  # Assuming 16-bit samples
                result.extend(audio_data[i:i+2])
            return bytes(result)


class LiveRequestQueue:
    """Manages real-time requests to Google Live API."""
    
    def __init__(self, session_id: str, config=None):
        self.session_id = session_id
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.audio_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()
        self.is_active = False
        self._tasks = []
        self.live_model = None
        self.live_session = None
    
    async def start(self):
        """Start the Live API session."""
        if not ADK_LIVE_AVAILABLE:
            self.logger.warning("Live API not available, using mock implementation")
            self.is_active = True
            return
        
        try:
            # Initialize Live API connection with gemini-2.5-pro
            if self.config:
                # Initialize AI Platform if not already done
                aiplatform.init(
                    project=self.config.project_id,
                    location=self.config.location
                )
                
                # Initialize Live API model (gemini-2.5-pro for Live API)
                self.live_model = GenerativeModel("gemini-2.5-pro")
                
                # Start Live API session
                self.live_session = await asyncio.to_thread(
                    run_live,
                    model=self.live_model,
                    session_id=self.session_id
                )
                
                self.logger.info(f"Started Live API session with gemini-2.5-pro: {self.session_id}")
            else:
                self.logger.warning("No config provided, using mock Live API")
            
            self.is_active = True
            
        except Exception as e:
            self.logger.error(f"Failed to start Live API session: {e}")
            self.logger.info("Falling back to mock implementation")
            self.is_active = True
    
    async def stop(self):
        """Stop the Live API session."""
        self.is_active = False
        
        # Stop Live API session
        if self.live_session and ADK_LIVE_AVAILABLE:
            try:
                await asyncio.to_thread(self.live_session.close)
                self.logger.info(f"Closed Live API session: {self.session_id}")
            except Exception as e:
                self.logger.error(f"Error closing Live API session: {e}")
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Clear queues
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        self.live_model = None
        self.live_session = None
        self.logger.info(f"Stopped Live API session: {self.session_id}")
    
    async def send_audio_chunk(self, audio: bytes):
        """Send audio chunk to Live API."""
        if not self.is_active:
            return
        
        try:
            await self.audio_queue.put(audio)
            self.logger.debug(f"Queued audio chunk: {len(audio)} bytes")
        except Exception as e:
            self.logger.error(f"Error sending audio chunk: {e}")
    
    async def receive_transcription(self) -> Optional[str]:
        """Receive transcription from Live API."""
        if not self.is_active:
            return None
        
        try:
            if self.live_session and ADK_LIVE_AVAILABLE:
                # Real Live API transcription
                if not self.audio_queue.empty():
                    audio_data = await self.audio_queue.get()
                    
                    # Send audio to Live API for transcription
                    transcription = await asyncio.to_thread(
                        self.live_session.send_audio,
                        audio_data
                    )
                    
                    if transcription:
                        self.logger.debug(f"Live API transcription: {transcription[:50]}...")
                        return transcription
                    
                return None
            else:
                # Mock transcription fallback
                if not self.audio_queue.empty():
                    audio_data = await self.audio_queue.get()
                    return f"[Mock transcription of {len(audio_data)} bytes audio]"
                return None
            
        except Exception as e:
            self.logger.error(f"Error receiving transcription: {e}")
            return None
    
    async def send_text_response(self, text: str):
        """Send text response to Live API for TTS."""
        if not self.is_active:
            return
        
        try:
            await self.response_queue.put(text)
            self.logger.debug(f"Queued text response: {text[:50]}...")
        except Exception as e:
            self.logger.error(f"Error sending text response: {e}")
    
    async def receive_audio_response(self) -> AsyncIterator[bytes]:
        """Receive audio response from Live API."""
        if not self.is_active:
            return
        
        try:
            while self.is_active:
                if not self.response_queue.empty():
                    text = await self.response_queue.get()
                    
                    if self.live_session and ADK_LIVE_AVAILABLE:
                        # Real Live API TTS
                        try:
                            audio_stream = await asyncio.to_thread(
                                self.live_session.generate_speech,
                                text
                            )
                            
                            # Stream audio chunks
                            async for audio_chunk in audio_stream:
                                if audio_chunk:
                                    yield audio_chunk
                                    
                        except Exception as e:
                            self.logger.error(f"Live API TTS error: {e}")
                            # Fallback to mock audio
                            mock_audio = self._generate_mock_audio(text)
                            yield mock_audio
                    else:
                        # Mock TTS - generate silence for now
                        mock_audio = self._generate_mock_audio(text)
                        yield mock_audio
                
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Error receiving audio response: {e}")
    
    def _generate_mock_audio(self, text: str) -> bytes:
        """Generate mock audio for text (silence)."""
        # Generate 1 second of silence at 16kHz, 16-bit, mono
        duration_seconds = min(len(text) * 0.1, 5.0)  # Max 5 seconds
        sample_rate = 16000
        samples = int(duration_seconds * sample_rate)
        
        # Generate silence (zeros)
        return b'\x00\x00' * samples


class LiveAPIManager:
    """Manages Live API sessions and processing."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, LiveRequestQueue] = {}
        self.format_converter = AudioFormatConverter()
    
    async def create_live_session(self, session_id: str) -> LiveRequestQueue:
        """Create new Live API session."""
        if session_id in self.active_sessions:
            await self.close_live_session(session_id)
        
        live_queue = LiveRequestQueue(session_id, self.config)
        await live_queue.start()
        
        self.active_sessions[session_id] = live_queue
        self.logger.info(f"Created Live API session: {session_id}")
        
        return live_queue
    
    async def get_live_session(self, session_id: str) -> Optional[LiveRequestQueue]:
        """Get existing Live API session."""
        return self.active_sessions.get(session_id)
    
    async def close_live_session(self, session_id: str):
        """Close Live API session."""
        if session_id in self.active_sessions:
            live_queue = self.active_sessions[session_id]
            await live_queue.stop()
            del self.active_sessions[session_id]
            self.logger.info(f"Closed Live API session: {session_id}")
    
    async def process_audio_for_transcription(
        self, 
        audio_chunk: AudioChunk, 
        session_id: str
    ) -> Optional[str]:
        """Process audio chunk for speech-to-text."""
        live_session = await self.get_live_session(session_id)
        if not live_session:
            return None
        
        try:
            # Convert audio format if needed
            processed_audio = self._preprocess_audio(audio_chunk)
            
            # Send to Live API
            await live_session.send_audio_chunk(processed_audio)
            
            # Get transcription
            transcription = await live_session.receive_transcription()
            
            if transcription:
                self.logger.debug(f"Transcription received: {transcription[:50]}...")
            
            return transcription
            
        except Exception as e:
            self.logger.error(f"Error processing audio for transcription: {e}")
            return None
    
    async def generate_speech_from_text(
        self, 
        text: str, 
        session_id: str
    ) -> AsyncIterator[bytes]:
        """Generate speech audio from text."""
        live_session = await self.get_live_session(session_id)
        if not live_session:
            return
        
        try:
            # Send text to Live API
            await live_session.send_text_response(text)
            
            # Stream audio response
            async for audio_chunk in live_session.receive_audio_response():
                if audio_chunk:
                    # Post-process audio if needed
                    processed_audio = self._postprocess_audio(audio_chunk)
                    yield processed_audio
                    
        except Exception as e:
            self.logger.error(f"Error generating speech from text: {e}")
    
    def _preprocess_audio(self, audio_chunk: AudioChunk) -> bytes:
        """Preprocess audio for Live API."""
        audio_data = audio_chunk.data
        
        # Ensure correct format for Live API (16kHz, 16-bit, mono)
        if audio_chunk.sample_rate != 16000:
            audio_data = self.format_converter.resample_audio(
                audio_data, 
                audio_chunk.sample_rate, 
                16000, 
                audio_chunk.channels
            )
        
        return audio_data
    
    def _postprocess_audio(self, audio_data: bytes) -> bytes:
        """Post-process audio from Live API."""
        # Apply any necessary post-processing
        return audio_data
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get Live API session statistics."""
        return {
            "active_sessions": len(self.active_sessions),
            "sessions": list(self.active_sessions.keys())
        }


class SpeechProcessor:
    """High-level speech processing interface."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.live_api_manager = LiveAPIManager(config)
        self.processing_tasks: Dict[str, asyncio.Task] = {}
    
    async def start_speech_processing(self, session: 'EnhancedVoiceSession'):
        """Start speech processing for a session."""
        session_id = session.session_id
        
        # Create Live API session
        live_queue = await self.live_api_manager.create_live_session(session_id)
        session.google_live_session = live_queue
        
        # Start processing task
        task = asyncio.create_task(self._process_speech_loop(session))
        self.processing_tasks[session_id] = task
        
        await session.log_event("speech_processing_started", {"session_id": session_id})
        self.logger.info(f"Started speech processing for session: {session_id}")
    
    async def stop_speech_processing(self, session: 'EnhancedVoiceSession'):
        """Stop speech processing for a session."""
        session_id = session.session_id
        
        # Cancel processing task
        if session_id in self.processing_tasks:
            task = self.processing_tasks[session_id]
            if not task.done():
                task.cancel()
            del self.processing_tasks[session_id]
        
        # Close Live API session
        await self.live_api_manager.close_live_session(session_id)
        session.google_live_session = None
        
        await session.log_event("speech_processing_stopped", {"session_id": session_id})
        self.logger.info(f"Stopped speech processing for session: {session_id}")
    
    async def process_audio_chunk(
        self, 
        audio_chunk: AudioChunk, 
        session: 'EnhancedVoiceSession'
    ) -> Optional[str]:
        """Process single audio chunk."""
        return await self.live_api_manager.process_audio_for_transcription(
            audio_chunk, 
            session.session_id
        )
    
    async def generate_speech_response(
        self, 
        text: str, 
        session: 'EnhancedVoiceSession'
    ) -> AsyncIterator[bytes]:
        """Generate speech response from text."""
        async for audio_chunk in self.live_api_manager.generate_speech_from_text(
            text, 
            session.session_id
        ):
            yield audio_chunk
    
    async def _process_speech_loop(self, session: 'EnhancedVoiceSession'):
        """Main speech processing loop for a session."""
        try:
            while session.google_live_session and session.google_live_session.is_active:
                # Process any pending audio chunks
                if session.audio_buffer:
                    audio_data = await session.audio_buffer.get_audio_data(1024)  # Get 1KB chunks
                    
                    if audio_data:
                        # Create audio chunk
                        chunk = AudioChunk(
                            data=audio_data,
                            timestamp=datetime.now(timezone.utc),
                            sequence_number=await session.get_next_sequence_number()
                        )
                        
                        # Process for transcription
                        transcription = await self.process_audio_chunk(chunk, session)
                        
                        if transcription:
                            # Add to conversation history
                            voice_message = VoiceMessage(
                                role="user",
                                content=transcription,
                                audio_data=audio_data,
                                message_type="voice"
                            )
                            await session.add_message(voice_message)
                            
                            await session.log_event("transcription_received", {
                                "transcription": transcription,
                                "audio_size": len(audio_data)
                            })
                
                await asyncio.sleep(0.1)  # Process every 100ms
                
        except asyncio.CancelledError:
            self.logger.info(f"Speech processing cancelled for session: {session.session_id}")
        except Exception as e:
            self.logger.error(f"Error in speech processing loop: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get speech processing statistics."""
        return {
            "active_processing_tasks": len(self.processing_tasks),
            "live_api_stats": self.live_api_manager.get_session_stats()
        }