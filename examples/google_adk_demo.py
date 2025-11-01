"""Example: Google ADK-Web integration demo."""

import asyncio
import os
from adk_mcp.google_adk import GoogleADKWebAgent, ADKWebConfig


async def main():
    """Demonstrate Google ADK-Web integration."""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║           Google ADK-Web Integration Demo             ║
    ║   Agent Development Kit with Google ADK-Web           ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    # Create configuration
    config = ADKWebConfig(
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id"),
        location="us-central1",
        model_name="gemini-1.5-pro",
        max_tokens=500,
        temperature=0.7
    )
    
    # Initialize agent
    agent = GoogleADKWebAgent(config)
    await agent.initialize()
    
    # Create a conversation session
    session_id = agent.create_session(user_id="demo_user")
    print(f"Created session: {session_id}")
    
    # Demo conversation
    messages = [
        "Hello! Can you help me understand what Google ADK-Web is?",
        "What are the main benefits of using ADK-Web for building conversational agents?",
        "Can you give me an example of how to integrate ADK-Web with a web application?"
    ]
    
    try:
        for i, message in enumerate(messages, 1):
            print(f"\n--- Message {i} ---")
            print(f"User: {message}")
            
            # Process message
            response = await agent.process_message(message, session_id)
            print(f"Assistant: {response.content}")
            
            # Show session info
            session = agent.get_session(session_id)
            print(f"Conversation length: {len(session.conversation_history)} messages")
            
            # Small delay between messages
            await asyncio.sleep(1)
        
        print(f"\n--- Streaming Demo ---")
        print("User: Tell me a short story about AI")
        
        # Demo streaming response
        chunks = []
        def collect_chunk(chunk):
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        
        await agent.stream_response(
            "Tell me a short story about AI", 
            session_id, 
            collect_chunk
        )
        print()  # New line after streaming
        
        # Show final session stats
        session = agent.get_session(session_id)
        print(f"\nFinal conversation length: {len(session.conversation_history)} messages")
        print(f"Session metadata: {session.metadata}")
        
    finally:
        # Clean up
        agent.close_session(session_id)
        print(f"\nSession {session_id} closed")
        print("Demo completed!")


if __name__ == "__main__":
    # Set up environment variables if needed
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        print("Note: GOOGLE_CLOUD_PROJECT not set, using mock responses")
        print("To use real Google ADK-Web, set the following environment variables:")
        print("  - GOOGLE_CLOUD_PROJECT")
        print("  - GOOGLE_APPLICATION_CREDENTIALS (path to service account key)")
        print()
    
    asyncio.run(main())