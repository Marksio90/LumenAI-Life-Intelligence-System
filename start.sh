#!/bin/bash

# LumenAI Quick Start Script
# This script helps you get LumenAI up and running quickly

set -e

echo "🌟 LumenAI - Life Intelligence System v2.0"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created!"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your API keys:"
    echo "   - OPENAI_API_KEY or ANTHROPIC_API_KEY"
    echo ""
    echo "ℹ️  You can skip this for now and add them later."
    echo "   LumenAI will still work, but AI features will be disabled."
    echo ""
    read -p "Press Enter to continue..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    echo ""
    echo "To start Docker:"
    echo "  - macOS/Windows: Open Docker Desktop"
    echo "  - Linux: sudo systemctl start docker"
    exit 1
fi

echo "🐳 Docker is running!"
echo ""

# Check if docker-compose is available (try both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose is not installed. Please install it first."
    echo ""
    echo "Installation instructions:"
    echo "  https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ docker-compose is available!"
echo ""

# Clean up old containers if they exist
echo "🧹 Cleaning up old containers..."
$DOCKER_COMPOSE down -v 2>/dev/null || true

# Build and start services
echo "🏗️  Building Docker images (this may take a few minutes)..."
echo ""
$DOCKER_COMPOSE build --no-cache

echo ""
echo "🚀 Starting LumenAI services..."
echo ""
$DOCKER_COMPOSE up -d

echo ""
echo "⏳ Waiting for services to initialize..."
echo "   This may take up to 60 seconds..."
echo ""

# Wait for health checks
for i in {1..60}; do
    if $DOCKER_COMPOSE ps | grep -q "healthy"; then
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo ""

# Check if services are running
if $DOCKER_COMPOSE ps | grep -q "Up"; then
    echo "✅ LumenAI is up and running!"
    echo ""
    echo "📱 Access your services:"
    echo "   Frontend:     http://localhost:3000"
    echo "   Backend API:  http://localhost:8000"
    echo "   API Docs:     http://localhost:8000/docs"
    echo ""
    echo "📊 View logs:"
    echo "   $DOCKER_COMPOSE logs -f"
    echo ""
    echo "📋 Check service status:"
    echo "   $DOCKER_COMPOSE ps"
    echo ""
    echo "🛑 Stop services:"
    echo "   $DOCKER_COMPOSE down"
    echo ""
    echo "🔄 Restart services:"
    echo "   $DOCKER_COMPOSE restart"
    echo ""
    echo "Happy chatting with LumenAI! 🌟"
    echo ""
    echo "💡 Tip: If you see connection errors, make sure to add your API keys to .env"
else
    echo "❌ Something went wrong starting services."
    echo ""
    echo "📋 Service status:"
    $DOCKER_COMPOSE ps
    echo ""
    echo "📊 Check logs with:"
    echo "   $DOCKER_COMPOSE logs"
    echo ""
    echo "Common issues:"
    echo "  1. Ports 3000 or 8000 already in use"
    echo "  2. Missing API keys in .env file"
    echo "  3. Insufficient Docker resources"
    exit 1
fi
