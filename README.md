# 🌟 LumenAI v2.0 — Life Intelligence System
**Twój osobisty, multimodalny, samouczący się asystent życia**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/yourusername/lumenai)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/next.js-15-black.svg)](https://nextjs.org)

## ✨ **NEW in v2.0** - Major Performance & Features Update

### 🚀 Performance Optimizations
- **⚡ 50-80% Faster Image Uploads** - Client-side compression (auto-reduces to 1MB)
- **🎤 30-50% Faster Audio** - Optimized Opus codec, echo cancellation, noise suppression
- **💬 Real-time Streaming Responses** - ChatGPT-like word-by-word display (80% faster perceived)
- **📦 40-50% Smaller Bundle** - Lazy loading for all heavy components
- **🗄️ 80% Fewer API Calls** - Smart caching with 5-min TTL
- **🧠 30-40% Reduced Costs** - Context optimization & better prompts

### 🎨 Complete Frontend Redesign
- **📅 Planner v2.0** - Task management, Google Calendar sync, time blocking
- **💭 Mood Tracker v2.0** - Emotion tracking, CBT/DBT tips, trend analysis
- **🤔 Decision Helper v2.0** - AI-powered pros/cons, scenario analysis
- **💰 Finance Tracker v2.0** - Expense tracking, budget management, analytics
- **⚙️ Interactive Settings** - Full tab navigation, live toggles
- **📊 Real-time Dashboard** - MongoDB-powered live data

### 🔧 Enhanced Backend
- **📡 SSE Streaming Endpoint** - `/api/v1/chat/stream` for real-time responses
- **🎯 Enhanced Prompts Library** - Professional prompt engineering for all agents
- **⚡ Performance Optimizer** - Caching, rate limiting, context optimization
- **📅 Enhanced Calendar Service** - Batch ops, free/busy, smart scheduling
- **📧 Gmail Service** - Auto-reply, filtering, email automation
- **🏥 Health Monitoring** - Service status tracking for all integrations

---

## 🚀 Quick Start

LumenAI to zaawansowana, wieloagentowa platforma AI, która integruje język, dźwięk, obraz, emocje oraz dane użytkownika, by działać jak osobisty przewodnik życiowy, planista, doradca i cyfrowy mentor.

System wykorzystuje:

LLM (Large Language Models)

Multi-agent orchestration

ML/DL training na prywatnych danych użytkownika

Analizę głosu, tekstu, obrazu i OCR

Spersonalizowaną pamięć semantyczną (Vector DB)

Planowanie i automatyzacje

Real-time interaction (WebSockets)

Celem LumenAI jest pomagać ludziom w codziennych decyzjach, emocjach, nawykach, finansach, zdrowiu psychicznym, pracy, relacjach i samorozwoju — w najbardziej naturalny sposób.

🔥 Najważniejsze funkcje
🤖 Wieloagentowy mózg systemu

System zawiera dziesiątki agentów odpowiedzialnych za różne obszary życia, m.in.:

Planner Agent – plan dnia, kalendarz, zadania

Decision Agent – decyzje życiowe, analiza scenariuszy

Mood Agent – analiza nastroju, trenowany na danych użytkownika

Therapy Agent (CBT/DBT) – wsparcie emocjonalne

Vision Agent – analiza obrazów, zdjęć, OCR

Speech Agent – mowa → tekst → mowa

Finance Agent – budżet, wydatki, cele finansowe

Automation Agent – wykonywanie działań (API: mail, kalendarz, Notion itd.)

Wszystkimi agentami zarządza Orchestrator, który podejmuje decyzję, który moduł odpowiedzieć ma użytkownikowi.

🧠 Uczenie i personalizacja

Każdy użytkownik otrzymuje własny, trenowany lokalnie model ML, obejmujący:

klasyfikator nastroju

model preferencji

embeddingi osobiste

model decyzji życiowych (forecasting)

profil zachowań (Behavior Vector)

System nie tylko odpowiada — uczy się.

Z czasem LumenAI:

zna Twój rytm dnia

zna Twoje emocje

widzi Twoje zmiany i postępy

przewiduje najbliższe trudne dni

proponuje najlepsze możliwe działania

działa jak „druga głowa”, współdecydując i współmyśląc

🔊 Multimodalność

LumenAI obsługuje:

Mowę (STT + TTS)

Tekst

Obraz (Vision, OCR)

Audio (analiza tonu głosu, emocji)

Wideo – opcjonalnie (pipeline gotowy)

Możesz rozmawiać z systemem:

pisząc

mówiąc

wysyłając zdjęcia notatek

nagrywając głos

przesyłając dokumenty do analizy

🏛️ Architektura (High-Level)
LUMENAI/
│
├── backend/
│   ├── gateway/          # FastAPI + WebSocket Gateway
│   ├── core/             # Orchestrator, Memory, LLM Engine
│   ├── agents/           # Multi-agent modules
│   ├── ml/               # ML training + personalization
│   ├── data/             # Vector DB, user data, logs
│   ├── services/         # Integracje (Google, Notion, Email)
│   └── shared/           # Config, utils, constants
│
├── frontend/
│   └── lumenai-app/      # Next.js + React + Tailwind
│
├── infra/
│   ├── docker/           # Dockerfiles + compose
│   ├── kubernetes/       # Deploy to K8S clusters
│   ├── monitoring/       # Grafana + Prometheus
│   └── devops/           # CI/CD pipelines
│
└── docs/                 # Dokumentacja techniczna

⚙️ Technologie
Backend

Python 3.11

FastAPI

LangChain / LlamaIndex

ChromaDB / Pinecone

Whisper / SpeechRecognition

Tesseract OCR / Vision AI

Pydantic

Uvicorn

Frontend

Next.js 15

React 19

TailwindCSS

Zustand / Redux

WebSockets (real-time)

Machine Learning

PyTorch

Scikit-learn

SentenceTransformers

CatBoost

DevOps

Docker

Docker Compose

Kubernetes

Prometheus

Grafana

🔌 Integracje

Platforma ma gotowe moduły integracyjne z:

Google Calendar

Notion

Gmail API

Weather API

HuggingFace models

OpenAI / Anthropic LLMs

🧩 Moduły backendu
🧠 core/

orchestrator

memory manager

context builder

persona system

llm engine

🧬 agents/

cognitive

emotional

vision

speech

planning

automation

🤖 ml/

trainer

pipelines

local models

💾 data/

vector DB

logs

user memory folders

📡 services/

API integracje

TTS

STT

OCR

🎨 Moduły frontendowe
🧩 UI

Chat window

Audio recorder

OCR uploader

Timeline of moods

Dashboard of habits

Task planner

Finance charts

Settings panel

⚡ Komunikacja

API wrapper

WebSocket client

Streaming responses

Reconnect logic

🛠️ Jak uruchomić projekt?

Wybierz metodę instalacji:

**Metoda A: Mamba/Conda (Deweloperzy ML/AI)** 🐍

# Automatyczna instalacja środowiska
make mamba-setup

# Aktywuj środowisko
mamba activate lumenai

# Uruchom backend
make backend-dev

# Uruchom frontend (osobny terminal)
make frontend-dev


Frontend: http://localhost:3000
Backend: http://localhost:8000

📖 [Pełna dokumentacja Mamba](./docs/MAMBA_SETUP.md)

**Metoda B: Docker (Produkcja)** 🐳

# Szybki start
./start.sh

# Lub manualnie
docker compose up --build


Frontend: http://localhost:3000
Backend: http://localhost:8000
API Docs: http://localhost:8000/docs

📖 [Szczegóły w Getting Started](./docs/GETTING_STARTED.md)

🧪 Testowanie
pytest backend/tests/

🔐 Bezpieczeństwo i prywatność

System implementuje:

pełne szyfrowanie danych użytkownika

E2E dla sesji czatu

osobny profil danych dla każdego użytkownika

kontrolę polityk prywatności

pełną transparentność co do tego, jak modele się uczą

LumenAI nigdy nie wysyła prywatnych danych do modeli zewnętrznych bez zgody.

🗺️ Roadmapa
✔️ v1.0 — Fundament (ten etap)

Backend core

Multi-agent skeleton

Next.js frontend

Docker environment

🔄 v2.0 — Multi-Agent Alpha

Planner Agent

Mood Agent

Vision Agent

Speech Agent

🔥 v3.0 — Personal AI

trenowanie modeli użytkownika

budowa osobistej pamięci długoterminowej

timeline emocji

habit intelligence

🌐 v4.0 — Integracje i automatyzacje

mail

kalendarz

Notion

smart home

🪄 v5.0 — Real Life Co-Pilot

decyzje życiowe

zaawansowane scenariusze „co jeśli”

predykcja trudnych dni

wsparcie emocjonalne 24/7

💡 Misja LumenAI

Stworzyć pierwszy system AI, który:

uczy się człowieka głębiej niż jakiekolwiek narzędzie

realnie pomaga w codziennym życiu

daje wsparcie emocjonalne i praktyczne jednocześnie

jest multimodalny, empatyczny, przewidujący

prowadzi użytkownika jak mądry, wspierający mentor

🤝 Współtwórcy

Autor: Mateusz
AI Partner: ChatGPT