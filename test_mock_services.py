#!/usr/bin/env python3
"""Test the mock services endpoints."""

import requests
import json

def test_sentiment_analysis():
    """Test sentiment analysis endpoint."""
    print("=== Testing Sentiment Analysis ===")
    url = "http://localhost:9090/api/sentiment"
    
    payload = {
        "text": "I love using this ADK-MCP server! It's working great."
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_translation():
    """Test translation endpoint."""
    print("\n=== Testing Translation ===")
    url = "http://localhost:9090/api/translate"
    
    payload = {
        "text": "Hello, how are you?",
        "target_language": "es",
        "source_language": "en"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_text_generation():
    """Test text generation endpoint."""
    print("\n=== Testing Text Generation ===")
    url = "http://localhost:9090/api/generate"
    
    payload = {
        "prompt": "Explain Android development in simple terms",
        "max_tokens": 150,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_adk_session_management():
    """Test ADK session management."""
    print("\n=== Testing ADK Session Management ===")
    
    # Start session
    start_url = "http://localhost:9090/adk/session/start"
    start_payload = {"user_id": "test_user_123"}
    
    try:
        response = requests.post(start_url, json=start_payload)
        print(f"Start Session - Status Code: {response.status_code}")
        session_data = response.json()
        print(f"Start Session Response: {json.dumps(session_data, indent=2)}")
        
        session_id = session_data.get("session_id")
        
        if session_id:
            # End session
            end_url = "http://localhost:9090/adk/session/end"
            end_payload = {"session_id": session_id}
            
            response = requests.post(end_url, json=end_payload)
            print(f"End Session - Status Code: {response.status_code}")
            print(f"End Session Response: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sentiment_analysis()
    test_translation()
    test_text_generation()
    test_adk_session_management()