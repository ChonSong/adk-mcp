"""Example: Mock Google Cloud services."""

import asyncio
from adk_mcp.mock_services import MockGoogleCloudServices


async def main():
    """Demonstrate mock Google Cloud services."""
    print("Mock Google Cloud Services Demo\n")
    print("=" * 50)
    
    services = MockGoogleCloudServices()
    
    # Example 1: Sentiment Analysis
    print("\n1. Sentiment Analysis:")
    texts = [
        "This is an amazing and wonderful day!",
        "I feel terrible and sad.",
        "The weather is okay."
    ]
    
    for text in texts:
        result = await services.analyze_sentiment(text)
        print(f"\nText: '{text}'")
        print(f"  Sentiment Score: {result.sentiment_score:.2f}")
        print(f"  Magnitude: {result.sentiment_magnitude:.2f}")
        print(f"  Language: {result.language}")
    
    # Example 2: Translation
    print("\n\n2. Text Translation:")
    original = "Hello, how are you?"
    languages = ["es", "fr", "de"]
    
    print(f"Original: '{original}'")
    for lang in languages:
        result = await services.translate_text(original, target_language=lang)
        print(f"  → {lang}: {result.translated_text}")
        print(f"     Confidence: {result.confidence:.2%}")
    
    # Example 3: Text Generation
    print("\n\n3. Text Generation:")
    prompts = [
        "Tell me about artificial intelligence",
        "What is machine learning?",
        "Explain neural networks"
    ]
    
    for prompt in prompts:
        result = await services.generate_text(prompt, max_tokens=50)
        print(f"\nPrompt: '{prompt}'")
        print(f"Generated: {result['generated_text']}")
        print(f"Tokens used: {result['tokens_used']}")
    
    # Example 4: Speech Services
    print("\n\n4. Speech Services:")
    
    # Speech to text
    audio_data = b"fake audio data for testing"
    stt_result = await services.speech_to_text(audio_data)
    print(f"\nSpeech-to-Text:")
    print(f"  Transcript: {stt_result['transcript']}")
    print(f"  Confidence: {stt_result['confidence']:.2%}")
    
    # Text to speech
    text = "Hello from ADK-MCP!"
    tts_result = await services.text_to_speech(text)
    print(f"\nText-to-Speech:")
    print(f"  Input: '{text}'")
    print(f"  Audio data size: {len(tts_result)} bytes")
    
    # Show request history
    print("\n\n5. Request History:")
    history = services.get_request_history()
    print(f"Total requests made: {len(history)}")
    for i, req in enumerate(history[:3], 1):
        print(f"  {i}. {req['operation']} at {req['timestamp']}")
    
    print("\n" + "=" * 50)
    print("✓ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
