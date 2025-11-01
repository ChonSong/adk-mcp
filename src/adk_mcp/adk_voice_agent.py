"""Enhanced Google ADK Voice Agent with multi-agent system and session persistence."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, AsyncIterator, Callable
from dataclasses import dataclass, asdict

try:
    from google_adk import (
        LlmAgent, 
        SequentialAgent, 
        ParallelAgent, 
        LoopAgent,
        AgentTool,
        Session,
        ToolContext,
        run_live
    )
    ADK_AVAILABLE = True
except ImportError:
    # Fallback for when google-adk is not available
    ADK_AVAILABLE = False
    logging.warning("google-adk package not available, using fallback implementation")

from .voice_streaming import VoiceSession, VoiceMessage, AudioChunk
from .google_adk import GoogleADKWebAgent, ADKWebConfig
from .live_api_integration import SpeechProcessor
from .conversation_context import (
    PersistentConversationContext, 
    ConversationTurn, 
    ContextualResponseGenerator
)
from .voice_code_executor import VoiceCodeExecutor


@dataclass
class SessionState:
    """Enhanced session state with structured data storage."""
    
    # Core session info
    session_id: str
    user_id: Optional[str] = None
    
    # Conversation context
    current_debugging_step: Optional[str] = None
    current_topic: Optional[str] = None
    
    # Code execution context
    last_code_execution: Optional[Dict[str, Any]] = None
    execution_history: List[Dict[str, Any]] = None
    
    # User preferences (persistent across sessions)
    preferred_language: str = "python"
    preferred_android_api_level: Optional[int] = None
    
    # Working memory for complex tasks
    working_memory: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.execution_history is None:
            self.execution_history = []
        if self.working_memory is None:
            self.working_memory = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Create from dictionary."""
        return cls(**data)


