#!/bin/bash

# LumenAI Mamba Environment Setup Script
# Automatically installs Mamba and sets up the LumenAI environment

set -e

echo "🐍 LumenAI Mamba Environment Setup"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if mamba is installed
if ! command -v mamba &> /dev/null; then
    echo -e "${YELLOW}Mamba not found. Installing Miniforge (includes Mamba)...${NC}"
    echo ""

    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="MacOSX"
    else
        echo -e "${RED}Unsupported OS: $OSTYPE${NC}"
        exit 1
    fi

    # Detect architecture
    ARCH=$(uname -m)

    # Download Miniforge
    MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-${OS}-${ARCH}.sh"

    echo "Downloading Miniforge from: $MINIFORGE_URL"
    curl -L -O "$MINIFORGE_URL"

    # Install Miniforge
    bash "Miniforge3-${OS}-${ARCH}.sh" -b -p "$HOME/miniforge3"
    rm "Miniforge3-${OS}-${ARCH}.sh"

    # Initialize
    "$HOME/miniforge3/bin/conda" init bash

    echo ""
    echo -e "${GREEN}✅ Miniforge installed successfully!${NC}"
    echo -e "${YELLOW}⚠️  Please run: source ~/.bashrc (or restart your terminal)${NC}"
    echo -e "${YELLOW}⚠️  Then run this script again.${NC}"
    exit 0
else
    echo -e "${GREEN}✅ Mamba is already installed${NC}"
fi

echo ""

# Ask which environment to create
echo "Which environment would you like to create?"
echo "1) Full environment (includes ML, vision, audio processing) - Recommended"
echo "2) Minimal environment (just core dependencies)"
echo ""
read -p "Enter choice [1-2]: " env_choice

if [ "$env_choice" = "2" ]; then
    ENV_FILE="environment-minimal.yml"
    ENV_NAME="lumenai-minimal"
    echo -e "${YELLOW}Creating minimal environment...${NC}"
else
    ENV_FILE="environment.yml"
    ENV_NAME="lumenai"
    echo -e "${YELLOW}Creating full environment...${NC}"
fi

echo ""

# Check if environment already exists
if mamba env list | grep -q "^${ENV_NAME} "; then
    echo -e "${YELLOW}Environment '${ENV_NAME}' already exists.${NC}"
    read -p "Do you want to update it? [y/N]: " update_choice

    if [[ "$update_choice" =~ ^[Yy]$ ]]; then
        echo "Updating environment..."
        mamba env update -f "$ENV_FILE" --prune
    else
        echo "Skipping environment creation."
    fi
else
    echo "Creating new environment from $ENV_FILE..."
    mamba env create -f "$ENV_FILE"
fi

echo ""
echo -e "${GREEN}✅ Environment setup complete!${NC}"
echo ""
echo "To activate the environment, run:"
echo -e "${GREEN}  mamba activate ${ENV_NAME}${NC}"
echo ""
echo "To deactivate:"
echo -e "${GREEN}  mamba deactivate${NC}"
echo ""

# Install frontend dependencies if Node.js is available
if command -v npm &> /dev/null; then
    echo "Installing frontend dependencies..."
    cd frontend/lumenai-app
    npm install
    cd ../..
    echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  npm not found. Skipping frontend setup.${NC}"
    echo "   Install Node.js to set up the frontend."
fi

echo ""
echo "🎯 Next steps:"
echo "1. Activate environment: mamba activate ${ENV_NAME}"
echo "2. Copy environment file: cp .env.example .env"
echo "3. Add your API keys to .env"
echo "4. Start backend: cd backend && uvicorn gateway.main:app --reload"
echo "5. Start frontend: cd frontend/lumenai-app && npm run dev"
echo ""
echo "Or use Docker Compose: docker-compose up --build"
echo ""
echo "Happy coding with LumenAI! 🌟"
