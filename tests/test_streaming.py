"""Tests for bidirectional streaming functionality."""

import pytest
import asyncio
from adk_mcp.streaming import BiDirectionalStream, StreamMessage, StreamHandler


@pytest.mark.asyncio
async def test_stream_message_creation():
    """Test creating a stream message."""
    message = StreamMessage(
        id="test-123",
        content="Hello, world!",
        timestamp="2025-10-29T20:00:00",
        message_type="text"
    )
    
    assert message.id == "test-123"
    assert message.content == "Hello, world!"
    assert message.message_type == "text"


@pytest.mark.asyncio
async def test_stream_message_serialization():
    """Test message serialization to JSON."""
    message = StreamMessage(
        id="test-456",
        content="Test message",
        timestamp="2025-10-29T20:00:00",
        message_type="text"
    )
    
    json_str = message.to_json()
    assert isinstance(json_str, str)
    
    # Deserialize
    restored = StreamMessage.from_json(json_str)
    assert restored.id == message.id
    assert restored.content == message.content


@pytest.mark.asyncio
async def test_bidirectional_stream_lifecycle():
    """Test starting and stopping a stream."""
    stream = BiDirectionalStream()
    
    assert not stream.is_active
    
    await stream.start()
    assert stream.is_active
    
    await stream.stop()
    assert not stream.is_active


@pytest.mark.asyncio
async def test_stream_send_receive():
    """Test sending messages through stream."""
    stream = BiDirectionalStream()
    await stream.start()
    
    try:
        # Send a message
        sent_message = await stream.send("Test content", "text")
        assert sent_message.content == "Test content"
        assert sent_message.message_type == "text"
        
        # Simulate receiving a message
        receive_message = StreamMessage(
            id="recv-1",
            content="Response",
            timestamp="2025-10-29T20:00:00",
            message_type="text"
        )
        stream.simulate_receive(receive_message)
        
        # Wait a bit for async processing
        await asyncio.sleep(0.2)
        
        # Receive the message
        received = await asyncio.wait_for(stream.receive(), timeout=1.0)
        assert received.id == "recv-1"
        assert received.content == "Response"
        
    finally:
        await stream.stop()


@pytest.mark.asyncio
async def test_stream_handler():
    """Test stream message handler."""
    handler = StreamHandler()
    
    handled_messages = []
    
    def text_handler(message: StreamMessage):
        handled_messages.append(message)
        return None
    
    handler.register_handler("text", text_handler)
    
    message = StreamMessage(
        id="test-789",
        content="Handler test",
        timestamp="2025-10-29T20:00:00",
        message_type="text"
    )
    
    await handler.handle_message(message)
    
    assert len(handled_messages) == 1
    assert handled_messages[0].id == "test-789"


@pytest.mark.asyncio
async def test_stream_handler_async():
    """Test stream handler with async handler function."""
    handler = StreamHandler()
    
    handled_messages = []
    
    async def async_handler(message: StreamMessage):
        await asyncio.sleep(0.1)
        handled_messages.append(message)
        return None
    
    handler.register_handler("text", async_handler)
    
    message = StreamMessage(
        id="test-async",
        content="Async handler test",
        timestamp="2025-10-29T20:00:00",
        message_type="text"
    )
    
    await handler.handle_message(message)
    
    assert len(handled_messages) == 1
    assert handled_messages[0].id == "test-async"
