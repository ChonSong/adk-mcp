# ADK-MCP (Agent Development Kit - MCP)

A comprehensive Agent Development Kit with Google ADK-Web integration and bidirectional streaming support, designed for building interactive AI agents with real-time communication capabilities powered by Google's conversational AI framework.

## Features

### Core Capabilities
- **Google ADK-Web Integration**: Native integration with Google's Agent Development Kit for Web, providing advanced conversational AI capabilities
- **Bidirectional Streaming**: Real-time text-based communication using WebSocket and async queues
- **Conversation Management**: Session-based conversations with context preservation and history tracking
- **Python Code Execution**: Server-side Python execution with safety checks (subprocess-based)
- **Google Cloud AI Services**: Integration with Vertex AI, Gemini models, and other Google Cloud AI services
  - Advanced text generation with Gemini models
  - Conversation context management
  - Streaming responses for real-time interaction
- **Fallback Mock Services**: Mock providers for development without Google Cloud credentials
  - Sentiment Analysis
  - Text Translation
  - Text Generation
- **Extensible Message Handling**: Use `StreamHandler` to register custom handlers for different message types
- **Interactive WebView UI**: A pre-built, chat-like HTML interface optimized for Google ADK-Web
- **Health Check Endpoint**: Monitor server status, active connections, and ADK-Web sessions
- **Android WebView Support**: Ready-to-use bridge for mobile integration with session management

### Architecture
- **AI Framework**: Built on Google ADK-Web for advanced conversational AI capabilities
- **Modality**: Text-based conversations with streaming support (voice capabilities can be added)
- **Authentication**: Google Cloud service account credentials with automatic fallback to mock responses
- **Session Management**: Persistent conversation sessions with context and history tracking
- **Mobile**: WebView wrapper for Android with ADK-Web session integration
- **Execution**: Secure subprocess-based Python execution (Docker sandbox planned for future)

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

## Google ADK-Web Configuration

### Prerequisites
1. **Google Cloud Project**: Create a project in Google Cloud Console
2. **Enable APIs**: Enable Vertex AI API and other required services
3. **Service Account**: Create a service account with appropriate permissions
4. **Credentials**: Download the service account key JSON file

### Environment Variables
Set the following environment variables for Google ADK-Web integration:

```bash
# Required
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Optional (with defaults)
export GOOGLE_CLOUD_LOCATION="us-central1"
export ADK_MODEL_NAME="gemini-1.5-pro"
export ADK_MAX_TOKENS="1000"
export ADK_TEMPERATURE="0.7"
export ADK_ENABLE_STREAMING="true"
```

### Without Google Cloud Credentials
The system automatically falls back to mock responses when Google Cloud credentials are not available, making it perfect for development and testing.

## Quick Start

### 1. Google ADK-Web Conversation

```python
import asyncio
from adk_mcp.google_adk import GoogleADKWebAgent, ADKWebConfig

async def main():
    # Configure Google ADK-Web
    config = ADKWebConfig(
        project_id="your-project-id",
        model_name="gemini-1.5-pro"
    )
    
    # Initialize agent
    agent = GoogleADKWebAgent(config)
    await agent.initialize()
    
    # Create conversation session
    session_id = agent.create_session(user_id="demo_user")
    
    # Chat with the agent
    response = await agent.process_message("Hello! Tell me about Google ADK-Web.", session_id)
    print(response.content)
    
    # Clean up
    agent.close_session(session_id)

asyncio.run(main())
```

### 2. Basic Bidirectional Streaming

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

Access the web interface at `http://localhost:8080` or the Android WebView interface at `http://localhost:8080/webview`

## API Endpoints

### HTTP Endpoints

#### `GET /`
Main information page

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
Generate text (mock service)
```json
{
  "prompt": "Tell me about AI",
  "max_tokens": 100,
  "temperature": 0.7
}
```

### Google ADK-Web Endpoints

#### `POST /adk/chat`
Chat with Google ADK-Web agent
```json
{
  "message": "Hello, how can you help me?",
  "session_id": "optional-session-id"
}
```

#### `POST /adk/session/start`
Start new conversation session
```json
{
  "user_id": "optional-user-id"
}
```

#### `POST /adk/session/end`
End conversation session
```json
{
  "session_id": "session-id-to-end"
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

Run the example scripts to see ADK-MCP with Google ADK-Web in action:

```bash
# Google ADK-Web integration demo
python examples/google_adk_demo.py

# Full server with Google ADK-Web
python examples/run_server.py

# WebSocket client with ADK-Web
python examples/adk_websocket_client.py

# Basic streaming (legacy)
python examples/basic_streaming.py

# Python execution
python examples/python_execution.py

# Mock services
python examples/mock_services_demo.py
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