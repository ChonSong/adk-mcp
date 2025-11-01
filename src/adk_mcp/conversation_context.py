"""Enhanced conversation context management with persistent state."""

import asyncio
import json
import logging
import pickle
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from pathlib import Path

from .voice_streaming import VoiceMessage


@dataclass
class ConversationTurn:
    """Represents a single turn in conversation."""
    
    turn_id: str
    user_input: str
    assistant_response: str
    timestamp: datetime
    audio_data: Optional[bytes] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "turn_id": self.turn_id,
            "user_input": self.user_input,
            "assistant_response": self.assistant_response,
            "timestamp": self.timestamp.isoformat(),
            "audio_data": self.audio_data.hex() if self.audio_data else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create from dictionary."""
        return cls(
            turn_id=data["turn_id"],
            user_input=data["user_input"],
            assistant_response=data["assistant_response"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            audio_data=bytes.fromhex(data["audio_data"]) if data.get("audio_data") else None,
            metadata=data.get("metadata", {})
        )


@dataclass
class ConversationSummary:
    """Summary of conversation for context compression."""
    
    summary_text: str
    key_topics: List[str]
    important_facts: List[str]
    code_snippets: List[Dict[str, Any]]
    timestamp: datetime
    turn_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "summary_text": self.summary_text,
            "key_topics": self.key_topics,
            "important_facts": self.important_facts,
            "code_snippets": self.code_snippets,
            "timestamp": self.timestamp.isoformat(),
            "turn_count": self.turn_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSummary':
        """Create from dictionary."""
        return cls(
            summary_text=data["summary_text"],
            key_topics=data["key_topics"],
            important_facts=data["important_facts"],
            code_snippets=data["code_snippets"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            turn_count=data["turn_count"]
        )


class ConversationMemory:
    """Manages conversation memory with different retention strategies."""
    
    def __init__(self, max_recent_turns: int = 10, max_total_turns: int = 100):
        self.max_recent_turns = max_recent_turns
        self.max_total_turns = max_total_turns
        self.recent_turns: List[ConversationTurn] = []
        self.archived_turns: List[ConversationTurn] = []
        self.summaries: List[ConversationSummary] = []
        self.working_memory: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    async def add_turn(self, turn: ConversationTurn):
        """Add a new conversation turn."""
        self.recent_turns.append(turn)
        
        # Manage memory limits
        if len(self.recent_turns) > self.max_recent_turns:
            # Move oldest recent turn to archive
            old_turn = self.recent_turns.pop(0)
            self.archived_turns.append(old_turn)
            
            # Check if we need to create a summary
            if len(self.archived_turns) > self.max_total_turns:
                await self._create_summary()
    
    async def _create_summary(self):
        """Create summary of old conversations to compress memory."""
        if len(self.archived_turns) < 5:  # Need at least 5 turns to summarize
            return
        
        # Take oldest 10 turns for summarization
        turns_to_summarize = self.archived_turns[:10]
        self.archived_turns = self.archived_turns[10:]
        
        # Extract key information
        key_topics = set()
        important_facts = []
        code_snippets = []
        
        summary_parts = []
        for turn in turns_to_summarize:
            summary_parts.append(f"User: {turn.user_input}")
            summary_parts.append(f"Assistant: {turn.assistant_response}")
            
            # Extract topics (simple keyword extraction)
            words = turn.user_input.lower().split()
            for word in words:
                if word in ["android", "kotlin", "java", "xml", "gradle", "adb", "debug", "error"]:
                    key_topics.add(word)
            
            # Extract code snippets
            if "```" in turn.assistant_response:
                code_snippets.append({
                    "code": turn.assistant_response,
                    "timestamp": turn.timestamp.isoformat(),
                    "context": turn.user_input[:100]
                })
        
        summary = ConversationSummary(
            summary_text=" ".join(summary_parts),
            key_topics=list(key_topics),
            important_facts=important_facts,
            code_snippets=code_snippets,
            timestamp=datetime.now(timezone.utc),
            turn_count=len(turns_to_summarize)
        )
        
        self.summaries.append(summary)
        self.logger.info(f"Created conversation summary for {len(turns_to_summarize)} turns")
    
    def get_context_for_prompt(self, max_tokens: int = 2000) -> str:
        """Get conversation context formatted for AI prompt."""
        context_parts = []
        
        # Add recent summaries
        if self.summaries:
            context_parts.append("Previous conversation summary:")
            for summary in self.summaries[-2:]:  # Last 2 summaries
                context_parts.append(f"- Topics: {', '.join(summary.key_topics)}")
                context_parts.append(f"- Key facts: {'; '.join(summary.important_facts)}")
        
        # Add working memory
        if self.working_memory:
            context_parts.append("Current context:")
            for key, value in self.working_memory.items():
                if isinstance(value, str) and len(value) < 100:
                    context_parts.append(f"- {key}: {value}")
        
        # Add recent turns
        if self.recent_turns:
            context_parts.append("Recent conversation:")
            for turn in self.recent_turns[-5:]:  # Last 5 turns
                context_parts.append(f"User: {turn.user_input}")
                context_parts.append(f"Assistant: {turn.assistant_response}")
        
        context = "\n".join(context_parts)
        
        # Truncate if too long (rough token estimation: 1 token ≈ 4 characters)
        if len(context) > max_tokens * 4:
            context = context[:max_tokens * 4] + "..."
        
        return context
    
    def update_working_memory(self, key: str, value: Any):
        """Update working memory with key-value pair."""
        self.working_memory[key] = value
        self.logger.debug(f"Updated working memory: {key} = {str(value)[:50]}...")
    
    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """Get value from working memory."""
        return self.working_memory.get(key, default)
    
    def clear_working_memory(self):
        """Clear working memory."""
        self.working_memory.clear()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        return {
            "recent_turns": len(self.recent_turns),
            "archived_turns": len(self.archived_turns),
            "summaries": len(self.summaries),
            "working_memory_keys": len(self.working_memory),
            "total_turns": len(self.recent_turns) + len(self.archived_turns)
        }


class PersistentConversationContext:
    """Manages persistent conversation context across sessions."""
    
    def __init__(self, storage_dir: str = ".adk_sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # In-memory contexts
        self.active_contexts: Dict[str, ConversationMemory] = {}
        
        # User preferences (persistent across sessions)
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self._load_user_preferences()
    
    async def get_or_create_context(self, session_id: str, user_id: Optional[str] = None) -> ConversationMemory:
        """Get existing context or create new one."""
        if session_id in self.active_contexts:
            return self.active_contexts[session_id]
        
        # Try to load from storage
        context = await self._load_context(session_id)
        if context is None:
            context = ConversationMemory()
        
        # Load user preferences if available
        if user_id and user_id in self.user_preferences:
            prefs = self.user_preferences[user_id]
            context.update_working_memory("user_preferences", prefs)
        
        self.active_contexts[session_id] = context
        return context
    
    async def save_context(self, session_id: str):
        """Save context to persistent storage."""
        if session_id not in self.active_contexts:
            return
        
        context = self.active_contexts[session_id]
        context_file = self.storage_dir / f"{session_id}.json"
        
        try:
            # Prepare data for serialization
            data = {
                "recent_turns": [turn.to_dict() for turn in context.recent_turns],
                "archived_turns": [turn.to_dict() for turn in context.archived_turns],
                "summaries": [summary.to_dict() for summary in context.summaries],
                "working_memory": context.working_memory,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            with open(context_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug(f"Saved context for session: {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error saving context for session {session_id}: {e}")
    
    async def _load_context(self, session_id: str) -> Optional[ConversationMemory]:
        """Load context from persistent storage."""
        context_file = self.storage_dir / f"{session_id}.json"
        
        if not context_file.exists():
            return None
        
        try:
            with open(context_file, 'r') as f:
                data = json.load(f)
            
            context = ConversationMemory()
            
            # Load turns
            context.recent_turns = [ConversationTurn.from_dict(turn_data) for turn_data in data.get("recent_turns", [])]
            context.archived_turns = [ConversationTurn.from_dict(turn_data) for turn_data in data.get("archived_turns", [])]
            
            # Load summaries
            context.summaries = [ConversationSummary.from_dict(summary_data) for summary_data in data.get("summaries", [])]
            
            # Load working memory
            context.working_memory = data.get("working_memory", {})
            
            self.logger.debug(f"Loaded context for session: {session_id}")
            return context
            
        except Exception as e:
            self.logger.error(f"Error loading context for session {session_id}: {e}")
            return None
    
    async def close_context(self, session_id: str):
        """Close and save context."""
        if session_id in self.active_contexts:
            await self.save_context(session_id)
            del self.active_contexts[session_id]
    
    def update_user_preference(self, user_id: str, key: str, value: Any):
        """Update user preference."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id][key] = value
        self._save_user_preferences()
    
    def get_user_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get user preference."""
        return self.user_preferences.get(user_id, {}).get(key, default)
    
    def _load_user_preferences(self):
        """Load user preferences from storage."""
        prefs_file = self.storage_dir / "user_preferences.json"
        
        if prefs_file.exists():
            try:
                with open(prefs_file, 'r') as f:
                    self.user_preferences = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading user preferences: {e}")
                self.user_preferences = {}
        else:
            self.user_preferences = {}
    
    def _save_user_preferences(self):
        """Save user preferences to storage."""
        prefs_file = self.storage_dir / "user_preferences.json"
        
        try:
            with open(prefs_file, 'w') as f:
                json.dump(self.user_preferences, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving user preferences: {e}")
    
    async def cleanup_old_contexts(self, max_age_days: int = 30):
        """Cleanup old context files."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        
        for context_file in self.storage_dir.glob("*.json"):
            if context_file.name == "user_preferences.json":
                continue
            
            try:
                if context_file.stat().st_mtime < cutoff_date.timestamp():
                    context_file.unlink()
                    self.logger.info(f"Cleaned up old context file: {context_file.name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up context file {context_file.name}: {e}")
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Get context management statistics."""
        total_files = len(list(self.storage_dir.glob("*.json")))
        
        return {
            "active_contexts": len(self.active_contexts),
            "stored_contexts": total_files - 1,  # Exclude user_preferences.json
            "users_with_preferences": len(self.user_preferences),
            "storage_dir": str(self.storage_dir)
        }


class ContextualResponseGenerator:
    """Generates contextually aware responses using conversation history."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def enhance_prompt_with_context(
        self, 
        user_input: str, 
        context: ConversationMemory,
        system_prompt: str = ""
    ) -> str:
        """Enhance user prompt with conversation context."""
        
        # Get conversation context
        conversation_context = context.get_context_for_prompt()
        
        # Build enhanced prompt
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")
        
        if conversation_context:
            prompt_parts.append(f"Context: {conversation_context}")
        
        prompt_parts.append(f"Current request: {user_input}")
        
        return "\n\n".join(prompt_parts)
    
    def extract_context_updates(self, response: str) -> Dict[str, Any]:
        """Extract context updates from AI response."""
        updates = {}
        
        # Extract debugging step if mentioned
        if "step" in response.lower():
            # Simple extraction - in production, use more sophisticated NLP
            if "debugging" in response.lower():
                updates["current_debugging_step"] = "active"
        
        # Extract code execution results
        if "executed" in response.lower() and "code" in response.lower():
            updates["last_action"] = "code_execution"
        
        # Extract topic changes
        topics = []
        for topic in ["android", "kotlin", "java", "xml", "gradle", "debugging"]:
            if topic in response.lower():
                topics.append(topic)
        
        if topics:
            updates["current_topics"] = topics
        
        return updates
    
    def should_summarize_context(self, context: ConversationMemory) -> bool:
        """Determine if context should be summarized."""
        return (
            len(context.recent_turns) > 8 or
            len(context.archived_turns) > 20 or
            len(context.working_memory) > 10
        )