"""Security measures for voice-triggered code execution."""

import re
import ast
import logging
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

# Remove circular import - will use TYPE_CHECKING for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adk_voice_agent import EnhancedVoiceSession


class SecurityLevel(Enum):
    """Security levels for code execution."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityViolation:
    """Represents a security violation detected in code."""
    
    violation_type: str
    severity: SecurityLevel
    description: str
    code_snippet: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "violation_type": self.violation_type,
            "severity": self.severity.value,
            "description": self.description,
            "code_snippet": self.code_snippet,
            "line_number": self.line_number,
            "suggestion": self.suggestion
        }


@dataclass
class ExecutionLimits:
    """Execution limits for voice-triggered code."""
    
    max_execution_time: int = 30  # seconds
    max_memory_mb: int = 100
    max_output_length: int = 1000
    max_file_operations: int = 5
    max_network_requests: int = 0  # No network by default
    allowed_imports: Set[str] = None
    
    def __post_init__(self):
        if self.allowed_imports is None:
            self.allowed_imports = {
                'math', 'random', 'datetime', 'json', 'os.path',
                'collections', 'itertools', 'functools', 're'
            }


class CodeSecurityAnalyzer:
    """Analyzes code for security vulnerabilities."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Dangerous patterns and their security levels
        self.dangerous_patterns = {
            # Critical security risks
            r'\b(exec|eval)\s*\(': (SecurityLevel.CRITICAL, "Dynamic code execution", "Avoid using exec() or eval()"),
            r'\b__import__\s*\(': (SecurityLevel.CRITICAL, "Dynamic imports", "Use standard import statements"),
            r'\bcompile\s*\(': (SecurityLevel.CRITICAL, "Code compilation", "Avoid compiling code at runtime"),
            r'\bgetattr\s*\([^,]+,\s*["\'][^"\']*__[^"\']*["\']': (SecurityLevel.CRITICAL, "Accessing private attributes", "Avoid accessing private/magic methods"),
            
            # High security risks
            r'\bos\.system\s*\(': (SecurityLevel.HIGH, "System command execution", "Use subprocess with specific commands"),
            r'\bsubprocess\.(call|run|Popen)': (SecurityLevel.HIGH, "Subprocess execution", "Be careful with subprocess calls"),
            r'\bopen\s*\([^)]*["\'][^"\']*\.\.[^"\']*["\']': (SecurityLevel.HIGH, "Path traversal", "Avoid using .. in file paths"),
            r'\bpickle\.(loads?|dumps?)\s*\(': (SecurityLevel.HIGH, "Pickle serialization", "Pickle can execute arbitrary code"),
            r'\b(input|raw_input)\s*\(': (SecurityLevel.HIGH, "User input", "Be careful with user input in voice context"),
            
            # Medium security risks
            r'\bimport\s+(os|sys|subprocess|socket|urllib|requests)': (SecurityLevel.MEDIUM, "Potentially dangerous import", "Review if this import is necessary"),
            r'\bfile\s*\(': (SecurityLevel.MEDIUM, "File operations", "Use open() instead of file()"),
            r'\bglobals\s*\(\)': (SecurityLevel.MEDIUM, "Global namespace access", "Avoid modifying global namespace"),
            r'\blocals\s*\(\)': (SecurityLevel.MEDIUM, "Local namespace access", "Be careful with namespace manipulation"),
            
            # Low security risks
            r'\bdel\s+': (SecurityLevel.LOW, "Variable deletion", "Consider if deletion is necessary"),
            r'\b(exit|quit)\s*\(': (SecurityLevel.LOW, "Program termination", "Avoid terminating the program"),
        }
        
        # Blocked imports (complete blacklist)
        self.blocked_imports = {
            'os', 'sys', 'subprocess', 'socket', 'urllib', 'urllib2', 'urllib3',
            'requests', 'http', 'ftplib', 'smtplib', 'telnetlib', 'xmlrpc',
            'pickle', 'cPickle', 'marshal', 'shelve', 'dbm', 'gdbm',
            'ctypes', 'multiprocessing', 'threading', 'thread', '_thread',
            'importlib', 'imp', 'pkgutil', 'modulefinder', 'runpy',
            'code', 'codeop', 'py_compile', 'compileall', 'dis', 'ast'
        }
        
        # Allowed safe imports
        self.safe_imports = {
            'math', 'random', 'datetime', 'time', 'calendar',
            'json', 'csv', 'base64', 'hashlib', 'uuid',
            'collections', 'itertools', 'functools', 'operator',
            're', 'string', 'textwrap', 'unicodedata',
            'decimal', 'fractions', 'statistics',
            'copy', 'pprint', 'reprlib'
        }
    
    def analyze_code(self, code: str) -> List[SecurityViolation]:
        """Analyze code for security violations."""
        violations = []
        
        try:
            # Parse code to AST for deeper analysis
            tree = ast.parse(code)
            violations.extend(self._analyze_ast(tree, code))
            
        except SyntaxError as e:
            # If code has syntax errors, still check patterns
            self.logger.warning(f"Syntax error in code analysis: {e}")
        
        # Pattern-based analysis
        violations.extend(self._analyze_patterns(code))
        
        # Import analysis
        violations.extend(self._analyze_imports(code))
        
        return violations
    
    def _analyze_ast(self, tree: ast.AST, code: str) -> List[SecurityViolation]:
        """Analyze AST for security issues."""
        violations = []
        lines = code.split('\n')
        
        for node in ast.walk(tree):
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ['exec', 'eval', 'compile', '__import__']:
                        line_num = getattr(node, 'lineno', None)
                        code_snippet = lines[line_num - 1] if line_num and line_num <= len(lines) else ""
                        
                        violations.append(SecurityViolation(
                            violation_type="dangerous_function",
                            severity=SecurityLevel.CRITICAL,
                            description=f"Use of dangerous function: {func_name}",
                            code_snippet=code_snippet,
                            line_number=line_num,
                            suggestion=f"Avoid using {func_name}() for security reasons"
                        ))
            
            # Check for attribute access to private methods
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith('__') and node.attr.endswith('__'):
                    line_num = getattr(node, 'lineno', None)
                    code_snippet = lines[line_num - 1] if line_num and line_num <= len(lines) else ""
                    
                    violations.append(SecurityViolation(
                        violation_type="private_access",
                        severity=SecurityLevel.HIGH,
                        description=f"Access to private attribute: {node.attr}",
                        code_snippet=code_snippet,
                        line_number=line_num,
                        suggestion="Avoid accessing private/magic methods"
                    ))
        
        return violations
    
    def _analyze_patterns(self, code: str) -> List[SecurityViolation]:
        """Analyze code using regex patterns."""
        violations = []
        lines = code.split('\n')
        
        for pattern, (severity, description, suggestion) in self.dangerous_patterns.items():
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                # Find line number
                line_num = code[:match.start()].count('\n') + 1
                code_snippet = lines[line_num - 1] if line_num <= len(lines) else match.group(0)
                
                violations.append(SecurityViolation(
                    violation_type="pattern_match",
                    severity=severity,
                    description=description,
                    code_snippet=code_snippet.strip(),
                    line_number=line_num,
                    suggestion=suggestion
                ))
        
        return violations
    
    def _analyze_imports(self, code: str) -> List[SecurityViolation]:
        """Analyze import statements for security issues."""
        violations = []
        
        # Find all import statements
        import_patterns = [
            r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import'
        ]
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in import_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    module_name = match.group(1).split('.')[0]  # Get root module
                    
                    if module_name in self.blocked_imports:
                        violations.append(SecurityViolation(
                            violation_type="blocked_import",
                            severity=SecurityLevel.CRITICAL,
                            description=f"Blocked import: {module_name}",
                            code_snippet=line.strip(),
                            line_number=line_num,
                            suggestion=f"Import of {module_name} is not allowed for security reasons"
                        ))
                    elif module_name not in self.safe_imports:
                        violations.append(SecurityViolation(
                            violation_type="unknown_import",
                            severity=SecurityLevel.MEDIUM,
                            description=f"Unknown/unverified import: {module_name}",
                            code_snippet=line.strip(),
                            line_number=line_num,
                            suggestion=f"Import of {module_name} needs review"
                        ))
        
        return violations


