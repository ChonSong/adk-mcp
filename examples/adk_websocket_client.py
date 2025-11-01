"""Example: WebSocket client for Google ADK-Web integration."""

import asyncio
import json
import websockets
from datetime import datetime, timezone
import uuid


async def main():
    """Demo WebSocket client with Google ADK-Web."""
    print("Connecting to ADK-MCP WebSocket server with Google ADK-Web...")
    
    uri = "ws://localhost:9091"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Starting conversation...")
            
            # Start a new session
            start_session_msg = {
                "id": str(uuid.uuid4()),
                "content": "start_session",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_type": "start_session",
                "metadata": {"user_id": "websocket_demo_user"}
            }
            
            await websocket.send(json.dumps(start_session_msg))
            response = await websocket.recv()
            session_response = json.loads(response)
            print(f"Session started: {session_response}")
            
            # Extract session ID for future messages
            session_id = session_response.get("metadata", {}).get("session_id")
            
            # Demo conversation messages
            messages = [
                "Hello! I'm connecting through WebSocket with Google ADK-Web.",
                "Can you tell me about the capabilities of this system?",
                "How does the bidirectional streaming work?",
                "What's the difference between using WebSocket vs HTTP endpoints?"
            ]
            
            for i, message_content in enumerate(messages, 1):
                print(f"\n--- Message {i} ---")
                print(f"Sending: {message_content}")
                
                # Create message
                message = {
                    "id": str(uuid.uuid4()),
                    "content": message_content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message_type": "text",
                    "metadata": {"session_id": session_id} if session_id else {}
                }
                
                # Send message
                await websocket.send(json.dumps(message))
                
                # Receive response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                print(f"Received: {response_data['content']}")
                print(f"Response ID: {response_data['id']}")
                
                # Update session ID if provided in response
                if "session_id" in response_data.get("metadata", {}):
                    session_id = response_data["metadata"]["session_id"]
                
                # Small delay between messages
                await asyncio.sleep(2)
            
            # End session
            if session_id:
                print(f"\n--- Ending Session ---")
                end_session_msg = {
                    "id": str(uuid.uuid4()),
                    "content": "end_session",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message_type": "end_session",
                    "metadata": {"session_id": session_id}
                }
                
                await websocket.send(json.dumps(end_session_msg))
                response = await websocket.recv()
                end_response = json.loads(response)
                print(f"Session ended: {end_response}")
            
            print("\nWebSocket demo completed!")
            
    except ConnectionRefusedError:
        print("Could not connect to WebSocket server.")
        print("Make sure the ADK-MCP server is running:")
        print("  python examples/run_server.py")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())