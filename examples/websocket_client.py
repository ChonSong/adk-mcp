"""Example WebSocket client for testing ADK-MCP streaming."""

import asyncio
import websockets
import json
from datetime import datetime, timezone


async def websocket_client():
    """Connect to ADK-MCP WebSocket server and test streaming."""
    uri = "ws://localhost:8081"
    
    print("WebSocket Client Test")
    print("=" * 50)
    print(f"Connecting to {uri}...\n")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to server\n")
            
            # Send test messages
            messages = [
                "Hello, ADK Server!",
                "How are you doing?",
                "Testing bidirectional streaming"
            ]
            
            for i, content in enumerate(messages, 1):
                message = {
                    "id": f"msg-{i}",
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message_type": "text",
                    "metadata": {}
                }
                
                print(f"Sending message {i}:")
                print(f"  {content}")
                
                await websocket.send(json.dumps(message))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=2.0
                    )
                    response_data = json.loads(response)
                    print(f"Received response:")
                    print(f"  {response_data.get('content', 'No content')}\n")
                except asyncio.TimeoutError:
                    print("  (No response received)\n")
                
                await asyncio.sleep(0.5)
            
            print("=" * 50)
            print("✓ Test completed!")
            
    except ConnectionRefusedError:
        print("✗ Error: Could not connect to server")
        print("  Make sure the server is running:")
        print("  python examples/run_server.py")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    asyncio.run(websocket_client())
