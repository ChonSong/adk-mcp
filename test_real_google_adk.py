#!/usr/bin/env python3
"""Test the real Google ADK-Web integration."""

import requests
import json

def test_google_adk_chat():
    """Test the Google ADK-Web chat endpoint with real Vertex AI."""
    print("=== Testing Google ADK-Web Chat (Real Vertex AI) ===")
    url = "http://localhost:9090/adk/chat"
    
    payload = {
        "message": "Hello! Can you explain what Android development is in simple terms?"
    }
    
    try:
        print("Sending request to Google ADK-Web...")
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
            
            # Check if it's a real response vs mock
            content = response_data.get("content", "")
            if "I'm having trouble generating a response right now" in content:
                print("\n❌ Still getting mock response - Google Cloud may not be properly configured")
            else:
                print("\n✅ Real Google ADK-Web response received!")
        else:
            print(f"Error response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("Request timed out - this might indicate the real API is being called")
    except Exception as e:
        print(f"Error: {e}")

def test_google_adk_with_session():
    """Test Google ADK-Web with session management."""
    print("\n=== Testing Google ADK-Web with Session Management ===")
    
    # Start session
    start_url = "http://localhost:9090/adk/session/start"
    start_payload = {"user_id": "real_test_user"}
    
    try:
        response = requests.post(start_url, json=start_payload)
        print(f"Start Session - Status Code: {response.status_code}")
        session_data = response.json()
        session_id = session_data.get("session_id")
        print(f"Session ID: {session_id}")
        
        if session_id:
            # Send chat message with session
            chat_url = "http://localhost:9090/adk/chat"
            chat_payload = {
                "message": "What are the key components of an Android app?",
                "session_id": session_id
            }
            
            print("\nSending chat message with session...")
            response = requests.post(chat_url, json=chat_payload, timeout=30)
            print(f"Chat Response - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                chat_data = response.json()
                print(f"Chat Response: {json.dumps(chat_data, indent=2)}")
            
            # End session
            end_url = "http://localhost:9090/adk/session/end"
            end_payload = {"session_id": session_id}
            
            response = requests.post(end_url, json=end_payload)
            print(f"\nEnd Session - Status Code: {response.status_code}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_google_adk_chat()
    test_google_adk_with_session()