# 🚀 Getting Started with LumenAI

## Prerequisites

Choose one of the following setups:

### Option A: Docker (Easiest - Recommended for Production)
- **Docker** (version 20.10+) and **Docker Compose** (version 2.0+)

### Option B: Mamba/Conda (Best for Development)
- **Mamba** or **Conda** (automatically installed by setup script)
- **Node.js 20+** and **npm** (for frontend)

### Option C: Manual Setup
- **Python 3.11+**
- **Node.js 20+** and **npm**
- **MongoDB**, **Redis**, **ChromaDB** (manual installation)

---

## 🐍 Quick Start with Mamba (Recommended for ML Development)

Perfect for data scientists and ML engineers who want to experiment locally!

### 1. Clone the Repository

```bash
git clone <repository-url>
cd LumenAI-Life-Intelligence-System
```

### 2. One-Command Setup

```bash
# This will install Mamba and create the environment
make mamba-setup

# Or run directly:
./setup_mamba.sh
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY
```

### 4. Activate and Run

```bash
# Activate the environment
mamba activate lumenai

# Start backend
make backend-dev
```

In a separate terminal:
```bash
# Start frontend
make frontend-dev
```

Visit http://localhost:3000 - you're ready! 🎉

**See [Mamba Setup Guide](./MAMBA_SETUP.md) for detailed instructions.**

---

## 🐳 Quick Start with Docker (Production-Ready)

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

## Comparison: Mamba vs Docker

| Feature | Mamba | Docker |
|---------|-------|--------|
| **Setup Time** | 5-10 min | 2-3 min |
| **Disk Space** | 2-7 GB | 10-15 GB |
| **Startup Speed** | Fast (~5s) | Medium (~30s) |
| **Hot Reload** | ✅ Native | ✅ Volume mount |
| **Jupyter Notebooks** | ✅ Yes | ⚠️ Requires config |
| **ML Experimentation** | ✅✅✅ Perfect | ⚠️ OK |
| **Production Deploy** | ❌ No | ✅✅✅ Perfect |
| **Team Consistency** | ⚠️ Platform-dependent | ✅ Identical |
| **Database Services** | ⚠️ Manual | ✅ Automatic |

**Our recommendation:** Use Mamba for development, Docker for production!

---

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
