#!/usr/bin/env python3
"""Test what Vertex AI models are available."""

import os
from google.cloud import aiplatform

def test_available_models():
    """Test what models are available in different regions."""
    
    # Set environment variables
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'gen-lang-client-0652476115'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\user\Documents\gen-lang-client-0652476115-036c67667706.json'
    
    project_id = 'gen-lang-client-0652476115'
    regions = ['us-central1', 'us-east1', 'us-west1', 'europe-west1']
    
    for region in regions:
        print(f"\n=== Testing region: {region} ===")
        
        try:
            # Initialize AI Platform for this region
            aiplatform.init(project=project_id, location=region)
            
            # Try to list models
            try:
                client = aiplatform.gapic.ModelServiceClient(
                    client_options={"api_endpoint": f"{region}-aiplatform.googleapis.com"}
                )
                
                parent = f"projects/{project_id}/locations/{region}"
                
                # List models
                models = client.list_models(parent=parent)
                
                print(f"✅ Successfully connected to {region}")
                
                model_count = 0
                for model in models:
                    print(f"  Model: {model.name}")
                    model_count += 1
                    if model_count >= 5:  # Limit output
                        break
                
                if model_count == 0:
                    print("  No models found")
                    
            except Exception as e:
                print(f"❌ Error listing models in {region}: {e}")
                
        except Exception as e:
            print(f"❌ Error initializing {region}: {e}")

def test_generative_models():
    """Test specific generative models."""
    print("\n=== Testing Generative Models ===")
    
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'gen-lang-client-0652476115'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\user\Documents\gen-lang-client-0652476115-036c67667706.json'
    
    project_id = 'gen-lang-client-0652476115'
    region = 'us-central1'
    
    # Common model names to try
    models_to_try = [
        'gemini-pro',
        'gemini-1.5-pro',
        'gemini-1.0-pro',
        'text-bison',
        'text-bison@001',
        'chat-bison',
        'chat-bison@001'
    ]
    
    try:
        aiplatform.init(project=project_id, location=region)
        
        for model_name in models_to_try:
            print(f"\nTrying model: {model_name}")
            
            try:
                from vertexai.generative_models import GenerativeModel
                model = GenerativeModel(model_name)
                
                # Try a simple generation
                response = model.generate_content("Hello")
                print(f"✅ {model_name}: {response.text[:50]}...")
                break  # If one works, we're good
                
            except Exception as e:
                print(f"❌ {model_name}: {e}")
                
    except Exception as e:
        print(f"❌ Error initializing generative models: {e}")

if __name__ == "__main__":
    test_available_models()
    test_generative_models()