"""Voice-enabled code execution with intelligent parsing and response generation."""

import asyncio
import re
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from .executor import SafePythonExecutor, ExecutionResult
# Remove circular import - will use TYPE_CHECKING for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adk_voice_agent import EnhancedVoiceSession
from .conversation_context import ConversationTurn
from .voice_security import SecureVoiceCodeExecutor, ExecutionLimits, SecurityViolation


@dataclass
class VoiceCodeRequest:
    """Represents a code execution request from voice input."""
    
    original_text: str
    extracted_code: str
    intent: str  # "execute", "explain", "debug", "modify"
    language: str = "python"
    context: Optional[str] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "original_text": self.original_text,
            "extracted_code": self.extracted_code,
            "intent": self.intent,
            "language": self.language,
            "context": self.context,
            "confidence": self.confidence
        }


class VoiceCodeParser:
    """Parses voice input to extract code execution requests."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns for detecting code execution requests
        self.execution_patterns = [
            r"(?:run|execute|eval(?:uate)?)\s+(?:this\s+)?(?:python\s+)?code[:\s]*(.+)",
            r"(?:can you|please)\s+(?:run|execute)\s+(.+)",
            r"execute[:\s]+(.+)",
            r"run[:\s]+(.+)",
            r"python[:\s]+(.+)",
        ]
        
        # Patterns for code blocks
        self.code_block_patterns = [
            r"```(?:python)?\s*\n?(.*?)\n?```",
            r"`([^`]+)`",
            r"(?:^|\s)([a-zA-Z_][a-zA-Z0-9_]*\s*=.+)",
            r"(?:^|\s)(print\s*\(.+\))",
            r"(?:^|\s)(for\s+.+:)",
            r"(?:^|\s)(if\s+.+:)",
            r"(?:^|\s)(def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(.+\):)",
        ]
        
        # Intent keywords
        self.intent_keywords = {
            "execute": ["run", "execute", "eval", "evaluate"],
            "explain": ["explain", "what does", "how does", "describe"],
            "debug": ["debug", "fix", "error", "problem", "issue"],
            "modify": ["change", "modify", "update", "alter", "improve"]
        }
    
    def parse_voice_input(self, text: str) -> Optional[VoiceCodeRequest]:
        """Parse voice input to extract code execution request."""
        text = text.strip().lower()
        
        # Check if this is a code-related request
        if not self._is_code_request(text):
            return None
        
        # Extract intent
        intent = self._extract_intent(text)
        
        # Extract code
        extracted_code = self._extract_code(text)
        
        if not extracted_code:
            return None
        
        # Calculate confidence based on patterns matched
        confidence = self._calculate_confidence(text, extracted_code, intent)
        
        return VoiceCodeRequest(
            original_text=text,
            extracted_code=extracted_code,
            intent=intent,
            language="python",
            confidence=confidence
        )
    
    def _is_code_request(self, text: str) -> bool:
        """Check if text contains a code execution request."""
        code_indicators = [
            "run", "execute", "eval", "python", "code", "script",
            "print", "def", "for", "if", "import", "=", "()", "[]"
        ]
        
        return any(indicator in text for indicator in code_indicators)
    
    def _extract_intent(self, text: str) -> str:
        """Extract the intent from voice input."""
        for intent, keywords in self.intent_keywords.items():
            if any(keyword in text for keyword in keywords):
                return intent
        
        # Default to execute if code patterns are found
        return "execute"
    
    def _extract_code(self, text: str) -> Optional[str]:
        """Extract code from voice input."""
        # Try execution patterns first
        for pattern in self.execution_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                code_text = match.group(1).strip()
                # Clean up the extracted code
                return self._clean_extracted_code(code_text)
        
        # Try code block patterns
        for pattern in self.code_block_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                code_text = match.group(1).strip()
                return self._clean_extracted_code(code_text)
        
        # If no specific patterns match, check if the entire text looks like code
        if self._looks_like_code(text):
            return self._clean_extracted_code(text)
        
        return None
    
    def _clean_extracted_code(self, code_text: str) -> str:
        """Clean and format extracted code."""
        # Remove common voice-to-text artifacts
        code_text = re.sub(r'\b(period|dot)\b', '.', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(comma)\b', ',', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(colon)\b', ':', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(semicolon)\b', ';', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(equals)\b', '=', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(plus)\b', '+', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(minus)\b', '-', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(open paren|left paren)\b', '(', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(close paren|right paren)\b', ')', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(open bracket|left bracket)\b', '[', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(close bracket|right bracket)\b', ']', code_text, flags=re.IGNORECASE)
        code_text = re.sub(r'\b(quote|quotes)\b', '"', code_text, flags=re.IGNORECASE)
        
        # Fix common spacing issues
        code_text = re.sub(r'\s*=\s*', '=', code_text)
        code_text = re.sub(r'\s*\(\s*', '(', code_text)
        code_text = re.sub(r'\s*\)\s*', ')', code_text)
        code_text = re.sub(r'\s*,\s*', ', ', code_text)
        
        return code_text.strip()
    
    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like Python code."""
        code_indicators = [
            r'[a-zA-Z_][a-zA-Z0-9_]*\s*=',  # Variable assignment
            r'print\s*\(',  # Print statement
            r'def\s+[a-zA-Z_]',  # Function definition
            r'for\s+.+\s+in\s+',  # For loop
            r'if\s+.+:',  # If statement
            r'import\s+[a-zA-Z_]',  # Import statement
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in code_indicators)
    
    def _calculate_confidence(self, text: str, code: str, intent: str) -> float:
        """Calculate confidence score for the extraction."""
        confidence = 0.0
        
        # Base confidence from intent keywords
        if intent in ["execute", "run"]:
            confidence += 0.3
        
        # Confidence from code patterns
        if re.search(r'print\s*\(', code, re.IGNORECASE):
            confidence += 0.2
        if re.search(r'[a-zA-Z_][a-zA-Z0-9_]*\s*=', code):
            confidence += 0.2
        if re.search(r'def\s+[a-zA-Z_]', code, re.IGNORECASE):
            confidence += 0.3
        
        # Confidence from explicit code markers
        if "```" in text or "`" in text:
            confidence += 0.4
        
        # Confidence from execution keywords
        execution_words = ["run", "execute", "eval", "python"]
        if any(word in text.lower() for word in execution_words):
            confidence += 0.2
        
        return min(confidence, 1.0)


