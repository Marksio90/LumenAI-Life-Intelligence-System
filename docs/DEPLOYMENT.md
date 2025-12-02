# 🚀 LumenAI Deployment Guide

## Development Deployment

### Quick Start with Docker Compose

```bash
# 1. Clone and navigate
git clone <repo-url>
cd LumenAI-Life-Intelligence-System

# 2. Configure environment
cp .env.example .env
# Edit .env and add your API keys

# 3. Start all services
docker-compose up --build

# 4. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Using Makefile

```bash
make install  # Install dependencies
make up       # Start services
make logs     # View logs
make down     # Stop services
```

## Production Deployment

### Prerequisites
- Docker and Docker Compose
- Domain name (for SSL)
- Reverse proxy (nginx/traefik)
- API keys for LLM providers

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.backend
    environment:
      - DEBUG=False
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: always
    networks:
      - lumenai-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.lumenai-api.rule=Host(`api.yourdomain.com`)"

  frontend:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.frontend
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
    restart: always
    networks:
      - lumenai-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.lumenai.rule=Host(`app.yourdomain.com`)"

  # ... other services
```

### Environment Variables (Production)

```bash
# Production .env
DEBUG=False
ENVIRONMENT=production
SECRET_KEY=<generate-strong-secret-key>

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database URLs
MONGODB_URL=mongodb://mongo:27017
REDIS_HOST=redis

# Security
ALLOWED_ORIGINS=https://app.yourdomain.com

# Logging
LOG_LEVEL=WARNING
```

### SSL/TLS Configuration

#### Using Let's Encrypt with Traefik

Add to `docker-compose.prod.yml`:

```yaml
  traefik:
    image: traefik:v2.10
    command:
      - --providers.docker=true
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.letsencrypt.acme.email=your@email.com
      - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
      - --certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./letsencrypt:/letsencrypt
```

## Cloud Deployment

### AWS ECS Deployment

1. **Build and push Docker images**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker build -f infra/docker/Dockerfile.backend -t lumenai-backend .
docker tag lumenai-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/lumenai-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/lumenai-backend:latest
```

2. **Create ECS Task Definition**
3. **Set up ECS Service**
4. **Configure Application Load Balancer**
5. **Set environment variables in ECS Task**

### Google Cloud Run

```bash
# Build and deploy backend
gcloud builds submit --tag gcr.io/PROJECT_ID/lumenai-backend
gcloud run deploy lumenai-backend \
  --image gcr.io/PROJECT_ID/lumenai-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=sk-...

# Build and deploy frontend
gcloud builds submit --tag gcr.io/PROJECT_ID/lumenai-frontend ./frontend/lumenai-app
gcloud run deploy lumenai-frontend \
  --image gcr.io/PROJECT_ID/lumenai-frontend \
  --platform managed \
  --region us-central1 \
  --set-env-vars NEXT_PUBLIC_API_URL=https://backend-url
```

### Kubernetes Deployment

See `infra/kubernetes/` for manifests:

```bash
# Apply configurations
kubectl apply -f infra/kubernetes/namespace.yaml
kubectl apply -f infra/kubernetes/secrets.yaml
kubectl apply -f infra/kubernetes/backend-deployment.yaml
kubectl apply -f infra/kubernetes/frontend-deployment.yaml
kubectl apply -f infra/kubernetes/services.yaml
kubectl apply -f infra/kubernetes/ingress.yaml
```

## Database Setup

### MongoDB

```bash
# Production MongoDB with authentication
docker run -d \
  --name lumenai-mongo \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=secure_password \
  -v mongo-data:/data/db \
  -p 27017:27017 \
  mongo:7.0
```

### Redis

```bash
# Production Redis with password
docker run -d \
  --name lumenai-redis \
  -e REDIS_PASSWORD=secure_password \
  -v redis-data:/data \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --requirepass secure_password
```

## Monitoring & Logging

### Prometheus + Grafana

Add to `docker-compose.prod.yml`:

```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infra/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Log Aggregation

Use ELK stack or cloud-native solutions:
- AWS CloudWatch
- Google Cloud Logging
- Datadog
- New Relic

## Backup Strategy

### MongoDB Backup

```bash
# Backup
docker exec lumenai-mongo mongodump --out /backup

# Restore
docker exec lumenai-mongo mongorestore /backup
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * docker exec lumenai-mongo mongodump --out /backup/$(date +\%Y\%m\%d)
```

## Security Checklist

- [ ] Strong SECRET_KEY set
- [ ] API keys in environment variables (not code)
- [ ] HTTPS enabled (SSL/TLS)
- [ ] Database authentication enabled
- [ ] Firewall rules configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Regular security updates
- [ ] Backup strategy in place
- [ ] Monitoring and alerting setup

## Scaling Considerations

### Horizontal Scaling
- Use load balancer (nginx/AWS ALB/GCP LB)
- Run multiple backend instances
- Shared Redis and MongoDB
- Session stickiness for WebSockets

### Database Scaling
- MongoDB replica set
- Redis cluster
- Read replicas
- Sharding for large datasets

### Performance Optimization
- Enable Redis caching
- CDN for frontend assets
- Database indexing
- Connection pooling
- Response compression

## Troubleshooting

### Backend fails to start
```bash
# Check logs
docker-compose logs backend

# Verify environment
docker-compose exec backend env | grep API_KEY

# Test database connection
docker-compose exec backend python -c "from pymongo import MongoClient; print(MongoClient('mongodb://mongo:27017').server_info())"
```

### High memory usage
- Limit Docker container memory
- Optimize LLM token usage
- Implement response caching
- Clean up old conversations

### WebSocket connection issues
- Check reverse proxy configuration
- Verify WebSocket support
- Check CORS settings
- Monitor connection limits

## Cost Optimization

### LLM API Costs
- Implement response caching
- Use cheaper models for simple tasks
- Set token limits
- Monitor usage with dashboards

### Infrastructure Costs
- Use spot instances (AWS)
- Preemptible VMs (GCP)
- Auto-scaling policies
- Reserved instances for steady load

---

For more details, see the [Architecture Documentation](./ARCHITECTURE.md)
