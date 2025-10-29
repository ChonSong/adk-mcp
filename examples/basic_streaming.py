"""Example: Basic bidirectional streaming."""

import asyncio
from adk_mcp.streaming import BiDirectionalStream, StreamMessage


async def main():
    """Demonstrate basic bidirectional streaming."""
    print("Starting bidirectional stream demo...\n")
    
    # Create and start stream
    stream = BiDirectionalStream()
    await stream.start()
    
    try:
        # Send some messages
        print("Sending messages...")
        msg1 = await stream.send("Hello, ADK!", "text")
        print(f"Sent: {msg1.content}")
        
        msg2 = await stream.send("How are you?", "text")
        print(f"Sent: {msg2.content}")
        
        # Simulate receiving messages
        print("\nSimulating received messages...")
        response1 = StreamMessage(
            id="resp-1",
            content="Hello! I'm doing well.",
            timestamp="2025-10-29T20:00:00",
            message_type="text"
        )
        stream.simulate_receive(response1)
        
        response2 = StreamMessage(
            id="resp-2",
            content="Thanks for asking!",
            timestamp="2025-10-29T20:00:01",
            message_type="text"
        )
        stream.simulate_receive(response2)
        
        # Receive messages
        print("\nReceiving messages...")
        await asyncio.sleep(0.3)  # Give time for async processing
        
        received1 = await asyncio.wait_for(stream.receive(), timeout=2.0)
        print(f"Received: {received1.content}")
        
        received2 = await asyncio.wait_for(stream.receive(), timeout=2.0)
        print(f"Received: {received2.content}")
        
        print("\n✓ Demo completed successfully!")
        
    finally:
        await stream.stop()


if __name__ == "__main__":
    asyncio.run(main())
