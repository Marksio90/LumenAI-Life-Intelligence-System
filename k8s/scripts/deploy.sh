#!/bin/bash
###############################################################################
# LumenAI Platform Deployment Script
#
# This script deploys the entire LumenAI platform to Kubernetes
# Supports: development, staging, production environments
#
# Usage:
#   ./deploy.sh [environment] [options]
#
# Examples:
#   ./deploy.sh development
#   ./deploy.sh production --dry-run
#   ./deploy.sh staging --skip-monitoring
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-development}"
DRY_RUN="${2:-}"
SKIP_MONITORING="${3:-}"

NAMESPACE="default"
MONITORING_NAMESPACE="monitoring"
K8S_DIR="../base"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     LumenAI Platform Deployment Script v1.0.0         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi

    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi

    # Check helm (optional but recommended)
    if ! command -v helm &> /dev/null; then
        log_warn "Helm is not installed. Some features may not be available."
    fi

    log_info "Prerequisites check passed ✓"
}

create_namespaces() {
    log_info "Creating namespaces..."

    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

    if [[ "${SKIP_MONITORING}" != "--skip-monitoring" ]]; then
        kubectl create namespace ${MONITORING_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    fi

    log_info "Namespaces created ✓"
}

deploy_secrets() {
    log_info "Deploying secrets and configmaps..."

    if [[ "${DRY_RUN}" == "--dry-run" ]]; then
        kubectl apply -f ${K8S_DIR}/configmaps.yaml --dry-run=client
    else
        kubectl apply -f ${K8S_DIR}/configmaps.yaml -n ${NAMESPACE}
    fi

    log_warn "⚠️  Remember to update secrets with production values!"
    log_info "Secrets deployed ✓"
}

deploy_storage() {
    log_info "Deploying StatefulSets (MongoDB, Redis, Qdrant)..."

    local components=("mongodb-statefulset.yaml" "redis-statefulset.yaml" "qdrant-statefulset.yaml")

    for component in "${components[@]}"; do
        if [[ "${DRY_RUN}" == "--dry-run" ]]; then
            kubectl apply -f ${K8S_DIR}/${component} --dry-run=client
        else
            kubectl apply -f ${K8S_DIR}/${component} -n ${NAMESPACE}
        fi
    done

    log_info "StatefulSets deployed ✓"
}

deploy_applications() {
    log_info "Deploying applications (Backend, Frontend)..."

    local apps=("backend-deployment.yaml" "frontend-deployment.yaml")

    for app in "${apps[@]}"; do
        if [[ "${DRY_RUN}" == "--dry-run" ]]; then
            kubectl apply -f ${K8S_DIR}/${app} --dry-run=client
        else
            kubectl apply -f ${K8S_DIR}/${app} -n ${NAMESPACE}
        fi
    done

    log_info "Applications deployed ✓"
}

deploy_autoscaling() {
    log_info "Deploying autoscaling configurations..."

    if [[ "${DRY_RUN}" == "--dry-run" ]]; then
        kubectl apply -f ${K8S_DIR}/hpa.yaml --dry-run=client
    else
        kubectl apply -f ${K8S_DIR}/hpa.yaml -n ${NAMESPACE}
    fi

    log_info "Autoscaling configured ✓"
}

deploy_ingress() {
    log_info "Deploying ingress configuration..."

    if [[ "${DRY_RUN}" == "--dry-run" ]]; then
        kubectl apply -f ${K8S_DIR}/ingress.yaml --dry-run=client
    else
        kubectl apply -f ${K8S_DIR}/ingress.yaml -n ${NAMESPACE}
    fi

    log_info "Ingress deployed ✓"
}

deploy_monitoring() {
    if [[ "${SKIP_MONITORING}" == "--skip-monitoring" ]]; then
        log_info "Skipping monitoring stack deployment"
        return
    fi

    log_info "Deploying monitoring stack (Prometheus, Grafana)..."

    if [[ "${DRY_RUN}" == "--dry-run" ]]; then
        kubectl apply -f ../monitoring/prometheus.yaml --dry-run=client
        kubectl apply -f ../monitoring/grafana.yaml --dry-run=client
    else
        kubectl apply -f ../monitoring/prometheus.yaml -n ${MONITORING_NAMESPACE}
        kubectl apply -f ../monitoring/grafana.yaml -n ${MONITORING_NAMESPACE}
    fi

    log_info "Monitoring stack deployed ✓"
}

wait_for_deployments() {
    log_info "Waiting for deployments to be ready..."

    local deployments=("lumenai-backend" "lumenai-frontend")

    for deployment in "${deployments[@]}"; do
        if [[ "${DRY_RUN}" != "--dry-run" ]]; then
            kubectl rollout status deployment/${deployment} -n ${NAMESPACE} --timeout=5m || {
                log_error "Deployment ${deployment} failed to become ready"
                exit 1
            }
        fi
    done

    log_info "All deployments ready ✓"
}

wait_for_statefulsets() {
    log_info "Waiting for StatefulSets to be ready..."

    local statefulsets=("mongodb" "redis" "qdrant")

    for statefulset in "${statefulsets[@]}"; do
        if [[ "${DRY_RUN}" != "--dry-run" ]]; then
            kubectl rollout status statefulset/${statefulset} -n ${NAMESPACE} --timeout=10m || {
                log_error "StatefulSet ${statefulset} failed to become ready"
                exit 1
            }
        fi
    done

    log_info "All StatefulSets ready ✓"
}

initialize_mongodb() {
    log_info "Initializing MongoDB replica set..."

    if [[ "${DRY_RUN}" != "--dry-run" ]]; then
        kubectl apply -f ${K8S_DIR}/mongodb-statefulset.yaml -n ${NAMESPACE}

        # Wait for job completion
        kubectl wait --for=condition=complete job/mongodb-init -n ${NAMESPACE} --timeout=5m || {
            log_warn "MongoDB initialization job may have failed. Check logs: kubectl logs job/mongodb-init -n ${NAMESPACE}"
        }
    fi

    log_info "MongoDB initialized ✓"
}

show_status() {
    log_info "Deployment Status:"
    echo ""

    if [[ "${DRY_RUN}" != "--dry-run" ]]; then
        echo "📊 Pods:"
        kubectl get pods -n ${NAMESPACE} -o wide
        echo ""

        echo "📡 Services:"
        kubectl get services -n ${NAMESPACE}
        echo ""

        echo "🔀 Ingress:"
        kubectl get ingress -n ${NAMESPACE}
        echo ""

        if [[ "${SKIP_MONITORING}" != "--skip-monitoring" ]]; then
            echo "📈 Monitoring:"
            kubectl get pods -n ${MONITORING_NAMESPACE}
        fi
    fi

    echo ""
    log_info "Deployment completed successfully! 🎉"
}

show_access_info() {
    log_info "Access Information:"
    echo ""

    if [[ "${DRY_RUN}" != "--dry-run" ]]; then
        local ingress_ip=$(kubectl get ingress lumenai-ingress -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending...")

        echo "🌐 Frontend: https://lumenai.example.com"
        echo "🔌 Backend API: https://api.lumenai.example.com"
        echo "📊 Grafana: https://grafana.lumenai.example.com (admin / CHANGE_ME)"
        echo "📈 Prometheus: http://prometheus.${MONITORING_NAMESPACE}.svc.cluster.local:9090"
        echo ""
        echo "⚠️  Make sure to update your DNS records to point to: ${ingress_ip}"
    fi
}

# Main deployment flow
main() {
    log_info "Starting deployment for environment: ${ENVIRONMENT}"
    echo ""

    check_prerequisites
    create_namespaces
    deploy_secrets
    deploy_storage
    wait_for_statefulsets
    initialize_mongodb
    deploy_applications
    deploy_autoscaling
    deploy_ingress
    deploy_monitoring
    wait_for_deployments
    show_status
    show_access_info

    echo ""
    log_info "🚀 LumenAI Platform deployment complete!"
    log_warn "📝 Next steps:"
    echo "   1. Update secrets with production values: kubectl edit secret lumenai-backend-secrets -n ${NAMESPACE}"
    echo "   2. Update DNS records to point to your ingress IP"
    echo "   3. Initialize RAG system: kubectl exec -it deployment/lumenai-backend -n ${NAMESPACE} -- python backend/scripts/init_rag.py --with-samples"
    echo "   4. Monitor logs: kubectl logs -f deployment/lumenai-backend -n ${NAMESPACE}"
}

# Run main
main
