"""Example: Python code execution."""

import asyncio
from adk_mcp.executor import PythonExecutor, SafePythonExecutor


async def main():
    """Demonstrate Python code execution."""
    print("Python Executor Demo\n")
    print("=" * 50)
    
    # Create executor
    executor = PythonExecutor(timeout=10)
    
    # Example 1: Simple calculation
    print("\n1. Simple calculation:")
    code1 = """
x = 10
y = 20
result = x + y
print(f"The sum of {x} and {y} is {result}")
"""
    result1 = await executor.execute(code1)
    print(f"Success: {result1.success}")
    print(f"Output: {result1.output.strip()}")
    
    # Example 2: List operations
    print("\n2. List operations:")
    code2 = """
numbers = [1, 2, 3, 4, 5]
squared = [n**2 for n in numbers]
print(f"Original: {numbers}")
print(f"Squared: {squared}")
"""
    result2 = await executor.execute(code2)
    print(f"Output:\n{result2.output.strip()}")
    
    # Example 3: Error handling
    print("\n3. Error handling:")
    code3 = """
result = 10 / 0
"""
    result3 = await executor.execute(code3)
    print(f"Success: {result3.success}")
    print(f"Error: {result3.error.strip() if result3.error else 'None'}")
    
    # Example 4: Safe executor
    print("\n4. Safe executor (blocks dangerous code):")
    safe_executor = SafePythonExecutor(enable_safety_checks=True)
    code4 = "import os"
    result4 = await safe_executor.execute(code4)
    print(f"Success: {result4.success}")
    print(f"Error: {result4.error}")
    
    print("\n" + "=" * 50)
    print("✓ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
