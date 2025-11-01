#!/usr/bin/env python3
"""Simple test for the execute endpoint."""

import requests
import json

def test_execute_endpoint():
    """Test the Python code execution endpoint."""
    url = "http://localhost:9090/execute"
    
    # Simple Python code to execute
    code = """
print('Hello from ADK-MCP server!')
result = 2 + 2
print(f'2 + 2 = {result}')
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
print(f'Sum of {numbers} = {total}')
"""
    
    payload = {
        "code": code
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_execute_endpoint()