class EnhancedVoiceSession(VoiceSession):
    """Enhanced voice session with ADK session integration."""
    
    def __init__(self, session_id: str, websocket, user_id: Optional[str] = None):
        super().__init__(session_id, websocket, user_id)
        self.adk_session: Optional['Session'] = None
        self.session_state = SessionState(session_id=session_id, user_id=user_id)
        self.events_log: List[Dict[str, Any]] = []
        self.conversation_memory = None  # Will be set by context manager
    
    async def initialize_adk_session(self):
        """Initialize ADK session for persistent context."""
        if ADK_AVAILABLE:
            self.adk_session = Session(session_id=self.session_id)
            # Initialize state with user preferences
            if self.user_id:
                self.adk_session.state[f"user:{self.user_id}:preferred_language"] = self.session_state.preferred_language
        
    async def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log event to session for debugging and context."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        self.events_log.append(event)
        
        if self.adk_session and ADK_AVAILABLE:
            self.adk_session.events.append(event)
    
    async def update_state(self, key: str, value: Any):
        """Update session state."""
        setattr(self.session_state, key, value)
        
        if self.adk_session and ADK_AVAILABLE:
            self.adk_session.state[key] = value
    
    async def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from session state."""
        if self.adk_session and ADK_AVAILABLE:
            return self.adk_session.state.get(key, default)
        return getattr(self.session_state, key, default)


class CodeExecutionTool:
    """Enhanced code execution tool with session state integration."""
    
    def __init__(self, executor):
        self.executor = executor
        self.logger = logging.getLogger(__name__)
    
    async def execute_code(
        self, 
        code: str, 
        context: Optional['ToolContext'] = None,
        session: Optional['EnhancedVoiceSession'] = None
    ) -> Dict[str, Any]:
        """Execute code with session state integration."""
        try:
            # Execute code using existing executor
            result = await self.executor.execute(code)
            
            # Log execution to session state
            execution_data = {
                "code": code,
                "result": result.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if session:
                await session.log_event("code_execution", execution_data)
                await session.update_state("last_code_execution", execution_data)
                session.session_state.execution_history.append(execution_data)
            
            if context and ADK_AVAILABLE:
                # Update ADK session state
                context.session.state["last_code_execution"] = execution_data
                context.session.state["execution_count"] = context.session.state.get("execution_count", 0) + 1
            
            return result.to_dict()
            
        except Exception as e:
            error_data = {
                "code": code,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if session:
                await session.log_event("code_execution_error", error_data)
            
            self.logger.error(f"Code execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "exit_code": -1
            }


class MultiAgentVoiceSystem:
    """Multi-agent system for complex Android development tasks."""
    
    def __init__(self, config: ADKWebConfig, code_executor):
        self.config = config
        self.code_executor = code_executor
        self.logger = logging.getLogger(__name__)
        
        # Initialize tools
        self.code_execution_tool = CodeExecutionTool(code_executor)
        self.voice_code_executor = VoiceCodeExecutor(code_executor)
        
        # Initialize agents if ADK is available
        if ADK_AVAILABLE:
            self._initialize_agents()
        else:
            self.logger.warning("ADK not available, using fallback single agent")
            self.fallback_agent = GoogleADKWebAgent(config)
    
    def _initialize_agents(self):
        """Initialize specialized agents for different tasks."""
        
        # 1. Router/Orchestrator Agent
        self.router_agent = LlmAgent(
            name="ADK_MCP_Router",
            model="gemini-2.5-pro",
            instruction="""You are a router agent for Android development assistance. 
            Analyze user queries and route them to the appropriate specialist:
            - Code generation/execution: Use code_expert_tool
            - Documentation/reference: Use docs_agent_tool  
            - Debugging/troubleshooting: Use bug_hunter_tool
            - General conversation: Handle directly
            
            Always maintain conversation context and provide helpful responses."""
        )
        
        # 2. Code Execution Agent
        self.code_expert = LlmAgent(
            name="Code_Expert",
            model="gemini-2.5-pro",
            instruction="""You are an expert Python code generator for Android development.
            Generate secure, efficient Python code to solve Android development problems.
            Always use the code_execution_tool to run and verify your code.
            Store execution results in session state for future reference.""",
            tools=[self._create_code_execution_tool()]
        )
        
        # 3. Documentation Agent
        self.docs_agent = LlmAgent(
            name="ADK_Docs_Agent", 
            model="gemini-2.5-pro",
            instruction="""You are an Android documentation expert.
            Provide accurate, up-to-date information about Android development,
            ADK features, and best practices. Reference official documentation
            and provide code examples when helpful."""
        )
        
        # 4. Troubleshooting Agent
        self.bug_hunter = LlmAgent(
            name="Bug_Hunter",
            model="gemini-2.5-pro", 
            instruction="""You are a debugging specialist for Android development.
            Analyze error messages, logs, and code to identify issues.
            Provide step-by-step troubleshooting solutions.
            Use session state to track debugging progress."""
        )
        
        # Create agent tools
        self.code_expert_tool = AgentTool(
            agent=self.code_expert,
            description="Generate and execute Python code for Android development problems"
        )
        
        self.docs_agent_tool = AgentTool(
            agent=self.docs_agent,
            description="Get Android development documentation and reference information"
        )
        
        self.bug_hunter_tool = AgentTool(
            agent=self.bug_hunter,
            description="Debug and troubleshoot Android development issues"
        )
        
        # Add tools to router
        self.router_agent.tools = [
            self.code_expert_tool,
            self.docs_agent_tool, 
            self.bug_hunter_tool
        ]
    
    def _create_code_execution_tool(self):
        """Create code execution tool for agents."""
        async def execute_code_func(code: str, context: 'ToolContext') -> str:
            """Execute Python code with session context."""
            result = await self.code_execution_tool.execute_code(code, context)
            
            if result["success"]:
                return f"Code executed successfully:\n{result['output']}"
            else:
                return f"Code execution failed:\n{result['error']}"
        
        return execute_code_func
    
    async def create_workflow_agents(self) -> Dict[str, Any]:
        """Create workflow agents for complex tasks."""
        if not ADK_AVAILABLE:
            return {}
        
        # Sequential workflow for code generation and debugging
        code_debug_workflow = SequentialAgent(
            name="Code_Debug_Workflow",
            sub_agents=[
                self.code_expert,
                self.bug_hunter
            ]
        )
        
        # Parallel workflow for gathering information
        info_gathering_workflow = ParallelAgent(
            name="Info_Gathering_Workflow", 
            sub_agents=[
                self.docs_agent,
                self.code_expert
            ]
        )
        
        # Iterative refinement for debugging
        debug_refinement_loop = LoopAgent(
            name="Debug_Refinement_Loop",
            agent=self.bug_hunter,
            max_iterations=5,
            condition=lambda result: "success" in result.lower()
        )
        
        return {
            "code_debug": code_debug_workflow,
            "info_gathering": info_gathering_workflow,
            "debug_loop": debug_refinement_loop
        }
    
    async def process_voice_message(
        self, 
        message: str, 
        session: EnhancedVoiceSession
    ) -> str:
        """Process voice message through multi-agent system with context."""
        try:
            await session.log_event("voice_input", {"message": message})
            
            # First, check if this is a code execution request
            code_response = await self.voice_code_executor.process_voice_input(message, session)
            if code_response:
                await session.log_event("code_execution_response", {"response": code_response})
                return code_response
            
            # Enhance message with conversation context
            if session.conversation_memory:
                enhanced_prompt = self.response_generator.enhance_prompt_with_context(
                    message, 
                    session.conversation_memory,
                    "You are an expert Android development assistant with voice interaction capabilities."
                )
            else:
                enhanced_prompt = message
            
            if ADK_AVAILABLE and hasattr(self, 'router_agent'):
                # Use multi-agent system
                response = await self._process_with_router(enhanced_prompt, session)
            else:
                # Fallback to single agent
                response = await self._process_with_fallback(enhanced_prompt, session)
            
            # Add conversation turn to memory
            if session.conversation_memory:
                turn = ConversationTurn(
                    turn_id=str(uuid.uuid4()),
                    user_input=message,
                    assistant_response=response,
                    timestamp=datetime.now(timezone.utc)
                )
                await session.conversation_memory.add_turn(turn)
                
                # Extract and update context
                context_updates = self.response_generator.extract_context_updates(response)
                for key, value in context_updates.items():
                    session.conversation_memory.update_working_memory(key, value)
            
            await session.log_event("voice_response", {"response": response})
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing voice message: {e}")
            return f"I encountered an error processing your request: {str(e)}"
    
    async def _process_with_router(self, message: str, session: EnhancedVoiceSession) -> str:
        """Process message using router agent."""
        try:
            # Create context with session state
            context = ToolContext(session=session.adk_session) if session.adk_session else None
            
            # Route message through main agent
            response = await self.router_agent.process(message, context=context)
            return response
            
        except Exception as e:
            self.logger.error(f"Router agent error: {e}")
            return await self._process_with_fallback(message, session)
    
    async def _process_with_fallback(self, message: str, session: EnhancedVoiceSession) -> str:
        """Fallback processing with single agent."""
        if hasattr(self, 'fallback_agent'):
            response = await self.fallback_agent.process_message(message, session.session_id)
            return response.content
        else:
            return "I'm having trouble processing your request right now. Please try again."
    
    async def handle_code_execution_request(
        self, 
        code: str, 
        session: EnhancedVoiceSession
    ) -> str:
        """Handle direct code execution request."""
        result = await self.code_execution_tool.execute_code(code, session=session)
        
        if result["success"]:
            return f"Code executed successfully. Output: {result['output']}"
        else:
            return f"Code execution failed with error: {result['error']}"
    
    async def get_session_context(self, session: EnhancedVoiceSession) -> Dict[str, Any]:
        """Get comprehensive session context for debugging."""
        return {
            "session_id": session.session_id,
            "state": session.session_state.to_dict(),
            "events_count": len(session.events_log),
            "conversation_length": len(session.conversation_history),
            "last_activity": session.last_activity.isoformat()
        }


class GoogleADKVoiceAgent:
    """Enhanced Google ADK agent with voice capabilities and multi-agent system."""
    
    def __init__(self, config: ADKWebConfig, code_executor):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, EnhancedVoiceSession] = {}
        
        # Initialize multi-agent system
        self.multi_agent_system = MultiAgentVoiceSystem(config, code_executor)
        
        # Speech processing
        self.speech_processor = SpeechProcessor(config)
        
        # Conversation context management
        self.context_manager = PersistentConversationContext()
        self.response_generator = ContextualResponseGenerator()
        
        # Live API session management
        self.live_sessions: Dict[str, Any] = {}
    
    async def initialize(self):
        """Initialize the voice agent and multi-agent system."""
        try:
            if ADK_AVAILABLE:
                self.logger.info("Initializing Google ADK Voice Agent with multi-agent system")
                # Initialize workflow agents
                self.workflow_agents = await self.multi_agent_system.create_workflow_agents()
            else:
                self.logger.info("Initializing fallback voice agent")
                await self.multi_agent_system.fallback_agent.initialize()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize voice agent: {e}")
    
    async def create_voice_session(
        self, 
        websocket, 
        user_id: Optional[str] = None
    ) -> EnhancedVoiceSession:
        """Create new enhanced voice session."""
        session_id = str(uuid.uuid4())
        session = EnhancedVoiceSession(session_id, websocket, user_id)
        
        await session.initialize_adk_session()
        
        # Initialize conversation context
        session.conversation_memory = await self.context_manager.get_or_create_context(session_id, user_id)
        
        self.active_sessions[session_id] = session
        
        # Start speech processing
        await self.speech_processor.start_speech_processing(session)
        
        self.logger.info(f"Created enhanced voice session: {session_id}")
        return session
    
    async def process_voice_input(
        self, 
        audio_chunk: AudioChunk, 
        session: EnhancedVoiceSession
    ) -> Optional[str]:
        """Process voice input and return transcription."""
        try:
            await session.log_event("voice_input_received", {
                "chunk_size": len(audio_chunk.data),
                "sequence": audio_chunk.sequence_number
            })
            
            # Process through speech processor
            transcription = await self.speech_processor.process_audio_chunk(audio_chunk, session)
            
            if transcription:
                await session.log_event("transcription_generated", {
                    "transcription": transcription,
                    "chunk_sequence": audio_chunk.sequence_number
                })
            
            return transcription
            
        except Exception as e:
            self.logger.error(f"Error processing voice input: {e}")
            return None
    
    async def generate_voice_response(
        self, 
        text: str, 
        session: EnhancedVoiceSession
    ) -> AsyncIterator[bytes]:
        """Generate voice response from text."""
        try:
            # Process text through multi-agent system
            response_text = await self.multi_agent_system.process_voice_message(text, session)
            
            await session.log_event("response_generated", {
                "input_text": text,
                "response_text": response_text
            })
            
            # Generate speech from response text
            async for audio_chunk in self.speech_processor.generate_speech_response(response_text, session):
                if audio_chunk:
                    yield audio_chunk
            
        except Exception as e:
            self.logger.error(f"Error generating voice response: {e}")
            yield b""
    
    async def handle_interruption(self, session: EnhancedVoiceSession):
        """Handle voice interruption."""
        await session.log_event("interruption", {"timestamp": datetime.now(timezone.utc).isoformat()})
        session.is_speaking = False
        
        # Stop any ongoing Live API operations
        if session.session_id in self.live_sessions:
            # Implementation will be added with Live API integration
            pass
    
    async def close_voice_session(self, session: EnhancedVoiceSession):
        """Close voice session and cleanup resources."""
        session_id = session.session_id
        
        # Stop speech processing
        await self.speech_processor.stop_speech_processing(session)
        
        # Save conversation context
        if session.conversation_memory:
            await self.context_manager.close_context(session_id)
        
        # Log session summary
        context = await self.multi_agent_system.get_session_context(session)
        await session.log_event("session_closed", context)
        
        # Cleanup resources
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        if session_id in self.live_sessions:
            del self.live_sessions[session_id]
        
        self.logger.info(f"Closed voice session: {session_id}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active voice sessions."""
        return {
            "active_sessions": len(self.active_sessions),
            "live_sessions": len(self.live_sessions),
            "adk_available": ADK_AVAILABLE,
            "speech_processing": self.speech_processor.get_processing_stats(),
            "context_management": self.context_manager.get_context_stats()
        }