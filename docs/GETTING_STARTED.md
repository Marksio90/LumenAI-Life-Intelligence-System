# 🚀 Getting Started with LumenAI

## Prerequisites

Before you begin, ensure you have the following installed:
- **Docker** (version 20.10+) and **Docker Compose** (version 2.0+)
- **Python 3.11+** (for local development)
- **Node.js 20+** and **npm** (for frontend development)
- **Git**

## Quick Start (Docker - Recommended)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd LumenAI-Life-Intelligence-System
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required for full functionality
OPENAI_API_KEY=sk-your-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Start the System

```bash
docker-compose up --build
```

This will start all services:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- MongoDB, Redis, ChromaDB (internal)

### 4. Open LumenAI

Visit http://localhost:3000 in your browser and start chatting!

## Local Development (Without Docker)

### Backend Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run backend
cd backend
uvicorn gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Install dependencies
cd frontend/lumenai-app
npm install

# Run frontend
npm run dev
```

Visit http://localhost:3000

## Using Makefile Commands

We provide a Makefile for common tasks:

```bash
make install   # Install all dependencies
make up        # Start services
make down      # Stop services
make logs      # View logs
make clean     # Clean everything
make test      # Run tests
```

## Architecture Overview

```
┌─────────────────┐
│   Frontend      │  Next.js + React + TailwindCSS
│   (Port 3000)   │
└────────┬────────┘
         │
         │ WebSocket + REST
         │
┌────────▼────────┐
│   Backend API   │  FastAPI + WebSocket
│   (Port 8000)   │
└────────┬────────┘
         │
    ┌────┴────┬─────────┬──────────┐
    │         │         │          │
┌───▼──┐  ┌──▼───┐  ┌──▼────┐  ┌──▼──────┐
│MongoDB│ │Redis │ │ChromaDB│ │LLM APIs │
│Users  │ │Cache │ │Vectors │ │GPT/Claude│
└───────┘ └──────┘ └────────┘ └─────────┘
```

## Available Agents

LumenAI includes several specialized agents:

1. **Planner Agent** 📅
   - Task management
   - Calendar integration
   - Daily planning

2. **Mood Agent** 💭
   - Emotional support
   - Mood tracking
   - CBT/DBT techniques

3. **Decision Agent** 🤔
   - Life decisions
   - Pros/cons analysis
   - Decision frameworks

## Next Steps

- Read the [Architecture Documentation](./ARCHITECTURE.md)
- Check [API Documentation](http://localhost:8000/docs) when backend is running
- Explore [Configuration Options](./CONFIGURATION.md)
- Learn about [Adding Custom Agents](./CUSTOM_AGENTS.md)

## Troubleshooting

### Backend won't start
- Check if ports 8000, 27017, 6379, 8001 are available
- Verify your API keys in `.env`
- Check logs: `docker-compose logs backend`

### Frontend can't connect
- Ensure backend is running at http://localhost:8000
- Check NEXT_PUBLIC_API_URL in your environment
- Verify CORS settings in backend

### LLM responses are mocked
- Add valid OPENAI_API_KEY or ANTHROPIC_API_KEY to `.env`
- Restart backend after adding keys

## Support

For issues and questions:
- Check existing issues on GitHub
- Read the documentation in `/docs`
- Review logs with `make logs`

Happy coding with LumenAI! 🌟
