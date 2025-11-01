"""ADK-MCP: Agent Development Kit with Google ADK-Web integration and bidirectional streaming support."""

__version__ = "0.1.0"

from .streaming import BiDirectionalStream, StreamMessage, StreamHandler
from .executor import PythonExecutor
from .mock_services import MockGoogleCloudServices
from .google_adk import (
    GoogleADKWebAgent, 
    ADKWebConfig, 
    ADKWebStreamHandler,
    ConversationContext,
    create_adk_config_from_env
)

__all__ = [
    "BiDirectionalStream",
    "StreamMessage", 
    "StreamHandler",
    "PythonExecutor",
    "MockGoogleCloudServices",
    "GoogleADKWebAgent",
    "ADKWebConfig",
    "ADKWebStreamHandler", 
    "ConversationContext",
    "create_adk_config_from_env",
]
