"""Server implementation for ADK-MCP with bidirectional streaming."""

import asyncio
import json
from typing import Optional, Dict, Any
from aiohttp import web
import websockets
from websockets.server import WebSocketServerProtocol

from .streaming import BiDirectionalStream, StreamMessage, WebSocketStream
from .executor import PythonExecutor, SafePythonExecutor
from .mock_services import MockGoogleCloudServices
from .mobile.android_webview import AndroidWebViewBridge
from .google_adk import GoogleADKWebAgent, ADKWebConfig, ADKWebStreamHandler, create_adk_config_from_env
from .voice_streaming import VoiceStreamManager, VoiceWebSocketHandler
from .adk_voice_agent import GoogleADKVoiceAgent


class ADKServer:
    """Main server for ADK-MCP with bidirectional streaming support."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        websocket_port: int = 8081,
        enable_executor: bool = True,
        enable_mock_services: bool = True,
        enable_google_adk: bool = True,
        adk_config: Optional[ADKWebConfig] = None,
    ):
        """
        Initialize ADK server.
        
        Args:
            host: Host to bind to
            port: HTTP server port
            websocket_port: WebSocket server port
            enable_executor: Enable Python code execution
            enable_mock_services: Enable mock Google Cloud services
            enable_google_adk: Enable Google ADK-Web integration
            adk_config: Google ADK-Web configuration (uses env vars if None)
        """
        self.host = host
        self.port = port
        self.websocket_port = websocket_port
        self.app = web.Application()
        self.setup_routes()
        
        # Components
        self.executor = SafePythonExecutor() if enable_executor else None
        self.mock_services = MockGoogleCloudServices() if enable_mock_services else None
        self.webview_bridge = AndroidWebViewBridge()
        
        # Google ADK-Web integration
        self.google_adk_agent = None
        self.google_adk_voice_agent = None
        if enable_google_adk:
            config = adk_config or create_adk_config_from_env()
            self.google_adk_agent = GoogleADKWebAgent(config)
            self.google_adk_voice_agent = GoogleADKVoiceAgent(config, self.executor)
        
        # Voice streaming
        self.voice_manager = VoiceStreamManager()
        self.voice_handler = VoiceWebSocketHandler(self.voice_manager)
        
        # Active streams
        self.active_streams: Dict[str, WebSocketStream] = {}
        
    def setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_get("/webview", self.handle_webview)
        self.app.router.add_get("/voice", self.handle_voice_client)
        
        # Static file serving
        self.app.router.add_static("/static/", "static/")
        self.app.router.add_post("/execute", self.handle_execute)
        self.app.router.add_post("/api/sentiment", self.handle_sentiment)
        self.app.router.add_post("/api/translate", self.handle_translate)
        self.app.router.add_post("/api/generate", self.handle_generate)
        
        # Google ADK-Web endpoints
        self.app.router.add_post("/adk/chat", self.handle_adk_chat)
        self.app.router.add_post("/adk/session/start", self.handle_adk_start_session)
        self.app.router.add_post("/adk/session/end", self.handle_adk_end_session)
        
        # Voice streaming endpoints
        self.app.router.add_get("/voice/stream", self.handle_voice_stream)
        self.app.router.add_get("/voice/stats", self.handle_voice_stats)
    
    async def handle_index(self, request: web.Request) -> web.Response:
        """Handle index page."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ADK-MCP Server</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                }}
                h1 {{ color: #2196f3; }}
                .endpoint {{
                    background: #f5f5f5;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 4px;
                }}
                code {{
                    background: #e0e0e0;
                    padding: 2px 6px;
                    border-radius: 3px;
                }}
            </style>
        </head>
        <body>
            <h1>ADK-MCP Server</h1>
            <p>Agent Development Kit with bidirectional streaming support</p>
            
            <h2>Available Endpoints</h2>
            <div class="endpoint"> 
                <strong>GET /health</strong> - Health check
            </div>
            <div class="endpoint"> 
                <strong>GET /webview</strong> - Android WebView interface
            </div>
            <div class="endpoint"> 
                <strong>POST /execute</strong> - Execute Python code
            </div>
            <div class="endpoint"> 
                <strong>POST /api/sentiment</strong> - Sentiment analysis (mocked)
            </div>
            <div class="endpoint">
                <strong>POST /api/translate</strong> - Text translation (mocked)
            </div>
            <div class="endpoint">
                <strong>POST /api/generate</strong> - Text generation (mocked)
            </div>
            
            <h2>Google ADK-Web Endpoints</h2>
            <div class="endpoint">
                <strong>POST /adk/chat</strong> - Chat with Google ADK-Web agent
            </div>
            <div class="endpoint">
                <strong>POST /adk/session/start</strong> - Start new conversation session
            </div>
            <div class="endpoint">
                <strong>POST /adk/session/end</strong> - End conversation session
            </div>
            
            <h2>Voice Streaming Endpoints</h2>
            <div class="endpoint">
                <strong>GET /voice/stream</strong> - WebSocket endpoint for voice streaming
            </div>
            <div class="endpoint">
                <strong>GET /voice/stats</strong> - Voice session statistics
            </div>
            
            <h2>WebSocket</h2>
            <p>Connect to <code>ws://localhost:{self.websocket_port}</code> for bidirectional streaming</p>
            <p>Connect to <code>ws://localhost:{self.websocket_port}/voice/stream</code> for voice streaming</p>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        voice_stats = self.voice_manager.get_session_stats() if self.voice_manager else {}
        
        return web.json_response({
            "status": "healthy",
            "active_streams": len(self.active_streams),
            "executor_enabled": self.executor is not None,
            "mock_services_enabled": self.mock_services is not None,
            "google_adk_enabled": self.google_adk_agent is not None,
            "voice_streaming_enabled": self.google_adk_voice_agent is not None,
            "active_sessions": len(self.google_adk_agent.active_sessions) if self.google_adk_agent else 0,
            "active_voice_sessions": voice_stats.get("active_sessions", 0),
        })
    
    async def handle_webview(self, request: web.Request) -> web.Response:
        """Serve Android WebView interface."""
        html = self.webview_bridge.get_html_template()
        return web.Response(text=html, content_type="text/html")
    
    async def handle_execute(self, request: web.Request) -> web.Response:
        """Execute Python code."""
        if not self.executor:
            return web.json_response(
                {"error": "Python execution is not enabled"},
                status=400
            )
        
        try:
            data = await request.json()
            code = data.get("code", "")
            timeout = data.get("timeout")
            
            result = await self.executor.execute(code, timeout)
            return web.json_response(result.to_dict())
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def handle_sentiment(self, request: web.Request) -> web.Response:
        """Mock sentiment analysis."""
        if not self.mock_services:
            return web.json_response(
                {"error": "Mock services not enabled"},
                status=400
            )
        
        try:
            data = await request.json()
            text = data.get("text", "")
            
            result = await self.mock_services.analyze_sentiment(text)
            return web.json_response(result.to_dict())
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def handle_translate(self, request: web.Request) -> web.Response:
        """Mock text translation."""
        if not self.mock_services:
            return web.json_response(
                {"error": "Mock services not enabled"},
                status=400
            )
        
        try:
            data = await request.json()
            text = data.get("text", "")
            target_language = data.get("target_language", "en")
            source_language = data.get("source_language")
            
            result = await self.mock_services.translate_text(
                text, target_language, source_language
            )
            return web.json_response(result.to_dict())
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def handle_generate(self, request: web.Request) -> web.Response:
        """Mock text generation."""
        if not self.mock_services:
            return web.json_response(
                {"error": "Mock services not enabled"},
                status=400
            )
        
        try:
            data = await request.json()
            prompt = data.get("prompt", "")
            max_tokens = data.get("max_tokens", 100)
            temperature = data.get("temperature", 0.7)
            
            result = await self.mock_services.generate_text(
                prompt, max_tokens, temperature
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def handle_adk_chat(self, request: web.Request) -> web.Response:
        """Handle chat with Google ADK-Web agent."""
        if not self.google_adk_agent:
            return web.json_response(
                {"error": "Google ADK-Web is not enabled"},
                status=400
            )
        
        try:
            data = await request.json()
            message = data.get("message", "")
            session_id = data.get("session_id")
            
            if not session_id:
                # Create new session if none provided
                session_id = self.google_adk_agent.create_session()
            
            response = await self.google_adk_agent.process_message(message, session_id)
            return web.json_response(response.to_dict())
            
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def handle_adk_start_session(self, request: web.Request) -> web.Response:
        """Start new ADK-Web conversation session."""
        if not self.google_adk_agent:
            return web.json_response(
                {"error": "Google ADK-Web is not enabled"},
                status=400
            )
        
        try:
            data = await request.json()
            user_id = data.get("user_id")
            
            session_id = self.google_adk_agent.create_session(user_id)
            return web.json_response({
                "session_id": session_id,
                "status": "started"
            })
            
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def handle_adk_end_session(self, request: web.Request) -> web.Response:
        """End ADK-Web conversation session."""
        if not self.google_adk_agent:
            return web.json_response(
                {"error": "Google ADK-Web is not enabled"},
                status=400
            )
        
        try:
            data = await request.json()
            session_id = data.get("session_id")
            
            if not session_id:
                return web.json_response(
                    {"error": "session_id is required"},
                    status=400
                )
            
            self.google_adk_agent.close_session(session_id)
            return web.json_response({
                "session_id": session_id,
                "status": "ended"
            })
            
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def handle_voice_stream(self, request: web.Request) -> web.WebSocketResponse:
        """Handle voice streaming WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Create voice session
        if self.google_adk_voice_agent:
            session = await self.google_adk_voice_agent.create_voice_session(ws)
            
            try:
                # Handle voice streaming
                await self.voice_handler.handle_connection(ws, "/voice/stream")
            finally:
                await self.google_adk_voice_agent.close_voice_session(session)
        else:
            await ws.close(code=1011, message=b"Voice streaming not available")
        
        return ws
    
    async def handle_voice_stats(self, request: web.Request) -> web.Response:
        """Get voice streaming statistics."""
        stats = {
            "voice_manager": self.voice_manager.get_session_stats(),
            "voice_agent": self.google_adk_voice_agent.get_session_stats() if self.google_adk_voice_agent else None
        }
        return web.json_response(stats)
    
    async def handle_voice_client(self, request: web.Request) -> web.Response:
        """Serve voice-enabled web client."""
        try:
            with open("static/voice_client.html", "r") as f:
                html_content = f.read()
            return web.Response(text=html_content, content_type="text/html")
        except FileNotFoundError:
            return web.Response(text="Voice client not found", status=404)
    
    async def handle_websocket(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket connection for bidirectional streaming."""
        stream = WebSocketStream(websocket)
        self.active_streams[stream.stream_id] = stream
        
        try:
            await stream.start()
            
            # Set up message handler
            if self.google_adk_agent:
                # Use Google ADK-Web handler
                adk_handler = ADKWebStreamHandler(self.google_adk_agent)
                stream.handler = adk_handler
            else:
                # Fallback to echo handler
                async def handle_message(message: StreamMessage):
                    response = StreamMessage(
                        id=message.id + "_response",
                        content=f"Received: {message.content}",
                        timestamp=message.timestamp,
                        message_type="text"
                    )
                    await stream.send_queue.put(response)
                
                stream.handler.register_handler("text", handle_message)
            
            # Start listening
            await stream.start_websocket_listener()
            
        finally:
            await stream.stop()
            del self.active_streams[stream.stream_id]
    
    async def start_websocket_server(self):
        """Start WebSocket server."""
        async with websockets.serve(
            self.handle_websocket,
            self.host,
            self.websocket_port
        ):
            await asyncio.Future()  # Run forever
    
    async def start(self):
        """Start the server."""
        # Initialize Google ADK-Web agent if enabled
        if self.google_adk_agent:
            await self.google_adk_agent.initialize()
        
        # Initialize Google ADK Voice agent if enabled
        if self.google_adk_voice_agent:
            await self.google_adk_voice_agent.initialize()
        
        # Start HTTP server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        print(f"ADK-MCP Server started")
        print(f"HTTP server: http://{self.host}:{self.port}")
        print(f"WebSocket server: ws://{self.host}:{self.websocket_port}")
        if self.google_adk_agent:
            print(f"Google ADK-Web: Enabled")
        else:
            print(f"Google ADK-Web: Disabled")
        
        # Start WebSocket server
        await self.start_websocket_server()
    
    def run(self):
        """Run the server (blocking)."""
        asyncio.run(self.start())


def main():
    """Main entry point."""
    server = ADKServer()
    server.run()


if __name__ == "__main__":
    main()
