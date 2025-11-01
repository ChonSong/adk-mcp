@echo off
set GOOGLE_CLOUD_PROJECT=gen-lang-client-0652476115
set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\user\Documents\gen-lang-client-0652476115-036c67667706.json
set GOOGLE_CLOUD_LOCATION=us-central1

echo Starting ADK-MCP Server with Google Cloud credentials...
echo Project: %GOOGLE_CLOUD_PROJECT%
echo Credentials: %GOOGLE_APPLICATION_CREDENTIALS%

C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe examples/run_server.py