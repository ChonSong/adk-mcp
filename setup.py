"""Setup configuration for ADK-MCP (Agent Development Kit - MCP)."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="adk-mcp",
    version="0.1.0",
    author="ADK Team",
    description="Agent Development Kit with bidirectional streaming support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ChonSong/adk-mcp",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.12",
    install_requires=[
        "asyncio>=3.4.3",
        "websockets>=10.0",
        "aiohttp>=3.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
    },
)
