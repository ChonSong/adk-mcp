"""Example: Complete ADK-MCP server with Google ADK-Web integration."""

import asyncio
import os
from adk_mcp.server import ADKServer
from adk_mcp.google_adk import ADKWebConfig


def main():
    """Run the complete ADK-MCP server with Google ADK-Web."""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║           ADK-MCP Server with Google ADK-Web          ║
    ║   Agent Development Kit with Bidirectional Streaming  ║
    ╚═══════════════════════════════════════════════════════╝
    
    Features:
    • Google ADK-Web integration
    • Bidirectional text streaming
    • Python code execution
    • Mock Google Cloud services (fallback)
    • Android WebView support
    
    """)
    
    # Check for Google Cloud configuration
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if project_id:
        print(f"Google Cloud Project: {project_id}")
        if credentials_path:
            print(f"Credentials: {credentials_path}")
        else:
            print("Credentials: Using default credentials")
    else:
        print("Google Cloud Project: Not configured (using mock responses)")
        print("To enable Google ADK-Web, set:")
        print("  - GOOGLE_CLOUD_PROJECT=your-project-id")
        print("  - GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json")
    
    print("\nStarting server...")
    
    # Create custom ADK config if needed
    adk_config = None
    if project_id:
        adk_config = ADKWebConfig(
            project_id=project_id,
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            credentials_path=credentials_path,
            model_name=os.getenv("ADK_MODEL_NAME", "gemini-1.5-pro"),
            enable_streaming=True,
            max_tokens=int(os.getenv("ADK_MAX_TOKENS", "1000")),
            temperature=float(os.getenv("ADK_TEMPERATURE", "0.7"))
        )
    
    server = ADKServer(
        host="0.0.0.0",
        port=9090,
        websocket_port=9091,
        enable_executor=True,
        enable_mock_services=True,
        enable_google_adk=True,
        adk_config=adk_config
    )
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")


if __name__ == "__main__":
    main()
