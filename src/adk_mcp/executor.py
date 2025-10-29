"""Python code execution module for ADK-MCP."""

import asyncio
import subprocess
import sys
import tempfile
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Result of Python code execution."""
    
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
        }


class PythonExecutor:
    """Executes Python code server-side using subprocess (simple implementation)."""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize Python executor.
        
        Args:
            timeout: Maximum execution time in seconds
        """
        self.timeout = timeout
        self.python_executable = sys.executable
        
    async def execute(self, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """
        Execute Python code in a subprocess.
        
        Args:
            code: Python code to execute
            timeout: Optional timeout override
            
        Returns:
            ExecutionResult containing output and status
        """
        exec_timeout = timeout or self.timeout
        
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False
        ) as tmp_file:
            tmp_file.write(code)
            tmp_file_path = tmp_file.name
        
        try:
            # Execute the code using subprocess
            result = await asyncio.wait_for(
                self._run_subprocess(tmp_file_path),
                timeout=exec_timeout
            )
            return result
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {exec_timeout} seconds",
                exit_code=-1
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass
    
    async def _run_subprocess(self, script_path: str) -> ExecutionResult:
        """
        Run Python script in subprocess.
        
        Args:
            script_path: Path to Python script file
            
        Returns:
            ExecutionResult
        """
        try:
            process = await asyncio.create_subprocess_exec(
                self.python_executable,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode('utf-8') if stdout else ""
            stderr_str = stderr.decode('utf-8') if stderr else ""
            
            success = process.returncode == 0
            
            return ExecutionResult(
                success=success,
                output=stdout_str,
                error=stderr_str if not success else None,
                exit_code=process.returncode
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                exit_code=-1
            )
    
    def execute_sync(self, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """
        Synchronous wrapper for execute method.
        
        Args:
            code: Python code to execute
            timeout: Optional timeout override
            
        Returns:
            ExecutionResult
        """
        return asyncio.run(self.execute(code, timeout))


class SafePythonExecutor(PythonExecutor):
    """
    Enhanced executor with basic safety checks.
    
    Note: This is a simple implementation. Future versions should use
    Docker sandboxing for proper security isolation.
    """
    
    # List of dangerous imports/operations to block
    BLOCKED_PATTERNS = [
        "import os",
        "import subprocess",
        "import sys",
        "__import__",
        "eval(",
        "exec(",
        "compile(",
        "open(",
        "file(",
    ]
    
    def __init__(self, timeout: int = 30, enable_safety_checks: bool = True):
        super().__init__(timeout)
        self.enable_safety_checks = enable_safety_checks
    
    async def execute(self, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """Execute code with safety checks."""
        if self.enable_safety_checks:
            # Check for blocked patterns
            for pattern in self.BLOCKED_PATTERNS:
                if pattern in code:
                    return ExecutionResult(
                        success=False,
                        output="",
                        error=f"Code contains blocked pattern: {pattern}",
                        exit_code=-1
                    )
        
        return await super().execute(code, timeout)
