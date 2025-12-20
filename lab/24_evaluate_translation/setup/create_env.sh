#!/bin/bash

# Environment setup script for translation evaluation project
# Usage: ./create_env.sh [environment_name]

ENV_NAME=${1:-eval_translation}

echo "Creating Python environment: $ENV_NAME"

# Create virtual environment using uv
echo "Setting up environment with uv..."
cd "$(dirname "$0")"

# Install dependencies from pyproject.toml
echo "Installing dependencies..."
uv sync

echo "Environment '$ENV_NAME' created successfully!"
echo ""
echo "To activate the environment and run evaluations:"
echo "  cd script"
echo "  uv run eval_cometkiwi.py"
echo "  uv run eval_metricx.py"
echo "  uv run eval_llm_judge.py"
echo ""
echo "Don't forget to configure authentication:"
echo "  huggingface-cli login"
echo "  aws configure"