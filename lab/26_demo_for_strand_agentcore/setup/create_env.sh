#!/bin/bash

# Environment setup script for standup agent demo
# Usage: ./create_env.sh

echo "Creating Python environment for standup-agent..."

# Install dependencies from pyproject.toml using uv
echo "Setting up environment with uv..."
cd "$(dirname "$0")"

echo "Installing dependencies..."
uv sync

echo "Environment created successfully!"
echo ""
echo "To run the agent locally:"
echo "  export GITHUB_TOKEN=your_github_pat_here"
echo "  export DEV_NAME=alex"
echo "  cd .."
echo "  uv run agent.py"
echo ""
echo "To run tests:"
echo "  uv run pytest tests/test_agent.py -v"
echo ""
echo "Don't forget to configure AWS credentials:"
echo "  aws configure"
