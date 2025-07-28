#!/bin/bash

#####################################
# Set virtual environment name
#####################################
# Always use .venv as the virtual environment name
export VirtualEnv=".venv"

echo "Setting up virtual environment: $VirtualEnv"

#####################################
# Install uv if not already installed
#####################################
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Verify UV installation
    if ! command -v uv &> /dev/null; then
        echo "Error: UV installation failed"
        exit 1
    fi
fi

# Always ensure UV is in PATH (whether newly installed or already present)
export PATH="$HOME/.local/bin:$PATH"

# Final verification that UV is accessible
if ! command -v uv &> /dev/null; then
    echo "Error: UV is not accessible. Please restart your terminal or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
fi

echo "UV is ready: $(uv --version)"

#####################################
# Create uv project and virtual environment
#####################################
echo "## Creating uv project and virtual environment"
uv python install 3.10
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python 3.10"
    exit 1
fi

uv venv --python 3.10
if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment"
    exit 1
fi

# wait for 5 seconds
echo "# Wait for 5 seconds to proceed with next step"
sleep 5

#####################################
# Activate the virtual environment
#####################################
echo "## Activating virtual environment"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment activation script not found"
    exit 1
fi

# show current virtual env
echo "# show current virtual environment"
which python
python --version
echo ""

# wait for 5 seconds
echo "## Finish creating virtual environment"
sleep 5

#####################################
# Initialize uv project and install packages
#####################################
echo "## Initializing uv project"
uv init
if [ $? -ne 0 ]; then
    echo "Error: Failed to initialize uv project"
    exit 1
fi

echo "## Installing packages from requirements.txt"
if [ -f "requirements.txt" ]; then
    uv add -r requirements.txt --active
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install packages from requirements.txt"
        exit 1
    fi
else
    echo "Warning: requirements.txt not found, skipping package installation"
fi

# wait for 5 seconds
echo "## Finish installing requirements.txt"
sleep 5

#####################################
# Install Jupyter kernel for notebook support
#####################################
echo "## Installing Jupyter kernel"
uv add ipykernel jupyter
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Jupyter packages"
    exit 1
fi

# Create Jupyter kernel
echo "## Creating Jupyter kernel"
python -m ipykernel install --user --name=.venv --display-name ".venv (Python 3.10.18)"
if [ $? -eq 0 ]; then
    echo "Jupyter kernel '.venv' created successfully"
else
    echo "Warning: Jupyter kernel creation failed"
fi

# wait for 5 seconds
echo "## Finish installing Jupyter kernel"
sleep 5

#####################################
# Show usage commands
#####################################
echo ""
echo "# Show important python packages"
uv pip list | grep -E "langchain|langgraph|bedrock" || echo "No langchain/langgraph/bedrock packages found"
echo ""

echo "# To activate this environment, use"
echo "#"
echo "# source .venv/bin/activate"
echo "#"
echo "# To deactivate an active environment, use"
echo "#"
echo "# deactivate"
echo "#"
echo "# To start Jupyter Lab, use"
echo "#"
echo "# uv run --with jupyter jupyter lab"
echo "#"
echo "# To run Python scripts, use"
echo "#"
echo "# uv run python your_script.py"
echo "#"
echo "# To add new packages, use"
echo "#"
echo "# uv add package_name"
echo "#"
echo "# To remove packages, use"
echo "#"
echo "# uv remove package_name"
echo "#"
echo "# To list installed packages, use"
echo "#"
echo "# uv pip list"
echo ""

echo "## Setup completed successfully! 🚀"