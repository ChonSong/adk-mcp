# ADK-MCP (Agent Development Kit - MCP)

A comprehensive Agent Development Kit with bidirectional streaming support, designed for building interactive AI agents with real-time coaddmmunication capabilities.

## Features

### Core Capabilities
- **Bidirectional Streaming**: Real-time text-based communication using WebSocket and async queues
- **Python Code Execution**: Server-side Python execution with safety checks (subprocess-based)
- **Google Cloud Services**: Integration with Google Cloud AI services, with a mock provider for local development.
  - Sentiment Analysis
  - Text Translation
  - Text Generation
  - Speech-to-Text & Text-to-Speech
- **Extensible Message Handling**: Use `StreamHandler` to register custom handlers for different message types.
- **API Request History**: Track mock service API calls for debugging and analysis.
- **Interactive WebView UI**: A pre-built, chat-like HTML interface for the Android WebView.
- **Health Check Endpoint**: Monitor server status and active connections via a `/health` endpoint.
- **Android WebView Support**: Ready-to-use bridge for mobile integration

### Architecture
- **Modality**: Text-only (voice capabilities can be added later)
- **Credentials**: Supports Google Cloud service account credentials, with a fallback to mocked APIs.
- **Mobile**: WebView wrapper for Android
- **Execution**: Simple subprocess-based Python execution (Docker sandbox planned for future)

## Installation

### From Source
```bash
git clone https://github.com/ChonSong/adk-mcp.git
cd adk-mcp
pip install -e .
```

### With Development Dependencies
```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Basic Bidirectional Streaming

```python
import asyncio
from adk_mcp.streaming import BiDirectionalStream

async def main():
    stream = BiDirectionalStream()
    await stream.start()
    
    # Send a message
    await stream.send("Hello, ADK!", "text")
    
    # Receive a message
    message = await stream.receive()
    print(f"Received: {message.content}")
    
    await stream.stop()

asyncio.run(main())
```

### 2. Python Code Execution

```python
import asyncio
from adk_mcp.executor import SafePythonExecutor

async def main():
    executor = SafePythonExecutor()
    
    code = """
x = 10
y = 20
print(f"Sum: {x + y}")
"""
    
    result = await executor.execute(code)
    print(result.output)  # "Sum: 30"

asyncio.run(main())
```

### 3. Mock Google Cloud Services

```python
import asyncio
from adk_mcp.mock_services import MockGoogleCloudServices

async def main():
    services = MockGoogleCloudServices()
    
    # Sentiment analysis
    result = await services.analyze_sentiment("This is amazing!")
    print(f"Sentiment: {result.sentiment_score}")
    
    # Translation
    translation = await services.translate_text("Hello", target_language="es")
    print(f"Translated: {translation.translated_text}")

asyncio.run(main())
```

### 4. Running the Full Server

```bash
python examples/run_server.py
```

The server will start on:
- HTTP: `http://localhost:8080`
- WebSocket: `ws://localhost:8081`

Access the interfaces:
- **Comprehensive Control Panel UI**: `http://localhost:8080/ui` (recommended)
- **Information Page**: `http://localhost:8080`
- **Android WebView Interface**: `http://localhost:8080/webview`

The Control Panel UI provides a modern, tabbed interface to access all features including:
- Dashboard with real-time server status
- Bidirectional streaming chat
- Python code executor with live results
- Sentiment analysis tool
- Text translation tool
- Text generation tool
- API request history viewer

## API Endpoints

### HTTP Endpoints

#### `GET /`
Main information page

#### `GET /ui`
Comprehensive Control Panel UI with access to all features

#### `GET /health`
Health check endpoint
```json
{
  "status": "healthy",
  "active_streams": 0,
  "executor_enabled": true,
  "mock_services_enabled": true
}
```

#### `GET /webview`
Android WebView interface (HTML page)

#### `POST /execute`
Execute Python code
```json
{
  "code": "print('Hello')",
  "timeout": 30
}
```

#### `POST /api/sentiment`
Analyze sentiment
```json
{
  "text": "This is a great day!"
}
```

#### `POST /api/translate`
Translate text
```json
{
  "text": "Hello",
  "target_language": "es",
  "source_language": "en"
}
```

#### `POST /api/generate`
Generate text
```json
{
  "prompt": "Tell me about AI",
  "max_tokens": 100,
  "temperature": 0.7
}
```

### WebSocket Connection

Connect to `ws://localhost:8081` for bidirectional streaming.

**Message Format:**
```json
{
  "id": "unique-id",
  "content": "message content",
  "timestamp": "2025-10-29T20:00:00",
  "message_type": "text",
  "metadata": {}
}
```

## Android Integration

### Using the WebView Bridge

1. **Add WebView to your Android layout**:
```xml
<WebView
    android:id="@+id/webview"
    android:layout_width="match_parent"
    android:layout_height="match_parent" />
```

2. **Configure WebView in your Activity/Fragment**:
```kotlin
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val webView = findViewById<WebView>(R.id.webview)
        webView.settings.javaScriptEnabled = true
        
        // Add interface
        webView.addJavascriptInterface(
            ADKWebInterface(webView) { message ->
                // Handle message from web
                handleMessage(message)
            },
            "AndroidInterface"
        )
        
        // Load ADK WebView interface
        webView.loadUrl("http://YOUR_SERVER:8080/webview")
    }
    
    private fun handleMessage(message: JSONObject) {
        val content = message.getString("content")
        // Process message...
    }
}

class ADKWebInterface(
    private val webView: WebView,
    private val messageHandler: (JSONObject) -> Unit
) {
    @JavascriptInterface
    fun receiveFromWeb(messageJson: String) {
        try {
            val message = JSONObject(messageJson)
            messageHandler(message)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
```

## Examples

Run the example scripts to see ADK-MCP in action:

```bash
# Basic streaming
python examples/basic_streaming.py

# Python execution
python examples/python_execution.py

# Mock services
python examples/mock_services_demo.py

# Full server
python examples/run_server.py
```

## Testing

Run tests with pytest:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=adk_mcp tests/

# Run specific test file
pytest tests/test_streaming.py
```

## Architecture Overview

```
adk-mcp/
├── src/adk_mcp/
│   ├── __init__.py           # Package initialization
│   ├── streaming.py          # Bidirectional streaming core
│   ├── executor.py           # Python code execution
│   ├── mock_services.py      # Mock Google Cloud services
│   ├── server.py             # HTTP/WebSocket server
│   └── mobile/
│       ├── __init__.py
│       └── android_webview.py # Android WebView bridge
├── tests/                    # Test suite
├── examples/                 # Example applications
└── setup.py                 # Package configuration
```

## Security Considerations

⚠️ **Current Implementation**: This is a development/demo version with basic security:
- Python executor uses simple subprocess calls
- Basic pattern blocking for dangerous code
- No sandboxing or isolation

🔒 **Planned for Production**:
- Docker-based sandboxing for code execution
- Proper authentication and authorization
- Rate limiting
- Input validation and sanitization

## Future Enhancements

- [ ] Voice/audio streaming support
- [ ] Docker-based execution sandbox
- [ ] Real Google Cloud service integration
- [ ] iOS WebView support
- [ ] Multi-user session management
- [ ] Enhanced security features
- [ ] Performance optimizations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions, please visit:
https://github.com/ChonSong/adk-mcp