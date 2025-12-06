# 🐳 Docker Setup Guide - LumenAI v2.0

This guide explains how to run LumenAI using Docker containers for a complete, isolated installation.

## 📋 Prerequisites

1. **Docker Desktop** (macOS/Windows) or **Docker Engine** (Linux)
   - Download: https://www.docker.com/get-started
   - Minimum 4GB RAM allocated to Docker
   - 10GB free disk space

2. **Docker Compose**
   - Included with Docker Desktop
   - Linux: Install separately if needed

## 🚀 Quick Start

### Option 1: Automated Start Script (Recommended)

```bash
./start.sh
```

This script will:
- ✅ Create `.env` from template if missing
- ✅ Validate Docker is running
- ✅ Build all Docker images
- ✅ Start all services with health checks
- ✅ Wait for services to be ready
- ✅ Display access URLs

### Option 2: Manual Docker Compose

```bash
# 1. Create .env file
cp .env.example .env

# 2. (Optional) Edit .env and add your API keys
nano .env

# 3. Build and start services
docker-compose up --build -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f
```

## 🏗️ Architecture

LumenAI runs 5 Docker containers:

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Frontend | `lumenai-frontend` | 3000 | Next.js React app |
| Backend | `lumenai-backend` | 8000 | FastAPI Python server |
| MongoDB | `lumenai-mongodb` | 27017 | User data & conversations |
| ChromaDB | `lumenai-chromadb` | 8001 | Vector embeddings |
| Redis | `lumenai-redis` | 6379 | Caching layer |

## 🔧 Configuration

### Environment Variables

The `.env` file contains all configuration. Key variables:

```bash
# Required for AI features
OPENAI_API_KEY="sk-..."          # OpenAI API key
ANTHROPIC_API_KEY="sk-ant-..."   # Anthropic API key

# Database connections (auto-configured for Docker)
MONGODB_URL="mongodb://mongodb:27017"
CHROMA_HOST="chromadb"
REDIS_URL="redis://redis:6379"

# Security (auto-generated, keep secret!)
SECRET_KEY="..."                  # JWT signing key
ALLOWED_ORIGINS='["http://localhost:3000","http://localhost:8000"]'
```

### Persistent Data

Data is stored in Docker volumes:
- `mongodb_data` - User data, conversations, tasks
- `chromadb_data` - Vector embeddings
- `redis_data` - Cache
- `backend_data` - Application data

To reset all data:
```bash
docker-compose down -v  # WARNING: Deletes all data!
```

## 🎯 Access Points

After startup, access:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/db/health

## 📊 Management Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Check Status
```bash
docker-compose ps
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart backend
```

### Stop Services
```bash
# Stop but keep containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything (including volumes)
docker-compose down -v
```

### Rebuild After Changes
```bash
# Rebuild all images
docker-compose build --no-cache

# Rebuild specific service
docker-compose build --no-cache backend

# Rebuild and restart
docker-compose up --build -d
```

## 🐛 Troubleshooting

### Services Won't Start

**Check if ports are in use:**
```bash
# macOS/Linux
lsof -i :3000
lsof -i :8000

# Windows
netstat -ano | findstr :3000
netstat -ano | findstr :8000
```

**Solution:** Stop conflicting services or change ports in `docker-compose.yml`

### Connection Errors

**Problem:** "Cannot connect to server"

**Solutions:**
1. Check if backend is healthy: `docker-compose ps`
2. View backend logs: `docker-compose logs backend`
3. Verify .env has correct values
4. Restart backend: `docker-compose restart backend`

### Database Connection Failed

**Problem:** "MongoDB connection failed"

**Solutions:**
1. Check MongoDB status: `docker-compose ps mongodb`
2. View MongoDB logs: `docker-compose logs mongodb`
3. Restart MongoDB: `docker-compose restart mongodb`
4. Reset data: `docker-compose down -v && docker-compose up -d`

### Out of Memory

**Problem:** Services crash or become slow

**Solutions:**
1. Increase Docker memory:
   - Docker Desktop → Settings → Resources → Memory (4GB+)
2. Reduce running containers
3. Clear unused Docker data: `docker system prune`

### Build Failures

**Problem:** "npm install failed" or "pip install failed"

**Solutions:**
1. Clear Docker build cache: `docker-compose build --no-cache`
2. Check internet connection
3. Restart Docker Desktop
4. Remove old images: `docker system prune -a`

## 🔄 Updates & Maintenance

### Update LumenAI

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild images
docker-compose build --no-cache

# 3. Restart services
docker-compose up -d
```

### Clean Up

```bash
# Remove unused images
docker image prune

# Remove all unused resources
docker system prune -a

# Remove volumes (WARNING: deletes data!)
docker volume prune
```

## 🎓 Advanced

### Development Mode

Edit code and see changes without rebuild:

```bash
# Already configured in docker-compose.yml
# Backend: auto-reload on code changes
# Frontend: hot-reload enabled
```

### Production Deployment

For production, use:

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start with production config
docker-compose -f docker-compose.prod.yml up -d
```

### Scaling

Run multiple backend instances:

```bash
docker-compose up --scale backend=3 -d
```

### Custom Network

Containers communicate via `lumenai-network` bridge network.

To inspect:
```bash
docker network inspect lumenai-network
```

## 📞 Support

If you encounter issues:

1. Check logs: `docker-compose logs`
2. Verify status: `docker-compose ps`
3. Review this guide's troubleshooting section
4. Create issue: https://github.com/Marksio90/LumenAI-Life-Intelligence-System/issues

## ✅ Success Checklist

After running `./start.sh`, verify:

- [ ] All 5 containers are "Up (healthy)"
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend API docs at http://localhost:8000/docs
- [ ] Health check returns `{"status": "healthy"}`
- [ ] Chat interface loads without errors
- [ ] Can send messages (if API keys configured)

---

**Happy containerizing! 🐳🌟**
