"""Comprehensive UI template for ADK-MCP features."""


def get_comprehensive_ui_html(websocket_port: int = 8081) -> str:
    """
    Get complete HTML for comprehensive ADK-MCP UI.
    
    Args:
        websocket_port: WebSocket port for streaming
        
    Returns:
        HTML template as string
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ADK-MCP Control Panel</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .tabs {{
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            overflow-x: auto;
        }}
        
        .tab {{
            padding: 15px 25px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 14px;
            font-weight: 500;
            color: #6c757d;
            transition: all 0.3s;
            white-space: nowrap;
            border-bottom: 3px solid transparent;
        }}
        
        .tab:hover {{
            background: #e9ecef;
            color: #495057;
        }}
        
        .tab.active {{
            color: #667eea;
            border-bottom-color: #667eea;
            background: white;
        }}
        
        .tab-content {{
            display: none;
            padding: 30px;
            animation: fadeIn 0.3s;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        
        .card h3 {{
            color: #495057;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .status-item {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .status-item .label {{
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 8px;
        }}
        
        .status-item .value {{
            font-size: 1.5em;
            font-weight: 600;
            color: #495057;
        }}
        
        .status-item.healthy .value {{
            color: #28a745;
        }}
        
        .form-group {{
            margin-bottom: 20px;
        }}
        
        label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #495057;
        }}
        
        input[type="text"],
        input[type="number"],
        textarea,
        select {{
            width: 100%;
            padding: 12px;
            border: 1px solid #ced4da;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
            transition: border-color 0.3s;
        }}
        
        input:focus,
        textarea:focus,
        select:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        
        textarea {{
            resize: vertical;
            min-height: 100px;
            font-family: 'Courier New', monospace;
        }}
        
        .code-editor {{
            min-height: 200px;
            font-family: 'Courier New', monospace;
            background: #282c34;
            color: #abb2bf;
            padding: 15px;
        }}
        
        button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        
        button:active {{
            transform: translateY(0);
        }}
        
        button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        
        .output {{
            background: #282c34;
            color: #abb2bf;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 15px;
        }}
        
        .output.success {{
            border-left: 4px solid #28a745;
        }}
        
        .output.error {{
            border-left: 4px solid #dc3545;
            color: #ff6b6b;
        }}
        
        .messages {{
            height: 400px;
            overflow-y: auto;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 15px;
            background: white;
            margin-bottom: 15px;
        }}
        
        .message {{
            margin-bottom: 12px;
            padding: 12px;
            border-radius: 6px;
            animation: slideIn 0.3s;
        }}
        
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(-20px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}
        
        .message.sent {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            margin-right: 0;
            max-width: 70%;
            text-align: right;
        }}
        
        .message.received {{
            background: #f8f9fa;
            color: #495057;
            margin-right: auto;
            margin-left: 0;
            max-width: 70%;
        }}
        
        .message .timestamp {{
            font-size: 0.75em;
            opacity: 0.7;
            margin-top: 5px;
        }}
        
        .input-group {{
            display: flex;
            gap: 10px;
        }}
        
        .input-group input {{
            flex: 1;
        }}
        
        .history-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }}
        
        .history-item .operation {{
            font-weight: 600;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .history-item .timestamp {{
            font-size: 0.85em;
            color: #6c757d;
        }}
        
        .result-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .result-label {{
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 5px;
        }}
        
        .result-value {{
            font-size: 1.3em;
            font-weight: 600;
            color: #495057;
        }}
        
        .loading {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        .ws-status {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        
        .ws-status.connected {{
            background: #28a745;
            box-shadow: 0 0 8px #28a745;
        }}
        
        .ws-status.disconnected {{
            background: #dc3545;
        }}
        
        .flex {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .slider-container {{
            margin: 10px 0;
        }}
        
        .slider {{
            width: 100%;
            margin: 10px 0;
        }}
        
        .slider-value {{
            font-weight: 600;
            color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ADK-MCP Control Panel</h1>
            <p>Agent Development Kit - Model Context Protocol</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('dashboard')">Dashboard</button>
            <button class="tab" onclick="switchTab('streaming')">Streaming Chat</button>
            <button class="tab" onclick="switchTab('executor')">Code Executor</button>
            <button class="tab" onclick="switchTab('sentiment')">Sentiment Analysis</button>
            <button class="tab" onclick="switchTab('translate')">Translation</button>
            <button class="tab" onclick="switchTab('generate')">Text Generation</button>
            <button class="tab" onclick="switchTab('history')">API History</button>
        </div>
        
        <!-- Dashboard Tab -->
        <div id="dashboard" class="tab-content active">
            <div class="card">
                <h3>Server Status</h3>
                <div class="status-grid" id="statusGrid">
                    <div class="status-item">
                        <div class="label">Loading...</div>
                        <div class="value">...</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>Quick Info</h3>
                <p style="color: #6c757d; line-height: 1.6;">
                    Welcome to ADK-MCP Control Panel! This interface provides access to all features including:
                    <strong>bidirectional streaming</strong>, <strong>Python code execution</strong>, 
                    <strong>sentiment analysis</strong>, <strong>translation</strong>, and <strong>text generation</strong>.
                </p>
                <p style="color: #6c757d; margin-top: 10px;">
                    WebSocket endpoint: <code style="background: #e9ecef; padding: 4px 8px; border-radius: 4px;">ws://localhost:{websocket_port}</code>
                </p>
            </div>
        </div>
        
        <!-- Streaming Chat Tab -->
        <div id="streaming" class="tab-content">
            <div class="card">
                <h3>
                    <span class="ws-status disconnected" id="wsStatus"></span>
                    Bidirectional Streaming Chat
                </h3>
                <div class="messages" id="chatMessages"></div>
                <div class="input-group">
                    <input type="text" id="chatInput" placeholder="Type a message..." onkeypress="if(event.key==='Enter') sendChatMessage()">
                    <button onclick="sendChatMessage()">Send</button>
                </div>
            </div>
        </div>
        
        <!-- Code Executor Tab -->
        <div id="executor" class="tab-content">
            <div class="card">
                <h3>Python Code Executor</h3>
                <div class="form-group">
                    <label>Python Code</label>
                    <textarea id="codeInput" class="code-editor" placeholder="# Enter Python code here
print('Hello from ADK-MCP!')
result = 2 + 2
print(f'Result: {{result}}')"># Example: Calculate fibonacci
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

print(f"Fibonacci(10) = {{fib(10)}}")</textarea>
                </div>
                <div class="form-group">
                    <label>Timeout (seconds)</label>
                    <input type="number" id="codeTimeout" value="30" min="1" max="300">
                </div>
                <button onclick="executeCode()" id="execButton">Execute Code</button>
                <div id="codeOutput"></div>
            </div>
        </div>
        
        <!-- Sentiment Analysis Tab -->
        <div id="sentiment" class="tab-content">
            <div class="card">
                <h3>Sentiment Analysis</h3>
                <div class="form-group">
                    <label>Text to Analyze</label>
                    <textarea id="sentimentInput" placeholder="Enter text to analyze sentiment...">This is a wonderful day! I'm feeling great and everything is going perfectly.</textarea>
                </div>
                <button onclick="analyzeSentiment()" id="sentimentButton">Analyze Sentiment</button>
                <div id="sentimentOutput"></div>
            </div>
        </div>
        
        <!-- Translation Tab -->
        <div id="translate" class="tab-content">
            <div class="card">
                <h3>Text Translation</h3>
                <div class="form-group">
                    <label>Text to Translate</label>
                    <textarea id="translateInput" placeholder="Enter text to translate...">Hello, how are you today? I hope you're having a great day!</textarea>
                </div>
                <div class="form-group">
                    <label>Source Language (optional)</label>
                    <input type="text" id="sourceLang" placeholder="e.g., en (auto-detect if empty)">
                </div>
                <div class="form-group">
                    <label>Target Language</label>
                    <select id="targetLang">
                        <option value="es">Spanish (es)</option>
                        <option value="fr">French (fr)</option>
                        <option value="de">German (de)</option>
                        <option value="it">Italian (it)</option>
                        <option value="pt">Portuguese (pt)</option>
                        <option value="ru">Russian (ru)</option>
                        <option value="ja">Japanese (ja)</option>
                        <option value="ko">Korean (ko)</option>
                        <option value="zh">Chinese (zh)</option>
                        <option value="ar">Arabic (ar)</option>
                    </select>
                </div>
                <button onclick="translateText()" id="translateButton">Translate</button>
                <div id="translateOutput"></div>
            </div>
        </div>
        
        <!-- Text Generation Tab -->
        <div id="generate" class="tab-content">
            <div class="card">
                <h3>Text Generation</h3>
                <div class="form-group">
                    <label>Prompt</label>
                    <textarea id="generatePrompt" placeholder="Enter your prompt...">Tell me an interesting fact about artificial intelligence and machine learning.</textarea>
                </div>
                <div class="form-group">
                    <label>Max Tokens: <span class="slider-value" id="maxTokensValue">100</span></label>
                    <input type="range" id="maxTokens" class="slider" min="10" max="500" value="100" 
                           oninput="document.getElementById('maxTokensValue').textContent = this.value">
                </div>
                <div class="form-group">
                    <label>Temperature: <span class="slider-value" id="temperatureValue">0.7</span></label>
                    <input type="range" id="temperature" class="slider" min="0" max="1" step="0.1" value="0.7"
                           oninput="document.getElementById('temperatureValue').textContent = this.value">
                </div>
                <button onclick="generateText()" id="generateButton">Generate Text</button>
                <div id="generateOutput"></div>
            </div>
        </div>
        
        <!-- API History Tab -->
        <div id="history" class="tab-content">
            <div class="card">
                <h3>Mock API Request History</h3>
                <button onclick="loadHistory()" style="margin-bottom: 15px;">Refresh History</button>
                <button onclick="clearHistory()" style="margin-bottom: 15px; background: #dc3545;">Clear History</button>
                <div id="historyList"></div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let isConnected = false;
        
        // Switch tabs
        function switchTab(tabName) {{
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(content => {{
                content.classList.remove('active');
            }});
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            // Load data for specific tabs
            if (tabName === 'dashboard') {{
                loadDashboard();
            }} else if (tabName === 'streaming') {{
                connectWebSocket();
            }} else if (tabName === 'history') {{
                loadHistory();
            }}
        }}
        
        // Load dashboard data
        async function loadDashboard() {{
            try {{
                const response = await fetch('/health');
                const data = await response.json();
                
                const statusGrid = document.getElementById('statusGrid');
                statusGrid.innerHTML = `
                    <div class="status-item healthy">
                        <div class="label">Server Status</div>
                        <div class="value">${{data.status || 'Unknown'}}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Active Streams</div>
                        <div class="value">${{data.active_streams || 0}}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Executor</div>
                        <div class="value">${{data.executor_enabled ? '✓ Enabled' : '✗ Disabled'}}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Mock Services</div>
                        <div class="value">${{data.mock_services_enabled ? '✓ Enabled' : '✗ Disabled'}}</div>
                    </div>
                `;
            }} catch (error) {{
                console.error('Failed to load dashboard:', error);
                document.getElementById('statusGrid').innerHTML = `
                    <div class="status-item">
                        <div class="label">Error</div>
                        <div class="value">Failed to load status</div>
                    </div>
                `;
            }}
        }}
        
        // WebSocket connection
        function connectWebSocket() {{
            if (isConnected) return;
            
            ws = new WebSocket('ws://localhost:{websocket_port}');
            
            ws.onopen = () => {{
                isConnected = true;
                document.getElementById('wsStatus').className = 'ws-status connected';
                addChatMessage('System', 'Connected to WebSocket', false);
            }};
            
            ws.onmessage = (event) => {{
                try {{
                    const message = JSON.parse(event.data);
                    addChatMessage('Server', message.content || event.data, false);
                }} catch (e) {{
                    addChatMessage('Server', event.data, false);
                }}
            }};
            
            ws.onerror = (error) => {{
                console.error('WebSocket error:', error);
                addChatMessage('System', 'WebSocket error occurred', false);
            }};
            
            ws.onclose = () => {{
                isConnected = false;
                document.getElementById('wsStatus').className = 'ws-status disconnected';
                addChatMessage('System', 'Disconnected from WebSocket', false);
            }};
        }}
        
        function addChatMessage(sender, content, isSent) {{
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (isSent ? 'sent' : 'received');
            
            const now = new Date().toLocaleTimeString();
            messageDiv.innerHTML = `
                <div><strong>${{sender}}:</strong> ${{content}}</div>
                <div class="timestamp">${{now}}</div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }}
        
        function sendChatMessage() {{
            const input = document.getElementById('chatInput');
            const content = input.value.trim();
            
            if (!content) return;
            
            if (!isConnected) {{
                alert('Not connected to WebSocket. Please wait for connection.');
                return;
            }}
            
            const message = {{
                id: Date.now().toString(),
                content: content,
                timestamp: new Date().toISOString(),
                message_type: 'text',
                metadata: {{}}
            }};
            
            ws.send(JSON.stringify(message));
            addChatMessage('You', content, true);
            input.value = '';
        }}
        
        // Execute Python code
        async function executeCode() {{
            const code = document.getElementById('codeInput').value;
            const timeout = parseInt(document.getElementById('codeTimeout').value);
            const button = document.getElementById('execButton');
            const output = document.getElementById('codeOutput');
            
            button.disabled = true;
            button.innerHTML = '<span class="loading"></span> Executing...';
            
            try {{
                const response = await fetch('/execute', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ code, timeout }})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    output.className = 'output success';
                    output.textContent = result.output || '(No output)';
                }} else {{
                    output.className = 'output error';
                    output.textContent = 'Error: ' + (result.error || 'Unknown error');
                }}
            }} catch (error) {{
                output.className = 'output error';
                output.textContent = 'Request failed: ' + error.message;
            }} finally {{
                button.disabled = false;
                button.textContent = 'Execute Code';
            }}
        }}
        
        // Analyze sentiment
        async function analyzeSentiment() {{
            const text = document.getElementById('sentimentInput').value;
            const button = document.getElementById('sentimentButton');
            const output = document.getElementById('sentimentOutput');
            
            button.disabled = true;
            button.innerHTML = '<span class="loading"></span> Analyzing...';
            
            try {{
                const response = await fetch('/api/sentiment', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ text }})
                }});
                
                const result = await response.json();
                
                output.innerHTML = `
                    <div class="result-card">
                        <div class="result-label">Sentiment Score</div>
                        <div class="result-value" style="color: ${{result.sentiment_score > 0 ? '#28a745' : result.sentiment_score < 0 ? '#dc3545' : '#6c757d'}}">${{result.sentiment_score?.toFixed(3) || 'N/A'}}</div>
                    </div>
                    <div class="result-card">
                        <div class="result-label">Magnitude</div>
                        <div class="result-value">${{result.sentiment_magnitude?.toFixed(3) || 'N/A'}}</div>
                    </div>
                    <div class="result-card">
                        <div class="result-label">Language</div>
                        <div class="result-value">${{result.language || 'Unknown'}}</div>
                    </div>
                    <div class="result-card">
                        <div class="result-label">Entities</div>
                        <div class="result-value">${{result.entities?.length || 0}} detected</div>
                    </div>
                `;
            }} catch (error) {{
                output.className = 'output error';
                output.textContent = 'Request failed: ' + error.message;
            }} finally {{
                button.disabled = false;
                button.textContent = 'Analyze Sentiment';
            }}
        }}
        
        // Translate text
        async function translateText() {{
            const text = document.getElementById('translateInput').value;
            const sourceLang = document.getElementById('sourceLang').value || null;
            const targetLang = document.getElementById('targetLang').value;
            const button = document.getElementById('translateButton');
            const output = document.getElementById('translateOutput');
            
            button.disabled = true;
            button.innerHTML = '<span class="loading"></span> Translating...';
            
            try {{
                const response = await fetch('/api/translate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ 
                        text, 
                        target_language: targetLang,
                        source_language: sourceLang 
                    }})
                }});
                
                const result = await response.json();
                
                output.innerHTML = `
                    <div class="result-card">
                        <div class="result-label">Original Text</div>
                        <div class="result-value" style="font-size: 1em;">${{text}}</div>
                    </div>
                    <div class="result-card">
                        <div class="result-label">Translated Text (${{targetLang}})</div>
                        <div class="result-value" style="font-size: 1.1em; color: #667eea;">${{result.translated_text || 'N/A'}}</div>
                    </div>
                    <div class="result-card">
                        <div class="result-label">Confidence</div>
                        <div class="result-value">${{(result.confidence * 100).toFixed(1)}}%</div>
                    </div>
                `;
            }} catch (error) {{
                output.className = 'output error';
                output.textContent = 'Request failed: ' + error.message;
            }} finally {{
                button.disabled = false;
                button.textContent = 'Translate';
            }}
        }}
        
        // Generate text
        async function generateText() {{
            const prompt = document.getElementById('generatePrompt').value;
            const maxTokens = parseInt(document.getElementById('maxTokens').value);
            const temperature = parseFloat(document.getElementById('temperature').value);
            const button = document.getElementById('generateButton');
            const output = document.getElementById('generateOutput');
            
            button.disabled = true;
            button.innerHTML = '<span class="loading"></span> Generating...';
            
            try {{
                const response = await fetch('/api/generate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ 
                        prompt, 
                        max_tokens: maxTokens,
                        temperature 
                    }})
                }});
                
                const result = await response.json();
                
                output.innerHTML = `
                    <div class="result-card">
                        <div class="result-label">Generated Text</div>
                        <div class="result-value" style="font-size: 1em; line-height: 1.6;">${{result.generated_text || 'N/A'}}</div>
                    </div>
                    <div class="result-card">
                        <div class="result-label">Tokens Used</div>
                        <div class="result-value">${{result.tokens_used || 0}} / ${{maxTokens}}</div>
                    </div>
                `;
            }} catch (error) {{
                output.className = 'output error';
                output.textContent = 'Request failed: ' + error.message;
            }} finally {{
                button.disabled = false;
                button.textContent = 'Generate Text';
            }}
        }}
        
        // Load API history
        async function loadHistory() {{
            const historyList = document.getElementById('historyList');
            historyList.innerHTML = '<p style="color: #6c757d;">Loading history...</p>';
            
            try {{
                // Note: This requires a new endpoint to get history
                // For now, we'll show a placeholder
                historyList.innerHTML = '<p style="color: #6c757d;">API history tracking is available through the MockGoogleCloudServices. Use the get_request_history() method in Python code to access history data.</p>';
            }} catch (error) {{
                historyList.innerHTML = '<p style="color: #dc3545;">Failed to load history: ' + error.message + '</p>';
            }}
        }}
        
        async function clearHistory() {{
            if (confirm('Are you sure you want to clear the API history?')) {{
                document.getElementById('historyList').innerHTML = '<p style="color: #28a745;">History cleared (note: this is a placeholder - implement server endpoint to actually clear history)</p>';
            }}
        }}
        
        // Initialize dashboard on load
        window.addEventListener('load', () => {{
            loadDashboard();
            // Auto-refresh dashboard every 10 seconds
            setInterval(() => {{
                if (document.getElementById('dashboard').classList.contains('active')) {{
                    loadDashboard();
                }}
            }}, 10000);
        }});
    </script>
</body>
</html>
    """
