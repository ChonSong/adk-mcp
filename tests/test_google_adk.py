"""Tests for Google ADK-Web integration."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from adk_mcp.google_adk import (
    GoogleADKWebAgent, 
    ADKWebConfig, 
    ADKWebStreamHandler,
    ConversationContext,
    create_adk_config_from_env
)
from adk_mcp.streaming import StreamMessage


class TestADKWebConfig:
    """Test ADK-Web configuration."""
    
    def test_config_creation(self):
        """Test creating ADK-Web config."""
        config = ADKWebConfig(
            project_id="test-project",
            location="us-central1",
            model_name="gemini-1.5-pro"
        )
        
        assert config.project_id == "test-project"
        assert config.location == "us-central1"
        assert config.model_name == "gemini-1.5-pro"
        assert config.enable_streaming is True
        assert config.max_tokens == 1000
        assert config.temperature == 0.7
    
    @patch.dict('os.environ', {
        'GOOGLE_CLOUD_PROJECT': 'env-project',
        'GOOGLE_CLOUD_LOCATION': 'us-west1',
        'ADK_MODEL_NAME': 'gemini-pro',
        'ADK_MAX_TOKENS': '500',
        'ADK_TEMPERATURE': '0.5'
    })
    def test_config_from_env(self):
        """Test creating config from environment variables."""
        config = create_adk_config_from_env()
        
        assert config.project_id == "env-project"
        assert config.location == "us-west1"
        assert config.model_name == "gemini-pro"
        assert config.max_tokens == 500
        assert config.temperature == 0.5


class TestConversationContext:
    """Test conversation context management."""
    
    def test_context_creation(self):
        """Test creating conversation context."""
        context = ConversationContext(
            session_id="test-session",
            user_id="test-user"
        )
        
        assert context.session_id == "test-session"
        assert context.user_id == "test-user"
        assert context.conversation_history == []
        assert context.metadata == {}
    
    def test_context_with_history(self):
        """Test context with conversation history."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        context = ConversationContext(
            session_id="test-session",
            conversation_history=history
        )
        
        assert len(context.conversation_history) == 2
        assert context.conversation_history[0]["content"] == "Hello"


class TestGoogleADKWebAgent:
    """Test Google ADK-Web agent."""
    
    @pytest.fixture
    def config(self):
        """Create test config."""
        return ADKWebConfig(
            project_id="test-project",
            model_name="gemini-1.5-pro"
        )
    
    @pytest.fixture
    def agent(self, config):
        """Create test agent."""
        return GoogleADKWebAgent(config)
    
    def test_agent_creation(self, agent, config):
        """Test agent creation."""
        assert agent.config == config
        assert agent._model is None
        assert len(agent.active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_initialize_without_credentials(self, agent):
        """Test initialization without Google Cloud credentials."""
        await agent.initialize()
        # Should not raise an error, just log a warning
        assert agent._model is None
    
    def test_session_management(self, agent):
        """Test session creation and management."""
        # Create session
        session_id = agent.create_session(user_id="test-user")
        assert session_id in agent.active_sessions
        
        # Get session
        session = agent.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.user_id == "test-user"
        
        # Close session
        agent.close_session(session_id)
        assert session_id not in agent.active_sessions
    
    @pytest.mark.asyncio
    async def test_process_message_mock(self, agent):
        """Test processing message with mock response."""
        # Create session
        session_id = agent.create_session()
        
        # Process message (should use mock since no real model)
        response = await agent.process_message("Hello", session_id)
        
        assert isinstance(response, StreamMessage)
        assert "Hello" in response.content or "mock" in response.content.lower()
        assert response.metadata["session_id"] == session_id
        
        # Check conversation history
        session = agent.get_session(session_id)
        assert len(session.conversation_history) == 2  # User + assistant
        assert session.conversation_history[0]["role"] == "user"
        assert session.conversation_history[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_process_message_invalid_session(self, agent):
        """Test processing message with invalid session."""
        response = await agent.process_message("Hello", "invalid-session")
        
        assert isinstance(response, StreamMessage)
        assert response.message_type == "error"
        assert "not found" in response.content.lower()
    
    @pytest.mark.asyncio
    async def test_stream_response(self, agent):
        """Test streaming response."""
        session_id = agent.create_session()
        chunks = []
        
        def collect_chunk(chunk):
            chunks.append(chunk)
        
        await agent.stream_response("Tell me a story", session_id, collect_chunk)
        
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0


class TestADKWebStreamHandler:
    """Test ADK-Web stream handler."""
    
    @pytest.fixture
    def agent(self):
        """Create test agent."""
        config = ADKWebConfig(project_id="test-project")
        return GoogleADKWebAgent(config)
    
    @pytest.fixture
    def handler(self, agent):
        """Create test handler."""
        return ADKWebStreamHandler(agent)
    
    @pytest.mark.asyncio
    async def test_handle_text_message(self, handler):
        """Test handling text messages."""
        message = StreamMessage(
            id="test-1",
            content="Hello",
            timestamp="2025-01-01T00:00:00Z",
            message_type="text"
        )
        
        response = await handler._handle_text_message(message)
        
        assert isinstance(response, StreamMessage)
        assert response.message_type == "text"
        assert "session_id" in response.metadata
    
    @pytest.mark.asyncio
    async def test_handle_start_session(self, handler):
        """Test handling session start."""
        message = StreamMessage(
            id="test-1",
            content="start_session",
            timestamp="2025-01-01T00:00:00Z",
            message_type="start_session",
            metadata={"user_id": "test-user"}
        )
        
        response = await handler._handle_start_session(message)
        
        assert response.message_type == "session_start"
        assert "session_id" in response.metadata
        assert "Session started" in response.content
    
    @pytest.mark.asyncio
    async def test_handle_end_session(self, handler):
        """Test handling session end."""
        # First create a session
        session_id = handler.adk_agent.create_session()
        
        message = StreamMessage(
            id="test-1",
            content="end_session",
            timestamp="2025-01-01T00:00:00Z",
            message_type="end_session",
            metadata={"session_id": session_id}
        )
        
        response = await handler._handle_end_session(message)
        
        assert response.message_type == "session_end"
        assert "Session ended" in response.content
        assert session_id not in handler.adk_agent.active_sessions