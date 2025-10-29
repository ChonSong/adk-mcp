"""Tests for Python code executor."""

import pytest
import asyncio
from adk_mcp.executor import PythonExecutor, SafePythonExecutor


@pytest.mark.asyncio
async def test_simple_execution():
    """Test executing simple Python code."""
    executor = PythonExecutor(timeout=10)
    
    code = "print('Hello from executor')"
    result = await executor.execute(code)
    
    assert result.success
    assert "Hello from executor" in result.output
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execution_with_output():
    """Test code execution with output capture."""
    executor = PythonExecutor(timeout=10)
    
    code = """
x = 10
y = 20
print(f"Sum: {x + y}")
"""
    result = await executor.execute(code)
    
    assert result.success
    assert "Sum: 30" in result.output


@pytest.mark.asyncio
async def test_execution_with_error():
    """Test code execution with error."""
    executor = PythonExecutor(timeout=10)
    
    code = "raise ValueError('Test error')"
    result = await executor.execute(code)
    
    assert not result.success
    assert result.error is not None
    assert "ValueError" in result.error


@pytest.mark.asyncio
async def test_execution_timeout():
    """Test execution timeout."""
    executor = PythonExecutor(timeout=1)
    
    code = """
import time
time.sleep(5)
print("Should not reach here")
"""
    result = await executor.execute(code)
    
    assert not result.success
    assert "timed out" in result.error


@pytest.mark.asyncio
async def test_safe_executor_blocks_dangerous_code():
    """Test that safe executor blocks dangerous patterns."""
    executor = SafePythonExecutor(timeout=10, enable_safety_checks=True)
    
    # Test blocking imports
    code = "import os"
    result = await executor.execute(code)
    
    assert not result.success
    assert "blocked pattern" in result.error


@pytest.mark.asyncio
async def test_safe_executor_allows_safe_code():
    """Test that safe executor allows safe code."""
    executor = SafePythonExecutor(timeout=10, enable_safety_checks=True)
    
    code = """
x = [1, 2, 3, 4, 5]
total = sum(x)
print(f"Total: {total}")
"""
    result = await executor.execute(code)
    
    assert result.success
    assert "Total: 15" in result.output


def test_sync_execution():
    """Test synchronous execution wrapper."""
    executor = PythonExecutor(timeout=10)
    
    code = "print('Sync execution')"
    result = executor.execute_sync(code)
    
    assert result.success
    assert "Sync execution" in result.output
