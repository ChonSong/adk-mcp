#!/usr/bin/env python3
"""Test the streaming endpoint."""

import requests
import json

def test_streaming_endpoint():
    """Test the streaming endpoint."""
    url = "http://localhost:9090/stream"
    
    payload = {
        "message": "Tell me about Android development with streaming response"
    }
    
    try:
        response = requests.post(url, json=payload, stream=True)
        print(f"Status Code: {response.status_code}")
        print("Streaming response:")
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    print(f"Chunk: {data}")
                except json.JSONDecodeError:
                    print(f"Raw line: {line.decode('utf-8')}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_streaming_endpoint()