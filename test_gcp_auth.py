#!/usr/bin/env python3
"""Test Google Cloud authentication and available services."""

import os
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

def test_authentication():
    """Test if Google Cloud authentication is working."""
    print("=== Testing Google Cloud Authentication ===")
    
    # Set environment variables
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'gen-lang-client-0652476115'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\user\Documents\gen-lang-client-0652476115-036c67667706.json'
    
    try:
        credentials, project = default()
        print(f"✅ Authentication successful!")
        print(f"Project ID: {project}")
        print(f"Credentials type: {type(credentials)}")
        
        # Try to get service account email
        if hasattr(credentials, 'service_account_email'):
            print(f"Service Account: {credentials.service_account_email}")
        
        return True, credentials, project
        
    except DefaultCredentialsError as e:
        print(f"❌ Authentication failed: {e}")
        return False, None, None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False, None, None

def test_vertex_ai_access():
    """Test if we can access Vertex AI."""
    print("\n=== Testing Vertex AI Access ===")
    
    try:
        from google.cloud import aiplatform
        
        # Initialize AI Platform
        aiplatform.init(
            project='gen-lang-client-0652476115',
            location='us-central1'
        )
        
        print("✅ Vertex AI client initialized")
        
        # Try to list models (this requires less permissions)
        try:
            from vertexai.generative_models import GenerativeModel
            model = GenerativeModel('gemini-1.5-pro')
            print("✅ Gemini model object created")
            
            # Try a simple generation (this will show the actual permission error)
            try:
                response = model.generate_content("Hello")
                print(f"✅ Generation successful: {response.text[:50]}...")
                return True
            except Exception as e:
                print(f"❌ Generation failed: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Model creation failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Vertex AI initialization failed: {e}")
        return False

def test_alternative_apis():
    """Test alternative Google APIs that might work."""
    print("\n=== Testing Alternative Google APIs ===")
    
    # Test Google Generative AI (different from Vertex AI)
    try:
        import google.generativeai as genai
        
        # This uses a different authentication method
        print("✅ Google Generative AI library available")
        
        # Note: This would require an API key, not service account
        print("ℹ️  Google Generative AI requires API key authentication")
        
    except ImportError:
        print("❌ Google Generative AI library not installed")
    
    # Test Cloud Translation
    try:
        from google.cloud import translate_v2 as translate
        
        translate_client = translate.Client()
        print("✅ Cloud Translation client created")
        
        # Try a simple translation
        try:
            result = translate_client.translate('Hello', target_language='es')
            print(f"✅ Translation successful: {result['translatedText']}")
        except Exception as e:
            print(f"❌ Translation failed: {e}")
            
    except Exception as e:
        print(f"❌ Cloud Translation failed: {e}")

if __name__ == "__main__":
    auth_success, credentials, project = test_authentication()
    
    if auth_success:
        test_vertex_ai_access()
        test_alternative_apis()
    else:
        print("\n❌ Cannot proceed without authentication")