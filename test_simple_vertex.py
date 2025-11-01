#!/usr/bin/env python3
"""Simple test to check Vertex AI API status."""

import os
from google.auth import default

def check_api_access():
    """Check if we can access Vertex AI APIs."""
    
    # Set environment variables
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'gen-lang-client-0652476115'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\user\Documents\gen-lang-client-0652476115-036c67667706.json'
    
    print("=== Checking Vertex AI API Access ===")
    
    try:
        # Test basic authentication
        credentials, project = default()
        print(f"✅ Authentication: {project}")
        
        # Test Vertex AI client creation
        from google.cloud import aiplatform_v1
        
        client = aiplatform_v1.ModelServiceClient()
        print("✅ Vertex AI client created")
        
        # Try to make a simple API call
        project_id = 'gen-lang-client-0652476115'
        location = 'us-central1'
        parent = f"projects/{project_id}/locations/{location}"
        
        print(f"Trying to list models in: {parent}")
        
        # This should tell us if the API is enabled
        request = aiplatform_v1.ListModelsRequest(parent=parent)
        response = client.list_models(request=request)
        
        print("✅ API call successful!")
        
        models = list(response)
        print(f"Found {len(models)} models")
        
        for i, model in enumerate(models[:3]):  # Show first 3
            print(f"  {i+1}. {model.display_name} ({model.name})")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # Check if it's an API not enabled error
        if "has not been used" in str(e) or "API has not been used" in str(e):
            print("\n💡 The Vertex AI API might not be enabled for this project.")
            print("   To enable it, run: gcloud services enable aiplatform.googleapis.com")
        elif "403" in str(e):
            print("\n💡 Permission denied - the service account needs more permissions.")
        elif "404" in str(e):
            print("\n💡 Resource not found - check project ID and location.")
            
        return False

def test_alternative_approach():
    """Test if we can use the legacy AI Platform."""
    print("\n=== Testing Legacy AI Platform ===")
    
    try:
        from google.cloud import aiplatform
        
        # Try the old approach
        aiplatform.init(
            project='gen-lang-client-0652476115',
            location='us-central1'
        )
        
        print("✅ Legacy AI Platform initialized")
        
        # Try to get endpoint list (simpler operation)
        endpoints = aiplatform.Endpoint.list()
        print(f"Found {len(list(endpoints))} endpoints")
        
        return True
        
    except Exception as e:
        print(f"❌ Legacy approach failed: {e}")
        return False

if __name__ == "__main__":
    api_works = check_api_access()
    
    if not api_works:
        test_alternative_approach()