class VoiceResponseGenerator:
    """Generates voice-friendly responses for code execution results."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_execution_response(
        self, 
        request: VoiceCodeRequest, 
        result: ExecutionResult
    ) -> str:
        """Generate voice response for code execution result."""
        
        if result.success:
            return self._generate_success_response(request, result)
        else:
            return self._generate_error_response(request, result)
    
    def _generate_success_response(
        self, 
        request: VoiceCodeRequest, 
        result: ExecutionResult
    ) -> str:
        """Generate response for successful execution."""
        
        response_parts = []
        
        # Acknowledge the execution
        if request.intent == "execute":
            response_parts.append("I've executed your Python code successfully.")
        else:
            response_parts.append("The code ran successfully.")
        
        # Include output if available
        if result.output.strip():
            output = result.output.strip()
            
            # Make output more voice-friendly
            if len(output) > 200:
                output = output[:200] + "... and more"
            
            # Clean up output for speech
            output = self._make_speech_friendly(output)
            response_parts.append(f"The output is: {output}")
        else:
            response_parts.append("The code executed without producing any output.")
        
        # Include execution time if significant
        if result.execution_time > 1.0:
            response_parts.append(f"Execution took {result.execution_time:.1f} seconds.")
        
        return " ".join(response_parts)
    
    def _generate_error_response(
        self, 
        request: VoiceCodeRequest, 
        result: ExecutionResult
    ) -> str:
        """Generate response for failed execution."""
        
        response_parts = []
        
        # Acknowledge the error
        response_parts.append("I encountered an error while executing your code.")
        
        # Include error information
        if result.error:
            error_msg = self._make_error_speech_friendly(result.error)
            response_parts.append(f"The error is: {error_msg}")
        
        # Suggest next steps
        if "syntax" in result.error.lower():
            response_parts.append("This looks like a syntax error. Would you like me to help fix the code?")
        elif "name" in result.error.lower() and "not defined" in result.error.lower():
            response_parts.append("It seems like a variable or function is not defined. Should we define it first?")
        else:
            response_parts.append("Would you like me to help debug this issue?")
        
        return " ".join(response_parts)
    
    def _make_speech_friendly(self, text: str) -> str:
        """Make text more suitable for speech synthesis."""
        # Replace common symbols with words
        text = text.replace("==", " equals ")
        text = text.replace("!=", " not equals ")
        text = text.replace("<=", " less than or equal to ")
        text = text.replace(">=", " greater than or equal to ")
        text = text.replace("<", " less than ")
        text = text.replace(">", " greater than ")
        text = text.replace("&&", " and ")
        text = text.replace("||", " or ")
        text = text.replace("++", " plus plus ")
        text = text.replace("--", " minus minus ")
        
        # Handle numbers and special characters
        text = re.sub(r'\b(\d+)\b', r'number \1', text)
        text = text.replace("_", " underscore ")
        text = text.replace("-", " dash ")
        
        return text
    
    def _make_error_speech_friendly(self, error: str) -> str:
        """Make error messages more suitable for speech."""
        # Simplify common Python errors
        error = re.sub(r'File ".*", line \d+', 'In your code', error)
        error = re.sub(r'Traceback \(most recent call last\):', '', error)
        error = error.replace("SyntaxError:", "Syntax error:")
        error = error.replace("NameError:", "Name error:")
        error = error.replace("TypeError:", "Type error:")
        error = error.replace("ValueError:", "Value error:")
        error = error.replace("IndentationError:", "Indentation error:")
        
        # Make it more conversational
        error = self._make_speech_friendly(error)
        
        # Limit length
        if len(error) > 150:
            error = error[:150] + "..."
        
        return error.strip()


class VoiceCodeExecutor:
    """Code execution with voice response capabilities."""
    
    def __init__(self, executor: SafePythonExecutor):
        self.executor = executor
        self.parser = VoiceCodeParser()
        self.response_generator = VoiceResponseGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Security wrapper
        self.secure_executor = SecureVoiceCodeExecutor(executor, ExecutionLimits())
        
        # Execution history for context
        self.execution_history: List[Tuple[VoiceCodeRequest, ExecutionResult]] = []
    
    async def process_voice_input(
        self, 
        voice_input: str, 
        session: 'EnhancedVoiceSession'
    ) -> Optional[str]:
        """Process voice input for code execution requests."""
        
        # Parse voice input
        code_request = self.parser.parse_voice_input(voice_input)
        
        if not code_request:
            return None  # Not a code execution request
        
        await session.log_event("code_request_parsed", code_request.to_dict())
        
        # Execute based on intent
        if code_request.intent == "execute":
            return await self.execute_code_from_voice(code_request, session)
        elif code_request.intent == "explain":
            return await self.explain_code(code_request, session)
        elif code_request.intent == "debug":
            return await self.debug_code(code_request, session)
        elif code_request.intent == "modify":
            return await self.modify_code(code_request, session)
        else:
            return await self.execute_code_from_voice(code_request, session)
    
    async def execute_code_from_voice(
        self, 
        request: VoiceCodeRequest, 
        session: 'EnhancedVoiceSession'
    ) -> str:
        """Execute code from voice request with security measures."""
        
        try:
            # Log the execution attempt
            await session.log_event("code_execution_attempt", {
                "code": request.extracted_code,
                "confidence": request.confidence
            })
            
            # Execute with security checks
            success, output_or_error, violations = await self.secure_executor.secure_execute(
                request.extracted_code, 
                session
            )
            
            # Create result object for compatibility
            if success:
                result = ExecutionResult(
                    success=True,
                    output=output_or_error,
                    error=None,
                    exit_code=0,
                    execution_time=0.0  # Time tracking handled by secure executor
                )
            else:
                result = ExecutionResult(
                    success=False,
                    output="",
                    error=output_or_error,
                    exit_code=1,
                    execution_time=0.0
                )
            
            # Store in history
            self.execution_history.append((request, result))
            
            # Update session state
            await session.update_state("last_code_execution", {
                "request": request.to_dict(),
                "result": result.to_dict(),
                "security_violations": [v.to_dict() for v in violations],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Generate voice response with security context
            if violations:
                response = self._generate_security_aware_response(request, result, violations)
            else:
                response = self.response_generator.generate_execution_response(request, result)
            
            await session.log_event("code_execution_completed", {
                "success": result.success,
                "response": response,
                "security_violations": len(violations)
            })
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error executing code from voice: {e}")
            return f"I encountered an error while trying to execute your code: {str(e)}"
    
    async def explain_code(
        self, 
        request: VoiceCodeRequest, 
        session: 'EnhancedVoiceSession'
    ) -> str:
        """Explain what the code does."""
        
        code = request.extracted_code
        
        # Simple code explanation (in production, use more sophisticated analysis)
        explanation_parts = ["Let me explain this code for you."]
        
        if "print" in code.lower():
            explanation_parts.append("This code includes print statements to display output.")
        
        if "=" in code and not "==" in code:
            explanation_parts.append("There are variable assignments in this code.")
        
        if "for" in code.lower():
            explanation_parts.append("This code contains a for loop for iteration.")
        
        if "if" in code.lower():
            explanation_parts.append("There are conditional statements using if.")
        
        if "def" in code.lower():
            explanation_parts.append("This code defines one or more functions.")
        
        explanation_parts.append("Would you like me to run this code to see what it does?")
        
        return " ".join(explanation_parts)
    
    async def debug_code(
        self, 
        request: VoiceCodeRequest, 
        session: 'EnhancedVoiceSession'
    ) -> str:
        """Help debug code issues."""
        
        # Try to execute the code to identify issues
        try:
            result = await self.executor.execute(request.extracted_code)
            
            if result.success:
                return "I ran your code and it executed successfully. What specific issue are you experiencing?"
            else:
                # Provide debugging suggestions based on the error
                error = result.error.lower()
                
                if "syntax" in error:
                    return "I found a syntax error in your code. This usually means there's a missing parenthesis, bracket, or incorrect indentation. Would you like me to suggest a fix?"
                elif "name" in error and "not defined" in error:
                    return "There's a name error - a variable or function is being used before it's defined. Should we define the missing variable first?"
                elif "indentation" in error:
                    return "There's an indentation error. Python requires consistent indentation. Would you like me to help fix the indentation?"
                else:
                    return f"I found an error: {self.response_generator._make_error_speech_friendly(result.error)}. Would you like me to suggest a solution?"
        
        except Exception as e:
            return f"I encountered an issue while analyzing your code: {str(e)}"
    
    async def modify_code(
        self, 
        request: VoiceCodeRequest, 
        session: 'EnhancedVoiceSession'
    ) -> str:
        """Help modify existing code."""
        
        # Get the last executed code from session
        last_execution = await session.get_state("last_code_execution")
        
        if last_execution:
            return "I can help you modify your previous code. What changes would you like to make?"
        else:
            return "I'd be happy to help modify code. Could you first show me the code you'd like to change?"
    
    async def speak_execution_result(
        self, 
        result: ExecutionResult, 
        session: 'EnhancedVoiceSession'
    ) -> str:
        """Generate speech-friendly response for execution result."""
        
        # This method is called when we have a direct ExecutionResult
        # Create a mock request for the response generator
        mock_request = VoiceCodeRequest(
            original_text="direct execution",
            extracted_code="",
            intent="execute"
        )
        
        return self.response_generator.generate_execution_response(mock_request, result)
    
    def _generate_security_aware_response(
        self, 
        request: VoiceCodeRequest, 
        result: ExecutionResult, 
        violations: List[SecurityViolation]
    ) -> str:
        """Generate response that includes security information."""
        
        response_parts = []
        
        # Handle security violations
        critical_violations = [v for v in violations if v.severity.value == "critical"]
        if critical_violations:
            response_parts.append("I couldn't execute your code due to security concerns.")
            response_parts.append(f"The main issue is: {critical_violations[0].description}")
            if critical_violations[0].suggestion:
                response_parts.append(critical_violations[0].suggestion)
            return " ".join(response_parts)
        
        # Handle warnings for non-critical violations
        warning_violations = [v for v in violations if v.severity.value in ["high", "medium"]]
        if warning_violations and result.success:
            response_parts.append("I executed your code successfully, but I noticed some security concerns.")
            response_parts.append(f"Warning: {warning_violations[0].description}")
            if result.output.strip():
                output = self.response_generator._make_speech_friendly(result.output.strip())
                response_parts.append(f"The output is: {output}")
        elif result.success:
            # Normal successful execution
            return self.response_generator.generate_execution_response(request, result)
        else:
            # Failed execution
            return self.response_generator.generate_execution_response(request, result)
        
        return " ".join(response_parts)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get code execution statistics."""
        successful_executions = sum(1 for _, result in self.execution_history if result.success)
        
        base_stats = {
            "total_executions": len(self.execution_history),
            "successful_executions": successful_executions,
            "error_rate": (len(self.execution_history) - successful_executions) / max(len(self.execution_history), 1),
            "recent_executions": len([h for h in self.execution_history[-10:]])
        }
        
        # Add security stats
        security_stats = self.secure_executor.get_security_stats()
        
        return {**base_stats, "security": security_stats}