"""Android WebView bridge for ADK-MCP streaming."""

import json
from typing import Optional, Callable, Any, Dict
import asyncio


class AndroidWebViewBridge:
    """
    Bridge between ADK-MCP streaming and Android WebView.
    
    This class provides a JavaScript interface that can be injected into
    Android WebView to enable bidirectional communication between the
    native Android app and the web-based streaming interface.
    """
    
    def __init__(self, interface_name: str = "ADK"):
        """
        Initialize Android WebView bridge.
        
        Args:
            interface_name: Name of the JavaScript interface to inject
        """
        self.interface_name = interface_name
        self.message_callbacks: Dict[str, Callable] = {}
        self.is_connected = False
        
    def get_javascript_interface(self) -> str:
        """
        Get JavaScript code to inject into WebView.
        
        Returns:
            JavaScript code as string
        """
        return f"""
        window.{self.interface_name} = {{
            sendMessage: function(message) {{
                if (window.AndroidInterface) {{
                    window.AndroidInterface.receiveFromWeb(JSON.stringify(message));
                }}
            }},
            
            receiveMessage: function(messageJson) {{
                try {{
                    const message = JSON.parse(messageJson);
                    if (window.{self.interface_name}.onMessage) {{
                        window.{self.interface_name}.onMessage(message);
                    }}
                }} catch (e) {{
                    console.error('Error parsing message:', e);
                }}
            }},
            
            onMessage: null,
            
            setMessageHandler: function(handler) {{
                window.{self.interface_name}.onMessage = handler;
            }},
            
            isConnected: function() {{
                return window.AndroidInterface !== undefined;
            }}
        }};
        
        // Auto-connect on load
        if (window.AndroidInterface) {{
            console.log('{self.interface_name} bridge connected');
        }}
        """
    
    def get_html_template(self, title: str = "ADK Streaming Interface") -> str:
        """
        Get complete HTML template for WebView.
        
        Args:
            title: Page title
            
        Returns:
            HTML template as string
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    padding: 20px;
                }}
                
                .messages {{
                    height: 400px;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 10px;
                    margin-bottom: 20px;
                }}
                
                .message {{
                    margin-bottom: 10px;
                    padding: 10px;
                    border-radius: 4px;
                }}
                
                .message.sent {{
                    background: #e3f2fd;
                    text-align: right;
                }}
                
                .message.received {{
                    background: #f5f5f5;
                }}
                
                .input-area {{
                    display: flex;
                    gap: 10px;
                }}
                
                #messageInput {{
                    flex: 1;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                }}
                
                #sendButton {{
                    padding: 10px 20px;
                    background: #2196f3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                }}
                
                #sendButton:hover {{
                    background: #1976d2;
                }}
                
                .status {{
                    padding: 10px;
                    margin-bottom: 20px;
                    border-radius: 4px;
                    background: #4caf50;
                    color: white;
                    text-align: center;
                }}
                
                .status.disconnected {{
                    background: #f44336;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div id="status" class="status">Connected to ADK</div>
                <div class="messages" id="messages"></div>
                <div class="input-area">
                    <input type="text" id="messageInput" placeholder="Type a message...">
                    <button id="sendButton">Send</button>
                </div>
            </div>
            
            <script>
                {self.get_javascript_interface()}
                
                // UI handlers
                const messagesDiv = document.getElementById('messages');
                const messageInput = document.getElementById('messageInput');
                const sendButton = document.getElementById('sendButton');
                const statusDiv = document.getElementById('status');
                
                function addMessage(content, isSent) {{
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message ' + (isSent ? 'sent' : 'received');
                    messageDiv.textContent = content;
                    messagesDiv.appendChild(messageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }}
                
                function sendMessage() {{
                    const content = messageInput.value.trim();
                    if (content) {{
                        const message = {{
                            id: Date.now().toString(),
                            content: content,
                            timestamp: new Date().toISOString(),
                            message_type: 'text'
                        }};
                        
                        {self.interface_name}.sendMessage(message);
                        addMessage(content, true);
                        messageInput.value = '';
                    }}
                }}
                
                sendButton.addEventListener('click', sendMessage);
                messageInput.addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') {{
                        sendMessage();
                    }}
                }});
                
                // Set up message handler
                {self.interface_name}.setMessageHandler(function(message) {{
                    addMessage(message.content, false);
                }});
                
                // Update connection status
                if ({self.interface_name}.isConnected()) {{
                    statusDiv.textContent = 'Connected to ADK';
                    statusDiv.className = 'status';
                }} else {{
                    statusDiv.textContent = 'Not connected to native interface';
                    statusDiv.className = 'status disconnected';
                }}
            </script>
        </body>
        </html>
        """
    
    def register_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register callback for messages from WebView.
        
        Args:
            callback: Function to call when message received
        """
        self.message_callbacks['default'] = callback
    
    def send_to_webview(self, message: Dict[str, Any]) -> str:
        """
        Prepare message to send to WebView.
        
        Args:
            message: Message dictionary
            
        Returns:
            JavaScript code to execute in WebView
        """
        message_json = json.dumps(message)
        return f"window.{self.interface_name}.receiveMessage('{message_json}');"
    
    async def handle_message_from_webview(self, message_json: str):
        """
        Handle message received from WebView.
        
        Args:
            message_json: JSON string of message
        """
        try:
            message = json.loads(message_json)
            if 'default' in self.message_callbacks:
                callback = self.message_callbacks['default']
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
        except json.JSONDecodeError as e:
            print(f"Error decoding message: {e}")


# Android interface template for Kotlin/Java
ANDROID_INTERFACE_TEMPLATE = '''
/**
 * Android WebView interface for ADK-MCP streaming.
 * Add this class to your Android project.
 */
 
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject

class ADKWebInterface(private val webView: WebView, private val messageHandler: (JSONObject) -> Unit) {
    
    @JavascriptInterface
    fun receiveFromWeb(messageJson: String) {
        try {
            val message = JSONObject(messageJson)
            messageHandler(message)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
    
    fun sendToWeb(message: JSONObject) {
        webView.post {
            val js = "window.ADK.receiveMessage('${message.toString()}');"
            webView.evaluateJavascript(js, null)
        }
    }
}

/**
 * Usage example:
 * 
 * val webView = findViewById<WebView>(R.id.webview)
 * webView.settings.javaScriptEnabled = true
 * 
 * val adkInterface = ADKWebInterface(webView) { message ->
 *     // Handle message from web
 *     val content = message.getString("content")
 *     // Process message...
 * }
 * 
 * webView.addJavascriptInterface(adkInterface, "AndroidInterface")
 * webView.loadData(htmlContent, "text/html", "UTF-8")
 */
'''
