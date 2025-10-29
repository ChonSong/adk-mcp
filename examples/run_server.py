"""Example: Complete ADK-MCP server with all features."""

import asyncio
from adk_mcp.server import ADKServer


def main():
    """Run the complete ADK-MCP server."""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║           ADK-MCP Server                              ║
    ║   Agent Development Kit with Bidirectional Streaming  ║
    ╚═══════════════════════════════════════════════════════╝
    
    Features:
    • Bidirectional text streaming
    • Python code execution
    • Mock Google Cloud services
    • Android WebView support
    
    Starting server...
    """)
    
    server = ADKServer(
        host="0.0.0.0",
        port=8080,
        websocket_port=8081,
        enable_executor=True,
        enable_mock_services=True
    )
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")


if __name__ == "__main__":
    main()
