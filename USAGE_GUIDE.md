# ADK-MCP Usage Guide

This guide provides detailed instructions on how to use the Agent Development Kit (ADK-MCP) for building applications with bidirectional streaming.

## Table of Contents

1. [Installation](#installation)
2. [Core Concepts](#core-concepts)
3. [Bidirectional Streaming](#bidirectional-streaming)
4. [Python Code Execution](#python-code-execution)
5. [Mock Google Cloud Services](#mock-google-cloud-services)
6. [Server Deployment](#server-deployment)
7. [Android Integration](#android-integration)
8. [Advanced Usage](#advanced-usage)

## Installation

### Install from source

```bash
git clone https://github.com/ChonSong/adk-mcp.git
cd adk-mcp
pip install -e .
```

### Install with development dependencies

```bash
pip install -e ".[dev]"
```

## Core Concepts

### StreamMessage

The `StreamMessage` class represents a single message in the bidirectional stream:

```python
from adk_mcp.streaming import StreamMessage

message = StreamMessage(
    id="unique-id",
    content="Hello, world!",
    timestamp="2025-10-29T20:00:00",
    message_type="text",
    metadata={"key": "value"}
)

# Serialize to JSON
json_str = message.to_json()

# Deserialize from JSON
restored = StreamMessage.from_json(json_str)
```

### BiDirectionalStream

The core streaming class that manages message queues:

```python
from adk_mcp.streaming import BiDirectionalStream

stream = BiDirectionalStream()
await stream.start()

# Send a message
await stream.send("Hello!", "text")

# Receive a message
message = await stream.receive()

await stream.stop()
```

## Bidirectional Streaming

### Basic Example

```python
import asyncio
from adk_mcp.streaming import BiDirectionalStream, StreamMessage

async def main():
    stream = BiDirectionalStream()
    await stream.start()
    
    # Send messages
    msg1 = await stream.send("First message", "text")
    msg2 = await stream.send("Second message", "text")
    
    # Simulate receiving (in production, messages come from network)
    response = StreamMessage(
        id="resp-1",
        content="Response message",
        timestamp="2025-10-29T20:00:00",
        message_type="text"
    )
    stream.simulate_receive(response)
    
    # Receive messages
    received = await stream.receive()
    print(f"Received: {received.content}")
    
    await stream.stop()

asyncio.run(main())
```

### Using Stream Handlers

Stream handlers process incoming messages:

```python
from adk_mcp.streaming import StreamHandler, StreamMessage

handler = StreamHandler()

# Define handler function
async def text_handler(message: StreamMessage):
    print(f"Handling: {message.content}")
    # Return a response message if needed
    return None

# Register handler
handler.register_handler("text", text_handler)

# Use with stream
stream.handler = handler
```

### WebSocket Streaming

For real-time communication over WebSocket:

```python
from adk_mcp.streaming import WebSocketStream

# On server side (with websockets library)
async def handle_client(websocket):
    stream = WebSocketStream(websocket)
    await stream.start()
    
    # Define message handler
    async def on_message(message):
        response = StreamMessage(
            id=f"{message.id}_response",
            content=f"Echo: {message.content}",
            timestamp=message.timestamp,
            message_type="text"
        )
        await stream.send_queue.put(response)
    
    stream.handler.register_handler("text", on_message)
    
    # Start listening
    await stream.start_websocket_listener()
```

## Python Code Execution

### Basic Execution

```python
from adk_mcp.executor import PythonExecutor

executor = PythonExecutor(timeout=30)

code = """
result = 2 + 2
print(f"Result: {result}")
"""

result = await executor.execute(code)

if result.success:
    print(result.output)  # "Result: 4"
else:
    print(f"Error: {result.error}")
```

### Safe Execution

The `SafePythonExecutor` blocks dangerous operations:

```python
from adk_mcp.executor import SafePythonExecutor

executor = SafePythonExecutor(
    timeout=30,
    enable_safety_checks=True
)

# This will be blocked
code = "import os"
result = await executor.execute(code)
print(result.error)  # "Code contains blocked pattern: import os"

# This is allowed
code = """
numbers = [1, 2, 3, 4, 5]
print(sum(numbers))
"""
result = await executor.execute(code)
print(result.output)  # "15"
```

### Synchronous Execution

For non-async contexts:

```python
executor = PythonExecutor(timeout=10)
result = executor.execute_sync("print('Hello')")
```

## Mock Google Cloud Services

### Sentiment Analysis

```python
from adk_mcp.mock_services import MockGoogleCloudServices

services = MockGoogleCloudServices()

result = await services.analyze_sentiment("This is wonderful!")

print(f"Sentiment Score: {result.sentiment_score}")  # Positive value
print(f"Magnitude: {result.sentiment_magnitude}")
print(f"Language: {result.language}")
print(f"Entities: {result.entities}")
```

### Text Translation

```python
result = await services.translate_text(
    text="Hello, how are you?",
    target_language="es",
    source_language="en"
)

print(f"Translated: {result.translated_text}")
print(f"Confidence: {result.confidence}")
```

### Text Generation

```python
result = await services.generate_text(
    prompt="Tell me about AI",
    max_tokens=100,
    temperature=0.7
)

print(f"Generated: {result['generated_text']}")
print(f"Tokens Used: {result['tokens_used']}")
```

### Speech Services

```python
# Speech to Text
audio_data = b"audio bytes here"
result = await services.speech_to_text(audio_data)
print(f"Transcript: {result['transcript']}")

# Text to Speech
audio = await services.text_to_speech("Hello world")
print(f"Audio size: {len(audio)} bytes")
```

### Request History

Track all API calls for debugging:

```python
# Get history
history = services.get_request_history()
for req in history:
    print(f"{req['operation']} at {req['timestamp']}")

# Clear history
services.clear_history()
```

## Server Deployment

### Starting the Server

```python
from adk_mcp.server import ADKServer

server = ADKServer(
    host="0.0.0.0",
    port=8080,
    websocket_port=8081,
    enable_executor=True,
    enable_mock_services=True
)

# Run the server (blocking)
server.run()
```

### Making HTTP Requests

```python
import aiohttp

async def test_api():
    async with aiohttp.ClientSession() as session:
        # Health check
        async with session.get("http://localhost:8080/health") as resp:
            data = await resp.json()
            print(data)
        
        # Execute code
        async with session.post(
            "http://localhost:8080/execute",
            json={"code": "print('Hello')"}
        ) as resp:
            data = await resp.json()
            print(data['output'])
        
        # Sentiment analysis
        async with session.post(
            "http://localhost:8080/api/sentiment",
            json={"text": "Great day!"}
        ) as resp:
            data = await resp.json()
            print(data['sentiment_score'])
```

## Android Integration

### Setting Up WebView

1. Add WebView to layout:

```xml
<WebView
    android:id="@+id/adk_webview"
    android:layout_width="match_parent"
    android:layout_height="match_parent" />
```

2. Configure in Activity:

```kotlin
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        webView = findViewById(R.id.adk_webview)
        setupWebView()
    }
    
    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
        }
        
        // Add JavaScript interface
        webView.addJavascriptInterface(
            ADKWebInterface(),
            "AndroidInterface"
        )
        
        // Load ADK interface
        webView.loadUrl("http://YOUR_SERVER:8080/webview")
    }
    
    inner class ADKWebInterface {
        @JavascriptInterface
        fun receiveFromWeb(messageJson: String) {
            runOnUiThread {
                try {
                    val message = JSONObject(messageJson)
                    val content = message.getString("content")
                    handleMessage(content)
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        }
    }
    
    private fun handleMessage(content: String) {
        // Process message from web
        println("Received: $content")
        
        // Send response back to web
        val response = JSONObject().apply {
            put("id", System.currentTimeMillis().toString())
            put("content", "Response from Android")
            put("timestamp", "2025-10-29T20:00:00")
            put("message_type", "text")
        }
        
        webView.evaluateJavascript(
            "window.ADK.receiveMessage('${response}')",
            null
        )
    }
}
```

## Advanced Usage

### Custom Stream Handler

Create custom handlers for specific message types:

```python
from adk_mcp.streaming import BiDirectionalStream, StreamHandler, StreamMessage

class CommandHandler(StreamHandler):
    def __init__(self):
        super().__init__()
        self.register_handler("command", self.handle_command)
    
    async def handle_command(self, message: StreamMessage):
        command = message.content
        
        if command == "status":
            return StreamMessage(
                id=f"{message.id}_resp",
                content="System is running",
                timestamp=message.timestamp,
                message_type="response"
            )
        
        return None

# Use custom handler
stream = BiDirectionalStream()
stream.handler = CommandHandler()
```

### Integration with Existing Applications

```python
from adk_mcp import BiDirectionalStream, PythonExecutor, MockGoogleCloudServices

class MyApplication:
    def __init__(self):
        self.stream = BiDirectionalStream()
        self.executor = PythonExecutor()
        self.ai_services = MockGoogleCloudServices()
    
    async def start(self):
        await self.stream.start()
        
        # Set up message handler
        self.stream.handler.register_handler(
            "code_execute",
            self.handle_code_execution
        )
        
        self.stream.handler.register_handler(
            "analyze",
            self.handle_analysis
        )
    
    async def handle_code_execution(self, message: StreamMessage):
        code = message.metadata.get("code", "")
        result = await self.executor.execute(code)
        
        return StreamMessage(
            id=f"{message.id}_result",
            content=result.output,
            timestamp=message.timestamp,
            message_type="result",
            metadata={"success": result.success}
        )
    
    async def handle_analysis(self, message: StreamMessage):
        text = message.content
        result = await self.ai_services.analyze_sentiment(text)
        
        return StreamMessage(
            id=f"{message.id}_analysis",
            content=f"Sentiment: {result.sentiment_score}",
            timestamp=message.timestamp,
            message_type="result"
        )
```

## Testing

### Unit Tests

```python
import pytest
from adk_mcp.streaming import BiDirectionalStream

@pytest.mark.asyncio
async def test_stream():
    stream = BiDirectionalStream()
    await stream.start()
    
    msg = await stream.send("test", "text")
    assert msg.content == "test"
    
    await stream.stop()
```

### Integration Tests

Run the test suite:

```bash
pytest tests/ -v
```

## Best Practices

1. **Always handle exceptions** in stream handlers
2. **Close streams properly** using `await stream.stop()`
3. **Set appropriate timeouts** for code execution
4. **Use SafePythonExecutor** in production
5. **Clear request history** periodically to manage memory
6. **Validate message content** before processing
7. **Use async/await** consistently throughout your application

## Troubleshooting

### Common Issues

**Issue**: Stream not receiving messages
- Ensure stream is started with `await stream.start()`
- Check that messages are being added to the receive queue

**Issue**: Code execution timeout
- Increase timeout parameter
- Check for infinite loops in executed code

**Issue**: WebView not connecting
- Verify JavaScript is enabled
- Check server URL is correct
- Ensure CORS is configured if needed

## Further Resources

- [GitHub Repository](https://github.com/ChonSong/adk-mcp)
- [Examples Directory](./examples/)
- [API Documentation](./API.md)
- [Contributing Guide](./CONTRIBUTING.md)
