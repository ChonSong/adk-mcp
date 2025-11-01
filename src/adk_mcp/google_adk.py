"""Google ADK-Web integration for ADK-MCP."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid

from google.cloud import aiplatform
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
import requests

from .streaming import StreamMessage, StreamHandler


@dataclass
class ADKWebConfig:
    """Configuration for Google ADK-Web integration."""
    
    project_id: str
    location: str = "us-central1"
    credentials_path: Optional[str] = None
    model_name: str = "gemini-1.5-pro"
    enable_streaming: bool = True
    max_tokens: int = 1000
    temperature: float = 0.7


@dataclass
class ConversationContext:
    """Context for ongoing conversation."""
    
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.metadata is None:
            self.metadata = {}


class GoogleADKWebAgent:
    """Google ADK-Web agent implementation."""
    
    def __init__(self, config: ADKWebConfig):
        """
        Initialize Google ADK-Web agent.
        
        Args:
            config: ADK-Web configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._model = None
        self.active_sessions: Dict[str, ConversationContext] = {}
        
    async def initialize(self):
        """Initialize Google Cloud AI Platform client."""
        try:
            # Initialize credentials
            if self.config.credentials_path:
                import os
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.credentials_path
            
            # Initialize AI Platform
            aiplatform.init(
                project=self.config.project_id,
                location=self.config.location
            )
            
            # Initialize the model
            from vertexai.generative_models import GenerativeModel
            self._model = GenerativeModel(self.config.model_name)
            
            self.logger.info(f"Google ADK-Web agent initialized with model: {self.config.model_name}")
            
        except DefaultCredentialsError:
            self.logger.warning("Google Cloud credentials not found, using mock mode")
            self._model = None
        except Exception as e:
            self.logger.error(f"Failed to initialize Google ADK-Web: {e}")
            self._model = None
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """
        Create a new conversation session.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = ConversationContext(
            session_id=session_id,
            user_id=user_id
        )
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation session by ID."""
        return self.active_sessions.get(session_id)
    
    def close_session(self, session_id: str):
        """Close and remove conversation session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    async def process_message(
        self, 
        message: str, 
        session_id: str,
        message_type: str = "text"
    ) -> StreamMessage:
        """
        Process a message using Google ADK-Web.
        
        Args:
            message: Input message
            session_id: Conversation session ID
            message_type: Type of message
            
        Returns:
            StreamMessage with response
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        try:
            # Add user message to history
            session.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Generate response
            if self._model:
                response_text = await self._generate_with_vertex_ai(message, session)
            else:
                response_text = await self._generate_mock_response(message, session)
            
            # Add assistant response to history
            session.conversation_history.append({
                "role": "assistant", 
                "content": response_text,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Create response message
            response_message = StreamMessage(
                id=str(uuid.uuid4()),
                content=response_text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                message_type=message_type,
                metadata={
                    "session_id": session_id,
                    "model": self.config.model_name,
                    "conversation_length": len(session.conversation_history)
                }
            )
            
            return response_message
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return StreamMessage(
                id=str(uuid.uuid4()),
                content=f"Sorry, I encountered an error: {str(e)}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                message_type="error",
                metadata={"session_id": session_id, "error": str(e)}
            )
    
    async def _generate_with_vertex_ai(
        self, 
        message: str, 
        session: ConversationContext
    ) -> str:
        """Generate response using Vertex AI."""
        try:
            # Build conversation context
            context = self._build_conversation_context(session)
            full_prompt = f"{context}\n\nUser: {message}\nAssistant:"
            
            # Generate response
            response = await asyncio.to_thread(
                self._model.generate_content,
                full_prompt,
                generation_config={
                    "max_output_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                }
            )
            
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Vertex AI generation error: {e}")
            return "I'm having trouble generating a response right now."
    
    async def _generate_mock_response(
        self, 
        message: str, 
        session: ConversationContext
    ) -> str:
        """Generate mock response when Vertex AI is not available."""
        mock_responses = [
            f"I understand you said: '{message}'. This is a mock response from ADK-Web.",
            f"Thanks for your message about '{message[:50]}...'. I'm running in mock mode.",
            f"I received your message: '{message}'. Google ADK-Web would process this in production.",
            f"Your message '{message}' has been processed. This is a simulated ADK-Web response."
        ]
        
        import random
        return random.choice(mock_responses)
    
    def _build_conversation_context(self, session: ConversationContext) -> str:
        """Build conversation context from history."""
        if not session.conversation_history:
            return "You are a helpful AI assistant powered by Google ADK-Web."
        
        context_parts = ["You are a helpful AI assistant powered by Google ADK-Web.\n\nConversation history:"]
        
        # Include last 10 messages for context
        recent_history = session.conversation_history[-10:]
        for msg in recent_history:
            role = msg["role"].title()
            content = msg["content"]
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    async def stream_response(
        self, 
        message: str, 
        session_id: str,
        callback: Callable[[str], None]
    ):
        """
        Stream response generation (for real-time typing effect).
        
        Args:
            message: Input message
            session_id: Session ID
            callback: Function to call with each chunk
        """
        if not self.config.enable_streaming:
            response = await self.process_message(message, session_id)
            callback(response.content)
            return
        
        # For now, simulate streaming by chunking the response
        response = await self.process_message(message, session_id)
        words = response.content.split()
        
        for i, word in enumerate(words):
            if i == 0:
                chunk = word
            else:
                chunk = f" {word}"
            
            callback(chunk)
            await asyncio.sleep(0.1)  # Simulate typing delay


class ADKWebStreamHandler(StreamHandler):
    """Stream handler integrated with Google ADK-Web."""
    
    def __init__(self, adk_agent: GoogleADKWebAgent):
        super().__init__()
        self.adk_agent = adk_agent
        self.register_handler("text", self._handle_text_message)
        self.register_handler("start_session", self._handle_start_session)
        self.register_handler("end_session", self._handle_end_session)
    
    async def _handle_text_message(self, message: StreamMessage) -> StreamMessage:
        """Handle text messages with ADK-Web."""
        session_id = message.metadata.get("session_id") if message.metadata else None
        
        if not session_id:
            # Create new session if none provided
            session_id = self.adk_agent.create_session()
        
        return await self.adk_agent.process_message(
            message.content, 
            session_id, 
            message.message_type
        )
    
    async def _handle_start_session(self, message: StreamMessage) -> StreamMessage:
        """Handle session start requests."""
        user_id = message.metadata.get("user_id") if message.metadata else None
        session_id = self.adk_agent.create_session(user_id)
        
        return StreamMessage(
            id=str(uuid.uuid4()),
            content=f"Session started: {session_id}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            message_type="session_start",
            metadata={"session_id": session_id}
        )
    
    async def _handle_end_session(self, message: StreamMessage) -> StreamMessage:
        """Handle session end requests."""
        session_id = message.metadata.get("session_id") if message.metadata else None
        
        if session_id:
            self.adk_agent.close_session(session_id)
            return StreamMessage(
                id=str(uuid.uuid4()),
                content=f"Session ended: {session_id}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                message_type="session_end",
                metadata={"session_id": session_id}
            )
        else:
            return StreamMessage(
                id=str(uuid.uuid4()),
                content="No session to end",
                timestamp=datetime.now(timezone.utc).isoformat(),
                message_type="error",
                metadata={"error": "No session_id provided"}
            )


# Configuration helper
def create_adk_config_from_env() -> ADKWebConfig:
    """Create ADK-Web config from environment variables."""
    import os
    
    return ADKWebConfig(
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        model_name=os.getenv("ADK_MODEL_NAME", "gemini-1.5-pro"),
        enable_streaming=os.getenv("ADK_ENABLE_STREAMING", "true").lower() == "true",
        max_tokens=int(os.getenv("ADK_MAX_TOKENS", "1000")),
        temperature=float(os.getenv("ADK_TEMPERATURE", "0.7"))
    )