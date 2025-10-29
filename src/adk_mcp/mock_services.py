"""Mocked Google Cloud services for ADK-MCP."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import uuid
from datetime import datetime, timezone
import random


@dataclass
class MockTextAnalysisResult:
    """Mock result from text analysis."""
    
    sentiment_score: float
    sentiment_magnitude: float
    language: str
    entities: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MockTranslationResult:
    """Mock result from translation."""
    
    translated_text: str
    detected_source_language: str
    target_language: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MockGoogleCloudServices:
    """Mocked Google Cloud services for testing and development."""
    
    def __init__(self):
        self.request_history: List[Dict[str, Any]] = []
    
    async def analyze_sentiment(self, text: str) -> MockTextAnalysisResult:
        """
        Mock sentiment analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            MockTextAnalysisResult with sentiment data
        """
        self._log_request("analyze_sentiment", {"text": text})
        
        # Generate mock sentiment based on simple heuristics
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "happy"]
        negative_words = ["bad", "terrible", "awful", "horrible", "sad", "angry"]
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            score = random.uniform(0.3, 0.9)
        elif neg_count > pos_count:
            score = random.uniform(-0.9, -0.3)
        else:
            score = random.uniform(-0.2, 0.2)
        
        magnitude = random.uniform(0.5, 2.0)
        
        # Mock entity extraction
        entities = []
        words = text.split()
        if len(words) > 3:
            entities.append({
                "name": words[0],
                "type": "UNKNOWN",
                "salience": random.uniform(0.1, 0.9)
            })
        
        return MockTextAnalysisResult(
            sentiment_score=score,
            sentiment_magnitude=magnitude,
            language="en",
            entities=entities
        )
    
    async def translate_text(
        self, 
        text: str, 
        target_language: str = "en",
        source_language: Optional[str] = None
    ) -> MockTranslationResult:
        """
        Mock text translation.
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (auto-detect if None)
            
        Returns:
            MockTranslationResult
        """
        self._log_request("translate_text", {
            "text": text,
            "target_language": target_language,
            "source_language": source_language
        })
        
        # Mock translation by adding prefix
        detected_source = source_language or "auto"
        translated = f"[TRANSLATED to {target_language}] {text}"
        
        return MockTranslationResult(
            translated_text=translated,
            detected_source_language=detected_source,
            target_language=target_language,
            confidence=random.uniform(0.85, 0.99)
        )
    
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Mock text generation (similar to Vertex AI or PaLM).
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Dictionary with generated text
        """
        self._log_request("generate_text", {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        })
        
        # Mock generation
        mock_responses = [
            "This is a mock generated response based on your prompt.",
            "Here is some AI-generated text for testing purposes.",
            "The system processed your request and generated this response.",
            "Mock AI response: Your input has been processed successfully."
        ]
        
        generated_text = random.choice(mock_responses)
        
        return {
            "generated_text": generated_text,
            "prompt": prompt,
            "tokens_used": random.randint(10, max_tokens),
            "finish_reason": "stop",
            "model": "mock-model-v1"
        }
    
    async def speech_to_text(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Mock speech-to-text conversion.
        
        Args:
            audio_data: Audio data bytes
            
        Returns:
            Dictionary with transcription
        """
        self._log_request("speech_to_text", {
            "audio_length": len(audio_data)
        })
        
        return {
            "transcript": "This is a mock transcription of the audio data.",
            "confidence": random.uniform(0.85, 0.98),
            "language": "en-US"
        }
    
    async def text_to_speech(self, text: str, voice: str = "en-US-Standard-A") -> bytes:
        """
        Mock text-to-speech conversion.
        
        Args:
            text: Text to convert
            voice: Voice to use
            
        Returns:
            Mock audio bytes
        """
        self._log_request("text_to_speech", {
            "text": text,
            "voice": voice
        })
        
        # Return mock audio data
        return b"MOCK_AUDIO_DATA_" + text.encode('utf-8')[:50]
    
    def _log_request(self, operation: str, params: Dict[str, Any]):
        """Log request for debugging/testing."""
        self.request_history.append({
            "operation": operation,
            "params": params,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4())
        })
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of all mock API requests."""
        return self.request_history.copy()
    
    def clear_history(self):
        """Clear request history."""
        self.request_history.clear()
