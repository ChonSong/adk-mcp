"""Bidirectional streaming core implementation for ADK-MCP."""

import asyncio
import json
from typing import Any, Callable, Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid


@dataclass
class StreamMessage:
    """Represents a message in the bidirectional stream."""
    
    id: str
    content: str
    timestamp: str
    message_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamMessage":
        """Create message from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "StreamMessage":
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class StreamHandler:
    """Handler for processing stream messages."""
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        
    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type."""
        if message_type not in self.handlers:
            self.handlers[message_type] = []
        self.handlers[message_type].append(handler)
    
    async def handle_message(self, message: StreamMessage) -> Optional[StreamMessage]:
        """Process a message using registered handlers."""
        if message.message_type in self.handlers:
            for handler in self.handlers[message.message_type]:
                result = handler(message)
                if asyncio.iscoroutine(result):
                    result = await result
                if result:
                    return result
        return None


class BiDirectionalStream:
    """Core bidirectional streaming implementation."""
    
    def __init__(self, stream_id: Optional[str] = None):
        self.stream_id = stream_id or str(uuid.uuid4())
        self.is_active = False
        self.send_queue: asyncio.Queue = asyncio.Queue()
        self.receive_queue: asyncio.Queue = asyncio.Queue()
        self.handler = StreamHandler()
        self._tasks: List[asyncio.Task] = []
        
    async def start(self):
        """Start the bidirectional stream."""
        if self.is_active:
            raise RuntimeError("Stream is already active")
        
        self.is_active = True
        # Start processing tasks
        self._tasks.append(asyncio.create_task(self._process_send_queue()))
        self._tasks.append(asyncio.create_task(self._process_receive_queue()))
        
    async def stop(self):
        """Stop the bidirectional stream."""
        self.is_active = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
    async def send(self, content: str, message_type: str = "text", 
                   metadata: Optional[Dict[str, Any]] = None) -> StreamMessage:
        """Send a message through the stream."""
        message = StreamMessage(
            id=str(uuid.uuid4()),
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            message_type=message_type,
            metadata=metadata or {}
        )
        
        await self.send_queue.put(message)
        return message
    
    async def receive(self) -> StreamMessage:
        """Receive a message from the stream."""
        message = await self.receive_queue.get()
        return message
    
    async def _process_send_queue(self):
        """Process messages in the send queue."""
        while self.is_active:
            try:
                message = await asyncio.wait_for(
                    self.send_queue.get(), 
                    timeout=0.1
                )
                # Here you would normally send to actual transport layer
                # For now, we'll echo it back to receive queue for testing
                await self._handle_outgoing_message(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
    
    async def _process_receive_queue(self):
        """Process messages in the receive queue."""
        while self.is_active:
            try:
                # Wait for messages to be added to receive queue
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
    
    async def _handle_outgoing_message(self, message: StreamMessage):
        """Handle outgoing messages (can be overridden for custom transport)."""
        # Default implementation: echo for testing
        pass
    
    def simulate_receive(self, message: StreamMessage):
        """Simulate receiving a message (for testing/demo purposes)."""
        asyncio.create_task(self.receive_queue.put(message))


class WebSocketStream(BiDirectionalStream):
    """WebSocket-based bidirectional stream implementation."""
    
    def __init__(self, websocket=None, stream_id: Optional[str] = None):
        super().__init__(stream_id)
        self.websocket = websocket
        
    async def _handle_outgoing_message(self, message: StreamMessage):
        """Send message through WebSocket."""
        if self.websocket:
            await self.websocket.send(message.to_json())
        else:
            # For testing without actual websocket
            await self.receive_queue.put(message)
    
    async def start_websocket_listener(self):
        """Listen for incoming WebSocket messages."""
        if not self.websocket:
            return
            
        try:
            async for message_str in self.websocket:
                try:
                    message = StreamMessage.from_json(message_str)
                    await self.receive_queue.put(message)
                    
                    # Process with handler
                    response = await self.handler.handle_message(message)
                    if response:
                        await self.send_queue.put(response)
                except json.JSONDecodeError:
                    # Handle malformed messages
                    pass
        except Exception:
            # Connection closed or error
            await self.stop()
