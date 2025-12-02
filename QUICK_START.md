# ⚡ LumenAI - Quick Start Guide

Najprostszy sposób na uruchomienie LumenAI w 5 minut!

## 🐍 Dla Data Scientists / ML Developers

**Jeśli wolisz Pythona i chcesz eksperymentować z ML:**

```bash
# 1. Sklonuj repo
git clone <repo-url>
cd LumenAI-Life-Intelligence-System

# 2. Automatyczna instalacja Mamba + środowisko
make mamba-setup

# 3. Dodaj API key
cp .env.example .env
# Edytuj .env i dodaj OPENAI_API_KEY lub ANTHROPIC_API_KEY

# 4. Uruchom (w 2 terminalach)
mamba activate lumenai
make backend-dev

# W drugim terminalu:
make frontend-dev
```

**Gotowe! → http://localhost:3000** 🎉

---

## 🐳 Dla Wszystkich Innych

**Najłatwiejszy sposób - Docker (zero konfiguracji):**

```bash
# 1. Sklonuj repo
git clone <repo-url>
cd LumenAI-Life-Intelligence-System

# 2. Uruchom setup script
./start.sh

# Lub manualnie:
cp .env.example .env
# Dodaj API keys do .env
docker-compose up --build
```

**Gotowe! → http://localhost:3000** 🎉

---

## 📋 Checklist

- [ ] Git zainstalowany
- [ ] Python 3.11+ LUB Docker
- [ ] Node.js 20+ (dla frontend dev)
- [ ] API key (OpenAI lub Anthropic)
- [ ] 5-10 GB wolnego miejsca

## 🆘 Problemy?

**Backend nie startuje:**
```bash
# Sprawdź logi
docker-compose logs backend
# Lub jeśli Mamba:
mamba activate lumenai && cd backend && python gateway/main.py
```

**Frontend nie łączy się:**
- Sprawdź czy backend działa: http://localhost:8000/health
- Sprawdź .env czy NEXT_PUBLIC_API_URL jest poprawny

**Mamba nie działa:**
```bash
# Reinstall
make mamba-setup
```

## 📚 Co dalej?

1. **Eksperymentuj** - Wypróbuj różne pytania do agentów
2. **Czytaj docs** - [GETTING_STARTED.md](./docs/GETTING_STARTED.md)
3. **Rozwijaj** - Dodaj własnego agenta
4. **Deploy** - [DEPLOYMENT.md](./docs/DEPLOYMENT.md)

---

**Więcej info:**
- 📖 [Full Documentation](./docs/)
- 🐍 [Mamba Setup](./docs/MAMBA_SETUP.md)
- 🏗️ [Architecture](./docs/ARCHITECTURE.md)

Miłego kodowania z LumenAI! 🌟
