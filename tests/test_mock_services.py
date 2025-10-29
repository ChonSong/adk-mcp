"""Tests for mock Google Cloud services."""

import pytest
from adk_mcp.mock_services import MockGoogleCloudServices


@pytest.mark.asyncio
async def test_sentiment_analysis():
    """Test mock sentiment analysis."""
    services = MockGoogleCloudServices()
    
    result = await services.analyze_sentiment("This is a great day!")
    
    assert result.sentiment_score is not None
    assert result.sentiment_magnitude is not None
    assert result.language == "en"
    assert isinstance(result.entities, list)


@pytest.mark.asyncio
async def test_sentiment_positive():
    """Test sentiment analysis with positive text."""
    services = MockGoogleCloudServices()
    
    result = await services.analyze_sentiment("This is amazing and wonderful!")
    
    # Should have positive sentiment
    assert result.sentiment_score > 0


@pytest.mark.asyncio
async def test_sentiment_negative():
    """Test sentiment analysis with negative text."""
    services = MockGoogleCloudServices()
    
    result = await services.analyze_sentiment("This is terrible and awful!")
    
    # Should have negative sentiment
    assert result.sentiment_score < 0


@pytest.mark.asyncio
async def test_translation():
    """Test mock text translation."""
    services = MockGoogleCloudServices()
    
    result = await services.translate_text(
        "Hello world",
        target_language="es"
    )
    
    assert result.translated_text is not None
    assert result.target_language == "es"
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_text_generation():
    """Test mock text generation."""
    services = MockGoogleCloudServices()
    
    result = await services.generate_text(
        "Write a story about",
        max_tokens=50
    )
    
    assert "generated_text" in result
    assert "tokens_used" in result
    assert result["tokens_used"] <= 50


@pytest.mark.asyncio
async def test_speech_to_text():
    """Test mock speech-to-text."""
    services = MockGoogleCloudServices()
    
    audio_data = b"fake audio data"
    result = await services.speech_to_text(audio_data)
    
    assert "transcript" in result
    assert "confidence" in result
    assert result["language"] == "en-US"


@pytest.mark.asyncio
async def test_text_to_speech():
    """Test mock text-to-speech."""
    services = MockGoogleCloudServices()
    
    audio = await services.text_to_speech("Hello world")
    
    assert isinstance(audio, bytes)
    assert len(audio) > 0


def test_request_history():
    """Test request history tracking."""
    services = MockGoogleCloudServices()
    
    # Make some requests
    import asyncio
    asyncio.run(services.analyze_sentiment("Test"))
    asyncio.run(services.translate_text("Test", "es"))
    
    history = services.get_request_history()
    assert len(history) == 2
    
    # Clear history
    services.clear_history()
    assert len(services.get_request_history()) == 0