class VoiceExecutionMonitor:
    """Monitors voice-triggered code execution for security and resource usage."""
    
    def __init__(self, limits: ExecutionLimits):
        self.limits = limits
        self.logger = logging.getLogger(__name__)
        
        # Execution tracking
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        # Rate limiting
        self.user_execution_counts: Dict[str, List[datetime]] = {}
        self.max_executions_per_minute = 10
        self.max_executions_per_hour = 50
    
    def start_execution_monitoring(
        self, 
        execution_id: str, 
        session: 'EnhancedVoiceSession',
        code: str
    ) -> bool:
        """Start monitoring a code execution."""
        
        # Check rate limits
        if not self._check_rate_limits(session.user_id or session.session_id):
            self.logger.warning(f"Rate limit exceeded for user: {session.user_id}")
            return False
        
        # Record execution start
        self.active_executions[execution_id] = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "code": code,
            "start_time": datetime.now(timezone.utc),
            "timeout": self.limits.max_execution_time
        }
        
        # Update rate limiting counters
        user_key = session.user_id or session.session_id
        if user_key not in self.user_execution_counts:
            self.user_execution_counts[user_key] = []
        
        self.user_execution_counts[user_key].append(datetime.now(timezone.utc))
        
        return True
    
    def end_execution_monitoring(
        self, 
        execution_id: str, 
        success: bool, 
        output: str = "", 
        error: str = ""
    ):
        """End monitoring a code execution."""
        
        if execution_id not in self.active_executions:
            return
        
        execution_info = self.active_executions[execution_id]
        end_time = datetime.now(timezone.utc)
        duration = (end_time - execution_info["start_time"]).total_seconds()
        
        # Record in history
        history_entry = {
            "execution_id": execution_id,
            "session_id": execution_info["session_id"],
            "user_id": execution_info["user_id"],
            "code_hash": hashlib.sha256(execution_info["code"].encode()).hexdigest()[:16],
            "duration": duration,
            "success": success,
            "output_length": len(output),
            "error": error[:200] if error else None,  # Truncate error for storage
            "timestamp": end_time.isoformat()
        }
        
        self.execution_history.append(history_entry)
        
        # Keep only recent history (last 1000 executions)
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
        
        # Clean up active execution
        del self.active_executions[execution_id]
        
        # Log security events
        if not success and error:
            self.logger.warning(f"Code execution failed: {error[:100]}")
        
        if duration > self.limits.max_execution_time * 0.8:  # 80% of limit
            self.logger.warning(f"Code execution took {duration:.2f}s (close to limit)")
    
    def _check_rate_limits(self, user_key: str) -> bool:
        """Check if user has exceeded rate limits."""
        
        if user_key not in self.user_execution_counts:
            return True
        
        now = datetime.now(timezone.utc)
        executions = self.user_execution_counts[user_key]
        
        # Clean old entries
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        recent_executions = [ex for ex in executions if ex > minute_ago]
        hourly_executions = [ex for ex in executions if ex > hour_ago]
        
        # Update the list with cleaned entries
        self.user_execution_counts[user_key] = hourly_executions
        
        # Check limits
        if len(recent_executions) >= self.max_executions_per_minute:
            return False
        
        if len(hourly_executions) >= self.max_executions_per_hour:
            return False
        
        return True
    
    def get_user_stats(self, user_key: str) -> Dict[str, Any]:
        """Get execution statistics for a user."""
        
        if user_key not in self.user_execution_counts:
            return {"executions_last_hour": 0, "executions_last_minute": 0}
        
        now = datetime.now(timezone.utc)
        executions = self.user_execution_counts[user_key]
        
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        recent_executions = len([ex for ex in executions if ex > minute_ago])
        hourly_executions = len([ex for ex in executions if ex > hour_ago])
        
        return {
            "executions_last_minute": recent_executions,
            "executions_last_hour": hourly_executions,
            "max_per_minute": self.max_executions_per_minute,
            "max_per_hour": self.max_executions_per_hour
        }
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get overall monitoring statistics."""
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for ex in self.execution_history if ex["success"])
        
        return {
            "active_executions": len(self.active_executions),
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "error_rate": (total_executions - successful_executions) / max(total_executions, 1),
            "unique_users": len(self.user_execution_counts)
        }


class SecureVoiceCodeExecutor:
    """Secure wrapper for voice code execution with comprehensive security measures."""
    
    def __init__(self, base_executor, limits: Optional[ExecutionLimits] = None):
        self.base_executor = base_executor
        self.limits = limits or ExecutionLimits()
        self.analyzer = CodeSecurityAnalyzer()
        self.monitor = VoiceExecutionMonitor(self.limits)
        self.logger = logging.getLogger(__name__)
    
    async def secure_execute(
        self, 
        code: str, 
        session: 'EnhancedVoiceSession',
        execution_id: Optional[str] = None
    ) -> Tuple[bool, str, List[SecurityViolation]]:
        """Execute code with comprehensive security checks."""
        
        if execution_id is None:
            execution_id = hashlib.sha256(f"{session.session_id}{code}{datetime.now()}".encode()).hexdigest()[:16]
        
        # Step 1: Security analysis
        violations = self.analyzer.analyze_code(code)
        
        # Check for critical violations
        critical_violations = [v for v in violations if v.severity == SecurityLevel.CRITICAL]
        if critical_violations:
            await session.log_event("security_violation", {
                "violations": [v.to_dict() for v in critical_violations],
                "code_blocked": True
            })
            
            violation_msg = f"Code execution blocked due to security violations: {', '.join([v.description for v in critical_violations])}"
            return False, violation_msg, violations
        
        # Step 2: Rate limiting check
        if not self.monitor.start_execution_monitoring(execution_id, session, code):
            return False, "Rate limit exceeded. Please wait before executing more code.", []
        
        try:
            # Step 3: Execute with timeout
            result = await asyncio.wait_for(
                self.base_executor.execute(code, timeout=self.limits.max_execution_time),
                timeout=self.limits.max_execution_time + 5  # Extra buffer
            )
            
            # Step 4: Validate output
            if len(result.output) > self.limits.max_output_length:
                result.output = result.output[:self.limits.max_output_length] + "\n[Output truncated for security]"
            
            # Step 5: Log execution
            await session.log_event("secure_code_execution", {
                "execution_id": execution_id,
                "success": result.success,
                "violations_count": len(violations),
                "output_length": len(result.output)
            })
            
            # Step 6: End monitoring
            self.monitor.end_execution_monitoring(
                execution_id, 
                result.success, 
                result.output, 
                result.error
            )
            
            if result.success:
                return True, result.output, violations
            else:
                return False, result.error, violations
        
        except asyncio.TimeoutError:
            self.monitor.end_execution_monitoring(execution_id, False, "", "Execution timeout")
            return False, f"Code execution timed out after {self.limits.max_execution_time} seconds", violations
        
        except Exception as e:
            self.monitor.end_execution_monitoring(execution_id, False, "", str(e))
            self.logger.error(f"Error in secure code execution: {e}")
            return False, f"Execution error: {str(e)}", violations
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get comprehensive security statistics."""
        return {
            "monitoring": self.monitor.get_monitoring_stats(),
            "limits": {
                "max_execution_time": self.limits.max_execution_time,
                "max_memory_mb": self.limits.max_memory_mb,
                "max_output_length": self.limits.max_output_length,
                "allowed_imports": len(self.limits.allowed_imports)
            }
        }