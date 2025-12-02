#!/bin/bash

# LumenAI Quick Start Script
# This script helps you get LumenAI up and running quickly

set -e

echo "🌟 LumenAI - Life Intelligence System"
echo "====================================="
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
    read -p "Press Enter when you've added your API keys..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "🐳 Docker is running!"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it first."
    exit 1
fi

echo "✅ docker-compose is available!"
echo ""

# Start services
echo "🚀 Starting LumenAI services..."
echo ""

docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ LumenAI is up and running!"
    echo ""
    echo "📱 Access your services:"
    echo "   Frontend:     http://localhost:3000"
    echo "   Backend API:  http://localhost:8000"
    echo "   API Docs:     http://localhost:8000/docs"
    echo ""
    echo "📊 View logs:"
    echo "   docker-compose logs -f"
    echo ""
    echo "🛑 Stop services:"
    echo "   docker-compose down"
    echo ""
    echo "Happy chatting with LumenAI! 🌟"
else
    echo ""
    echo "❌ Something went wrong. Check logs with:"
    echo "   docker-compose logs"
fi
