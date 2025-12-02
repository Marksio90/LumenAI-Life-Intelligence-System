# LumenAI Makefile - Quick commands for development

.PHONY: help install dev build up down logs clean test mamba-setup mamba-install mamba-activate

help:
	@echo "LumenAI - Available commands:"
	@echo ""
	@echo "🐍 Mamba/Conda Environment:"
	@echo "  make mamba-setup     - Auto-install Mamba and create environment"
	@echo "  make mamba-install   - Create Mamba environment from environment.yml"
	@echo "  make mamba-minimal   - Create minimal Mamba environment"
	@echo "  make mamba-update    - Update existing Mamba environment"
	@echo "  make mamba-clean     - Remove Mamba environment"
	@echo ""
	@echo "🐳 Docker Commands:"
	@echo "  make install         - Install all dependencies (pip + npm)"
	@echo "  make dev             - Run development environment (Docker)"
	@echo "  make build           - Build Docker containers"
	@echo "  make up              - Start all services (Docker)"
	@echo "  make down            - Stop all services"
	@echo "  make logs            - View logs"
	@echo ""
	@echo "🧪 Development:"
	@echo "  make backend-dev     - Run backend locally (needs Mamba env)"
	@echo "  make frontend-dev    - Run frontend locally (needs npm)"
	@echo "  make test            - Run tests"
	@echo "  make clean           - Clean up everything"

install:
	@echo "Installing backend dependencies..."
	pip install -r backend/requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend/lumenai-app && npm install
	@echo "✅ Installation complete!"

dev:
	@echo "Starting development environment..."
	docker-compose up --build

build:
	@echo "Building Docker containers..."
	docker-compose build

up:
	@echo "Starting services..."
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"
	@echo "   API Docs: http://localhost:8000/docs"

down:
	@echo "Stopping services..."
	docker-compose down
	@echo "✅ Services stopped!"

logs:
	docker-compose logs -f

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	rm -rf backend/__pycache__
	rm -rf backend/*/__pycache__
	rm -rf backend/*/*/__pycache__
	rm -rf frontend/lumenai-app/.next
	rm -rf frontend/lumenai-app/node_modules
	@echo "✅ Cleanup complete!"

test:
	@echo "Running tests..."
	pytest backend/tests/
	@echo "✅ Tests complete!"

backend-dev:
	@echo "Starting backend in development mode..."
	cd backend && uvicorn gateway.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	@echo "Starting frontend in development mode..."
	cd frontend/lumenai-app && npm run dev

# Mamba/Conda commands
mamba-setup:
	@echo "🐍 Setting up Mamba environment..."
	@chmod +x setup_mamba.sh
	@./setup_mamba.sh

mamba-install:
	@echo "Creating Mamba environment (full)..."
	@if command -v mamba >/dev/null 2>&1; then \
		mamba env create -f environment.yml; \
	else \
		echo "❌ Mamba not found. Run 'make mamba-setup' first."; \
		exit 1; \
	fi
	@echo "✅ Environment created! Activate with: mamba activate lumenai"

mamba-minimal:
	@echo "Creating minimal Mamba environment..."
	@if command -v mamba >/dev/null 2>&1; then \
		mamba env create -f environment-minimal.yml; \
	else \
		echo "❌ Mamba not found. Run 'make mamba-setup' first."; \
		exit 1; \
	fi
	@echo "✅ Environment created! Activate with: mamba activate lumenai-minimal"

mamba-update:
	@echo "Updating Mamba environment..."
	@if command -v mamba >/dev/null 2>&1; then \
		mamba env update -f environment.yml --prune; \
	else \
		echo "❌ Mamba not found. Run 'make mamba-setup' first."; \
		exit 1; \
	fi

mamba-clean:
	@echo "Removing Mamba environment..."
	@if command -v mamba >/dev/null 2>&1; then \
		mamba env remove -n lumenai -y; \
		mamba env remove -n lumenai-minimal -y; \
	else \
		echo "❌ Mamba not found."; \
	fi
	@echo "✅ Mamba environments removed!"

mamba-list:
	@echo "Available Mamba/Conda environments:"
	@if command -v mamba >/dev/null 2>&1; then \
		mamba env list; \
	else \
		echo "❌ Mamba not found. Run 'make mamba-setup' first."; \
	fi
