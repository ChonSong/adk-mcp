"""Quick test script to verify server endpoints."""

import asyncio
import aiohttp
import json


async def test_endpoints():
    """Test the ADK-MCP server endpoints."""
    base_url = "http://localhost:8080"
    
    print("Testing ADK-MCP Server Endpoints\n")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        print("\n1. Testing /health endpoint...")
        async with session.get(f"{base_url}/health") as resp:
            data = await resp.json()
            print(f"   Status: {resp.status}")
            print(f"   Response: {json.dumps(data, indent=2)}")
        
        # Test execute endpoint
        print("\n2. Testing /execute endpoint...")
        code_payload = {
            "code": "print('Hello from ADK!')",
            "timeout": 10
        }
        async with session.post(
            f"{base_url}/execute",
            json=code_payload
        ) as resp:
            data = await resp.json()
            print(f"   Status: {resp.status}")
            print(f"   Success: {data.get('success')}")
            print(f"   Output: {data.get('output')}")
        
        # Test sentiment endpoint
        print("\n3. Testing /api/sentiment endpoint...")
        sentiment_payload = {"text": "This is a wonderful day!"}
        async with session.post(
            f"{base_url}/api/sentiment",
            json=sentiment_payload
        ) as resp:
            data = await resp.json()
            print(f"   Status: {resp.status}")
            print(f"   Sentiment Score: {data.get('sentiment_score')}")
            print(f"   Magnitude: {data.get('sentiment_magnitude')}")
        
        # Test translate endpoint
        print("\n4. Testing /api/translate endpoint...")
        translate_payload = {
            "text": "Hello world",
            "target_language": "es"
        }
        async with session.post(
            f"{base_url}/api/translate",
            json=translate_payload
        ) as resp:
            data = await resp.json()
            print(f"   Status: {resp.status}")
            print(f"   Translated: {data.get('translated_text')}")
        
        # Test generate endpoint
        print("\n5. Testing /api/generate endpoint...")
        generate_payload = {
            "prompt": "Tell me about AI",
            "max_tokens": 50
        }
        async with session.post(
            f"{base_url}/api/generate",
            json=generate_payload
        ) as resp:
            data = await resp.json()
            print(f"   Status: {resp.status}")
            print(f"   Generated: {data.get('generated_text')}")
    
    print("\n" + "=" * 50)
    print("✓ All endpoint tests completed!")


if __name__ == "__main__":
    asyncio.run(test_endpoints())
