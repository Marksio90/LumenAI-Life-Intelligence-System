# LumenAI Makefile - Quick commands for development

.PHONY: help install dev build up down logs clean test

help:
	@echo "LumenAI - Available commands:"
	@echo "  make install    - Install all dependencies"
	@echo "  make dev        - Run development environment"
	@echo "  make build      - Build Docker containers"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs"
	@echo "  make clean      - Clean up everything"
	@echo "  make test       - Run tests"

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
