#!/usr/bin/env python3
"""Test script for ADK Runner.run_live() integration."""

import asyncio
import logging
from src.adk_mcp.adk_voice_agent import GoogleADKVoiceAgent, ADKVoiceSession
from src.adk_mcp.google_adk import create_adk_config_from_env

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages = []
    
    async def send(self, message):
        self.messages.append(message)
        logger.info(f"Mock WebSocket sent: {message}")


async def test_adk_voice_agent():
    """Test ADK voice agent initialization and basic functionality."""
    try:
        # Create configuration
        config = create_adk_config_from_env()
        
        # Initialize voice agent
        voice_agent = GoogleADKVoiceAgent(config)
        await voice_agent.initialize()
        
        logger.info("✅ ADK Voice Agent initialized successfully")
        
        # Test session creation
        mock_websocket = MockWebSocket()
        session = await voice_agent.create_voice_session(mock_websocket, user_id="test_user")
        
        logger.info(f"✅ Voice session created: {session.session_id}")
        
        # Test session stats
        stats = voice_agent.get_session_stats()
        logger.info(f"✅ Session stats: {stats}")
        
        # Cleanup
        await voice_agent.close_voice_session(session)
        logger.info("✅ Voice session closed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def test_voice_code_execution():
    """Test voice-aware code execution tool."""
    try:
        from src.adk_mcp.adk_voice_agent import VoiceCodeExecutionTool
        
        # Create code execution tool
        code_tool = VoiceCodeExecutionTool()
        
        # Test code execution
        result = await code_tool.execute_code_with_voice_response(
            code="print('Hello from ADK!')",
            session_id="test_session"
        )
        
        logger.info(f"✅ Code execution result: {result}")
        
        return result["status"] == "success"
        
    except Exception as e:
        logger.error(f"❌ Code execution test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Starting ADK integration tests...")
    
    tests = [
        ("ADK Voice Agent", test_adk_voice_agent),
        ("Voice Code Execution", test_voice_code_execution),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running test: {test_name}")
        result = await test_func()
        results.append((test_name, result))
    
    # Summary
    logger.info("\n📊 Test Results:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        logger.info("🎉 All tests passed! ADK integration is working.")
    else:
        logger.error("💥 Some tests failed. Check the logs above.")


if __name__ == "__main__":
    asyncio.run(main())