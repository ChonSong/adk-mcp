#!/usr/bin/env python3
"""Startup script for ADK-MCP server with voice capabilities."""

import sys
import os
sys.path.append('.')

from src.adk_mcp.server import ADKServer

def main():
    """Start the ADK-MCP server with voice capabilities."""
    # Use different ports to avoid conflicts
    server = ADKServer(
        host="0.0.0.0",
        port=8000,  # HTTP server port
        websocket_port=8001,  # WebSocket server port
        enable_executor=True,
        enable_mock_services=True,
        enable_google_adk=True
    )
    
    print("🎤 Starting ADK-MCP Server with Voice Capabilities...")
    print("📋 Features enabled:")
    print("   ✅ Python Code Execution")
    print("   ✅ Google ADK-Web Integration")
    print("   ✅ Voice Streaming (gemini-2.5-pro)")
    print("   ✅ Mock Google Cloud Services")
    print("   ✅ Android WebView Support")
    print()
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    main()