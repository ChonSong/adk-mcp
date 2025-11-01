"""Server implementation for ADK-MCP with bidirectional streaming."""

import asyncio
import json
from typing import Optional, Dict, Any
from aiohttp import web
import websockets
from websockets.server import WebSocketServerProtocol

from .google_adk import GoogleADKWebAgent, ADKWebConfig, create_adk_config_from_env
from .adk_voice_agent import GoogleADKVoiceAgent

try:
    from .mobile.android_webview import AndroidWebViewBridge
    ANDROID_WEBVIEW_AVAILABLE = True
except ImportError:
    ANDROID_WEBVIEW_AVAILABLE = False


class ADKServer:
    """Main server for ADK-MCP with bidirectional streaming support."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        websocket_port: int = 8081,
        enable_google_adk: bool = True,
        adk_config: Optional[ADKWebConfig] = None,
    ):
        """
        Initialize ADK server.
        
        Args:
            host: Host to bind to
            port: HTTP server port
            websocket_port: WebSocket server port
            enable_google_adk: Enable Google ADK integration
            adk_config: Google ADK configuration (uses env vars if None)
        """
        self.host = host
        self.port = port
        self.websocket_port = websocket_port
        self.app = web.Application()
        self.setup_routes()
        
        # Components
        self.webview_bridge = AndroidWebViewBridge() if ANDROID_WEBVIEW_AVAILABLE else None
        
        # Google ADK integration
        self.google_adk_agent = None
        self.google_adk_voice_agent = None
        if enable_google_adk:
            config = adk_config or create_adk_config_from_env()
            self.google_adk_agent = GoogleADKWebAgent(config)
            self.google_adk_voice_agent = GoogleADKVoiceAgent(config)
        
        # Active voice sessions (managed by ADK)
        self.active_voice_sessions = {}
        
    def setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_get("/webview", self.handle_webview)
        self.app.router.add_get("/voice", self.handle_voice_client)
        
        # Static file serving
        self.app.router.add_static("/static/", "static/")
        
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
        voice_stats = self.google_adk_voice_agent.get_session_stats() if self.google_adk_voice_agent else {}
        
        return web.json_response({
            "status": "healthy",
            "google_adk_enabled": self.google_adk_agent is not None,
            "voice_streaming_enabled": self.google_adk_voice_agent is not None,
            "active_sessions": len(self.google_adk_agent.active_sessions) if self.google_adk_agent else 0,
            "active_voice_sessions": voice_stats.get("active_sessions", 0),
            "android_webview_available": ANDROID_WEBVIEW_AVAILABLE,
        })
    
    async def handle_webview(self, request: web.Request) -> web.Response:
        """Serve Android WebView interface."""
        if not ANDROID_WEBVIEW_AVAILABLE:
            return web.Response(text="Android WebView not available", status=404)
        
        html = self.webview_bridge.get_html_template()
        return web.Response(text=html, content_type="text/html")
    

    
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
        
        # Create voice session using ADK
        if self.google_adk_voice_agent:
            session = await self.google_adk_voice_agent.create_voice_session(ws)
            self.active_voice_sessions[session.session_id] = session
            
            try:
                # Handle voice streaming with ADK
                await self.google_adk_voice_agent.handle_voice_websocket(ws, session)
            finally:
                await self.google_adk_voice_agent.close_voice_session(session)
                if session.session_id in self.active_voice_sessions:
                    del self.active_voice_sessions[session.session_id]
        else:
            await ws.close(code=1011, message=b"Voice streaming not available")
        
        return ws
    
    async def handle_voice_stats(self, request: web.Request) -> web.Response:
        """Get voice streaming statistics."""
        stats = {
            "voice_agent": self.google_adk_voice_agent.get_session_stats() if self.google_adk_voice_agent else None,
            "active_voice_sessions": len(self.active_voice_sessions)
        }
        return web.json_response(stats)
    
    async def handle_voice_client(self, request: web.Request) -> web.Response:
        """Serve voice-enabled web client."""
        try:
            with open("static/voice_client.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            return web.Response(text=html_content, content_type="text/html")
        except FileNotFoundError:
            return web.Response(text="Voice client not found", status=404)
        except UnicodeDecodeError:
            return web.Response(text="Error reading voice client file", status=500)
    

    
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
        if self.google_adk_agent:
            print(f"Google ADK: Enabled")
        else:
            print(f"Google ADK: Disabled")
        if self.google_adk_voice_agent:
            print(f"Voice streaming: Enabled")
        else:
            print(f"Voice streaming: Disabled")
        
        # Keep server running
        await asyncio.Future()  # Run forever
    
    def run(self):
        """Run the server (blocking)."""
        asyncio.run(self.start())


def main():
    """Main entry point."""
    server = ADKServer(
        host="0.0.0.0",
        port=8080,
        enable_google_adk=True
    )
    server.run()


if __name__ == "__main__":
    main()
