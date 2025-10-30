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
from .ui_template import get_comprehensive_ui_html


class ADKServer:
    """Main server for ADK-MCP with bidirectional streaming support."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        websocket_port: int = 8081,
        enable_executor: bool = True,
        enable_mock_services: bool = True,
    ):
        """
        Initialize ADK server.
        
        Args:
            host: Host to bind to
            port: HTTP server port
            websocket_port: WebSocket server port
            enable_executor: Enable Python code execution
            enable_mock_services: Enable mock Google Cloud services
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
        
        # Active streams
        self.active_streams: Dict[str, WebSocketStream] = {}
        
    def setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/ui", self.handle_ui)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_get("/webview", self.handle_webview)
        self.app.router.add_post("/execute", self.handle_execute)
        self.app.router.add_post("/api/sentiment", self.handle_sentiment)
        self.app.router.add_post("/api/translate", self.handle_translate)
        self.app.router.add_post("/api/generate", self.handle_generate)
    
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
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                h1 {{ 
                    color: #667eea; 
                    text-align: center;
                    font-size: 2.5em;
                    margin-bottom: 10px;
                }}
                .subtitle {{
                    text-align: center;
                    color: #6c757d;
                    margin-bottom: 30px;
                }}
                .cta {{
                    text-align: center;
                    margin: 30px 0;
                }}
                .cta a {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px 40px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-size: 1.2em;
                    font-weight: 600;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .cta a:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                }}
                .endpoint {{
                    background: #f8f9fa;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }}
                code {{
                    background: #e9ecef;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                }}
                .section {{
                    margin: 30px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 ADK-MCP Server</h1>
                <p class="subtitle">Agent Development Kit with Model Context Protocol</p>
                
                <div class="cta">
                    <a href="/ui">Open Control Panel →</a>
                </div>
                
                <div class="section">
                    <h2>Available Endpoints</h2>
                    <div class="endpoint"> 
                        <strong>GET /ui</strong> - Comprehensive Control Panel UI
                    </div>
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
                </div>
                
                <div class="section">
                    <h2>WebSocket</h2>
                    <p>Connect to <code>ws://localhost:{self.websocket_port}</code> for bidirectional streaming</p>
                </div>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")
    
    async def handle_ui(self, request: web.Request) -> web.Response:
        """Serve comprehensive UI control panel."""
        html = get_comprehensive_ui_html(self.websocket_port)
        return web.Response(text=html, content_type="text/html")
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "active_streams": len(self.active_streams),
            "executor_enabled": self.executor is not None,
            "mock_services_enabled": self.mock_services is not None,
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
    
    async def handle_websocket(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket connection for bidirectional streaming."""
        stream = WebSocketStream(websocket)
        self.active_streams[stream.stream_id] = stream
        
        try:
            await stream.start()
            
            # Set up message handler
            async def handle_message(message: StreamMessage):
                # Echo message back for demo
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
        # Start HTTP server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        print(f"ADK-MCP Server started")
        print(f"HTTP server: http://{self.host}:{self.port}")
        print(f"WebSocket server: ws://{self.host}:{self.websocket_port}")
        
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
