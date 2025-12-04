# LumenAI Kubernetes Deployment Guide

Complete guide for deploying the LumenAI platform to Kubernetes with enterprise-grade scalability, monitoring, and high availability.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Deployment](#detailed-deployment)
- [Configuration](#configuration)
- [Scaling](#scaling)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Production Best Practices](#production-best-practices)

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      NGINX Ingress                          │
│                   (Load Balancer + TLS)                     │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
         ┌────────▼────────┐     ┌───────▼────────┐
         │    Frontend     │     │    Backend     │
         │  (Next.js 14)   │     │  (FastAPI)     │
         │   3 replicas    │     │  3-20 replicas │
         │   HPA enabled   │     │  HPA enabled   │
         └─────────────────┘     └────────┬───────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
           ┌────────▼────────┐   ┌───────▼──────┐   ┌─────────▼────────┐
           │    MongoDB      │   │    Redis     │   │     Qdrant       │
           │  (Replica Set)  │   │  (Cluster)   │   │ (Vector Store)   │
           │   3 replicas    │   │  3 replicas  │   │   3 replicas     │
           │  100Gi storage  │   │  10Gi cache  │   │  50Gi vectors    │
           └─────────────────┘   └──────────────┘   └──────────────────┘
                    │                     │                     │
                    └─────────────────────┼─────────────────────┘
                                          │
                                ┌─────────▼─────────┐
                                │   Prometheus +    │
                                │     Grafana       │
                                │   (Monitoring)    │
                                └───────────────────┘
```

### Components

| Component | Type | Replicas | Scaling | Storage |
|-----------|------|----------|---------|---------|
| Backend | Deployment | 3-20 | HPA (CPU/Memory) | Ephemeral |
| Frontend | Deployment | 3-15 | HPA (CPU/Memory) | Ephemeral |
| MongoDB | StatefulSet | 3 | Manual/VPA | 100Gi PVC |
| Redis | StatefulSet | 3 | Manual/VPA | 10Gi PVC |
| Qdrant | StatefulSet | 3 | Manual/VPA | 50Gi PVC |
| Prometheus | Deployment | 1 | Manual | 50Gi PVC |
| Grafana | Deployment | 1 | Manual | 10Gi PVC |

## ✅ Prerequisites

### Required Tools

```bash
# Kubernetes CLI
kubectl version --client

# Helm (optional but recommended)
helm version

# Docker (for building images)
docker --version

# Optional: k9s (Kubernetes TUI)
brew install k9s
```

### Kubernetes Cluster

- **Minimum Version**: Kubernetes 1.24+
- **Recommended**: Kubernetes 1.28+
- **Node Requirements**:
  - 3+ nodes for production
  - 4 vCPUs per node
  - 16GB RAM per node
  - 100GB+ storage per node

### Cloud Provider Setup

<details>
<summary>Google Cloud (GKE)</summary>

```bash
# Create cluster
gcloud container clusters create lumenai-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --machine-type=n1-standard-4 \
  --enable-autoscaling \
  --min-nodes=3 \
  --max-nodes=10 \
  --enable-autorepair \
  --enable-autoupgrade

# Get credentials
gcloud container clusters get-credentials lumenai-cluster --zone=us-central1-a
```
</details>

<details>
<summary>AWS (EKS)</summary>

```bash
# Create cluster
eksctl create cluster \
  --name lumenai-cluster \
  --region us-west-2 \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --node-type t3.xlarge \
  --managed

# Update kubeconfig
aws eks update-kubeconfig --name lumenai-cluster --region us-west-2
```
</details>

<details>
<summary>Azure (AKS)</summary>

```bash
# Create cluster
az aks create \
  --resource-group lumenai-rg \
  --name lumenai-cluster \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10 \
  --network-plugin azure

# Get credentials
az aks get-credentials --resource-group lumenai-rg --name lumenai-cluster
```
</details>

## 🚀 Quick Start

### Option 1: Using Deployment Script (Recommended)

```bash
# Clone repository
git clone https://github.com/Marksio90/LumenAI-Life-Intelligence-System.git
cd LumenAI-Life-Intelligence-System/k8s/scripts

# Make script executable
chmod +x deploy.sh

# Deploy to development
./deploy.sh development

# Deploy to production
./deploy.sh production

# Dry run (test without applying)
./deploy.sh production --dry-run
```

### Option 2: Using Helm

```bash
cd helm/lumenai

# Install with default values
helm install lumenai . -n default

# Install with custom values
helm install lumenai . -n default -f custom-values.yaml

# Upgrade existing installation
helm upgrade lumenai . -n default
```

### Option 3: Manual kubectl Apply

```bash
cd k8s/base

# Create namespace
kubectl create namespace default

# Apply configurations in order
kubectl apply -f configmaps.yaml -n default
kubectl apply -f mongodb-statefulset.yaml -n default
kubectl apply -f redis-statefulset.yaml -n default
kubectl apply -f qdrant-statefulset.yaml -n default
kubectl apply -f backend-deployment.yaml -n default
kubectl apply -f frontend-deployment.yaml -n default
kubectl apply -f hpa.yaml -n default
kubectl apply -f ingress.yaml -n default

# Deploy monitoring
kubectl create namespace monitoring
kubectl apply -f ../monitoring/prometheus.yaml -n monitoring
kubectl apply -f ../monitoring/grafana.yaml -n monitoring
```

## 📝 Detailed Deployment

### Step 1: Configure Secrets

**IMPORTANT**: Update secrets before deploying to production!

```bash
# Edit secrets file
kubectl edit secret lumenai-backend-secrets -n default

# Or create from file
kubectl create secret generic lumenai-backend-secrets \
  --from-literal=MONGODB_PASSWORD=your_strong_password \
  --from-literal=JWT_SECRET_KEY=your_jwt_secret \
  --from-literal=OPENAI_API_KEY=sk-your-key \
  --from-literal=COHERE_API_KEY=your-cohere-key \
  -n default
```

### Step 2: Deploy Storage Layer

```bash
# Deploy StatefulSets (MongoDB, Redis, Qdrant)
kubectl apply -f k8s/base/mongodb-statefulset.yaml -n default
kubectl apply -f k8s/base/redis-statefulset.yaml -n default
kubectl apply -f k8s/base/qdrant-statefulset.yaml -n default

# Wait for StatefulSets to be ready
kubectl rollout status statefulset/mongodb -n default
kubectl rollout status statefulset/redis -n default
kubectl rollout status statefulset/qdrant -n default

# Initialize MongoDB replica set
kubectl apply -f k8s/base/mongodb-statefulset.yaml -n default
kubectl wait --for=condition=complete job/mongodb-init -n default --timeout=5m
```

### Step 3: Deploy Applications

```bash
# Deploy backend and frontend
kubectl apply -f k8s/base/backend-deployment.yaml -n default
kubectl apply -f k8s/base/frontend-deployment.yaml -n default

# Wait for deployments
kubectl rollout status deployment/lumenai-backend -n default
kubectl rollout status deployment/lumenai-frontend -n default
```

### Step 4: Configure Autoscaling

```bash
# Deploy HPA configurations
kubectl apply -f k8s/base/hpa.yaml -n default

# Verify HPA status
kubectl get hpa -n default
```

### Step 5: Setup Ingress & TLS

```bash
# Install cert-manager (if not already installed)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Deploy ingress configuration
kubectl apply -f k8s/base/ingress.yaml -n default

# Check certificate status
kubectl get certificate -n default
kubectl describe certificate lumenai-tls -n default
```

### Step 6: Deploy Monitoring

```bash
# Deploy Prometheus and Grafana
kubectl apply -f k8s/monitoring/prometheus.yaml -n monitoring
kubectl apply -f k8s/monitoring/grafana.yaml -n monitoring

# Wait for monitoring stack
kubectl rollout status deployment/prometheus -n monitoring
kubectl rollout status deployment/grafana -n monitoring
```

### Step 7: Initialize RAG System

```bash
# Port-forward to backend
kubectl port-forward deployment/lumenai-backend 8000:8000 -n default &

# Or exec into pod
kubectl exec -it deployment/lumenai-backend -n default -- bash

# Initialize RAG with sample data
python backend/scripts/init_rag.py --with-samples --test

# Check RAG stats
python backend/scripts/init_rag.py --stats
```

## ⚙️ Configuration

### Environment Variables

Edit `k8s/base/configmaps.yaml` to customize:

```yaml
# Backend Configuration
APP_NAME: "LumenAI"
LOG_LEVEL: "INFO"  # DEBUG, INFO, WARNING, ERROR
RATE_LIMIT_PER_MINUTE: "60"
LLM_MODEL: "gpt-4-turbo-preview"
RAG_TOP_K: "10"
EMBEDDING_MODEL: "text-embedding-3-large"
```

### Resource Limits

Adjust resources in deployment files:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### Storage Classes

Update storage class based on your provider:

```yaml
# Google Cloud
storageClassName: standard-rwo

# AWS
storageClassName: gp3

# Azure
storageClassName: managed-premium
```

## 📈 Scaling

### Horizontal Pod Autoscaling (HPA)

```bash
# View HPA status
kubectl get hpa -n default

# Manually scale (override HPA temporarily)
kubectl scale deployment lumenai-backend --replicas=10 -n default

# Adjust HPA parameters
kubectl edit hpa lumenai-backend-hpa -n default
```

### Vertical Pod Autoscaling (VPA)

```bash
# Install VPA (if not already installed)
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/download/vertical-pod-autoscaler-0.13.0/vertical-pod-autoscaler.yaml

# View VPA recommendations
kubectl describe vpa qdrant-vpa -n default
kubectl describe vpa redis-vpa -n default
```

### Cluster Autoscaling

<details>
<summary>GKE</summary>

```bash
gcloud container clusters update lumenai-cluster \
  --enable-autoscaling \
  --min-nodes=3 \
  --max-nodes=20 \
  --zone=us-central1-a
```
</details>

<details>
<summary>EKS</summary>

```bash
eksctl scale nodegroup --cluster=lumenai-cluster --nodes=10 --name=ng-1
```
</details>

## 📊 Monitoring

### Access Monitoring Tools

```bash
# Port-forward Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# Access: http://localhost:3000
# Default credentials: admin / CHANGE_ME_IN_PRODUCTION

# Port-forward Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n monitoring

# Access: http://localhost:9090
```

### Key Metrics to Monitor

- **Application Metrics**:
  - Request rate (requests/second)
  - Response time (p50, p95, p99)
  - Error rate (4xx, 5xx)
  - Active connections

- **Resource Metrics**:
  - CPU utilization
  - Memory utilization
  - Disk I/O
  - Network throughput

- **Database Metrics**:
  - MongoDB operations/sec
  - Redis hit rate
  - Qdrant vector count

### Alerting

Configure alerts in Prometheus:

```yaml
# Example alert rules in k8s/monitoring/prometheus.yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
```

## 🔍 Troubleshooting

### Common Issues

<details>
<summary>Pods not starting</summary>

```bash
# Check pod status
kubectl get pods -n default

# View pod events
kubectl describe pod <pod-name> -n default

# Check logs
kubectl logs <pod-name> -n default

# Check previous container logs (if crashed)
kubectl logs <pod-name> -n default --previous
```
</details>

<details>
<summary>StatefulSet pods stuck in Pending</summary>

```bash
# Check PVC status
kubectl get pvc -n default

# Check events
kubectl get events -n default --sort-by='.lastTimestamp'

# Check storage class
kubectl get storageclass

# Manual PVC creation if needed
kubectl apply -f pvc.yaml
```
</details>

<details>
<summary>Ingress not working</summary>

```bash
# Check ingress status
kubectl get ingress -n default
kubectl describe ingress lumenai-ingress -n default

# Check ingress controller
kubectl get pods -n ingress-nginx

# Check certificate
kubectl get certificate -n default
kubectl describe certificate lumenai-tls -n default

# View cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```
</details>

<details>
<summary>High memory/CPU usage</summary>

```bash
# Check resource usage
kubectl top pods -n default
kubectl top nodes

# View detailed metrics
kubectl describe node <node-name>

# Check HPA status
kubectl get hpa -n default

# Manually scale if needed
kubectl scale deployment lumenai-backend --replicas=5 -n default
```
</details>

### Debugging Commands

```bash
# Interactive shell in pod
kubectl exec -it deployment/lumenai-backend -n default -- /bin/bash

# Port-forward to service
kubectl port-forward svc/lumenai-backend 8000:8000 -n default

# View all resources
kubectl get all -n default

# View resource usage
kubectl top pods -n default
kubectl top nodes

# Check cluster events
kubectl get events -n default --sort-by='.lastTimestamp'
```

## 🔐 Production Best Practices

### Security

1. **Update all secrets** before production deployment
2. **Enable network policies** to restrict pod-to-pod communication
3. **Use RBAC** for fine-grained access control
4. **Enable pod security policies**
5. **Regular security scanning** of container images
6. **TLS everywhere** - enforce HTTPS

### High Availability

1. **Multi-zone deployment** - spread pods across availability zones
2. **Pod Disruption Budgets** - prevent too many pods down simultaneously
3. **Resource requests/limits** - ensure proper scheduling
4. **Health checks** - liveness and readiness probes
5. **Graceful shutdown** - proper termination handling

### Backup & Disaster Recovery

```bash
# Backup MongoDB
kubectl exec -it mongodb-0 -n default -- mongodump --out=/backup

# Backup Qdrant
kubectl exec -it qdrant-0 -n default -- tar czf /backup/qdrant.tar.gz /qdrant/storage

# Backup to cloud storage
# ... implement cloud-specific backup strategy
```

### Cost Optimization

1. **Right-size resources** - don't over-provision
2. **Use spot/preemptible instances** for non-critical workloads
3. **Enable cluster autoscaling** - scale down when idle
4. **Use storage tiers** - cold storage for backups
5. **Monitor costs** - set up billing alerts

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [LumenAI GitHub](https://github.com/Marksio90/LumenAI-Life-Intelligence-System)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/deployment/)
- [MongoDB on Kubernetes](https://www.mongodb.com/docs/kubernetes-operator/)

## 🆘 Support

For issues and questions:
- GitHub Issues: https://github.com/Marksio90/LumenAI-Life-Intelligence-System/issues
- Documentation: /docs
- Email: admin@lumenai.example.com

---

**Last Updated**: 2024-12-04
**Version**: 1.0.0
