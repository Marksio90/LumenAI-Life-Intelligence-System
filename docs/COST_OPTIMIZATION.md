# 💰 LumenAI - Cost Optimization Guide

## Problem: High LLM Costs

LumenAI był domyślnie skonfigurowany z `gpt-4-turbo-preview` - **najdroższym** dostępnym modelem!

**Koszt przed optymalizacją:**
- 1 zapytanie = **$0.02-0.03** 😱
- 100 zapytań dziennie = **$60-90/miesiąc** 💸
- 1000 zapytań dziennie = **$600-900/miesiąc** 🔥

## Rozwiązanie: Smart Cost Optimization

LumenAI v1.1 wprowadza **inteligentne zarządzanie kosztami** z 75x oszczędnościami!

### 🎯 Nowe Funkcje

1. **Smart Model Routing** - Automatyczny wybór najtańszego modelu do zadania
2. **Response Caching** - Cache odpowiedzi, zero duplikatów API
3. **Cost Tracking** - Real-time monitoring kosztów
4. **Token Limits** - Kontrola długości odpowiedzi
5. **Tańsze domyślne modele** - gpt-4o-mini zamiast gpt-4-turbo

### 📊 Porównanie Modeli

| Model | Input ($/1M) | Output ($/1M) | Typowy koszt* | Use Case |
|-------|--------------|---------------|---------------|----------|
| **gpt-4o-mini** ✅ | $0.15 | $0.60 | **$0.0004** | DEFAULT - 99% zadań |
| gpt-3.5-turbo | $0.50 | $1.50 | $0.0010 | FAST - proste zapytania |
| gpt-4o | $2.50 | $10.00 | $0.0063 | SMART - complex reasoning |
| ~~gpt-4-turbo~~ ❌ | $10.00 | $30.00 | **$0.0200** | NIE UŻYWAJ! |

*Zakładając ~500 input + 500 output tokenów

### 💡 Smart Routing

System automatycznie wybiera model na podstawie złożoności:

```python
# Proste pytanie → gpt-4o-mini ($0.0004)
"Co to jest Python?"

# Średnie → gpt-4o-mini ($0.0004)
"Napisz funkcję sortującą"

# Złożone → gpt-4o ($0.0063)
"Zaprojektuj architekturę systemu ML z analizą trade-offów..."
```

**Oszczędności: 75x dla prostych zapytań!**

## 🚀 Quick Start

### 1. Zaktualizuj .env

```bash
# Nowe ustawienia (już w .env.example)
DEFAULT_MODEL=gpt-4o-mini        # 75x tańszy!
SMART_MODEL=gpt-4o               # Dla złożonych zadań
FAST_MODEL=gpt-3.5-turbo         # Ultra szybki

ENABLE_SMART_ROUTING=true        # Włącz auto-routing
ENABLE_RESPONSE_CACHE=true       # Włącz caching
MAX_TOKENS_DEFAULT=1000          # Limit tokenów
```

### 2. Restart Backend

```bash
# Docker
docker-compose restart backend

# Mamba
mamba activate lumenai
make backend-dev
```

### 3. Gotowe! 🎉

System automatycznie:
- ✅ Wybiera tańsze modele
- ✅ Cache'uje odpowiedzi
- ✅ Limituje tokeny
- ✅ Loguje koszty

## 📈 Monitoring Kosztów

### API Endpoint

```bash
curl http://localhost:8000/api/v1/stats/costs
```

**Odpowiedź:**
```json
{
  "status": "success",
  "data": {
    "total_cost": 0.1234,
    "total_requests": 250,
    "average_cost_per_request": 0.0005,
    "total_tokens": 125000,
    "estimated_monthly_cost": 15.00,
    "model_breakdown": {
      "gpt-4o-mini": {
        "requests": 200,
        "cost": 0.08,
        "input_tokens": 50000,
        "output_tokens": 50000
      },
      "gpt-4o": {
        "requests": 50,
        "cost": 0.0434,
        "input_tokens": 12500,
        "output_tokens": 12500
      }
    }
  },
  "message": "💰 Total cost: $0.1234"
}
```

### Logi Real-time

W logach backendu:
```
💰 LLM Cost: $0.000375 | Model: gpt-4o-mini | Tokens: 500→500 | Total: $0.1234
```

## 🎛️ Konfiguracja

### Per-Agent Models

Możesz wymusić konkretny model dla agenta:

```python
# backend/core/model_router.py

agent_models = {
    "planner": "default",       # gpt-4o-mini - wystarczy
    "mood": "default",          # gpt-4o-mini - jakość OK
    "decision": "smart",        # gpt-4o - potrzebuje reasoning
    "vision": "smart",          # gpt-4o - analiza obrazów
}
```

### Manual Override

Wymuś konkretny model w kodzie:

```python
response = await llm_engine.generate(
    prompt="...",
    force_model="gpt-4o"  # Wymuś droższy model
)
```

### Disable Smart Routing

```bash
# .env
ENABLE_SMART_ROUTING=false
DEFAULT_MODEL=gpt-4o-mini  # Zawsze ten sam
```

## 💾 Response Caching

Cache działa automatycznie dla identycznych zapytań:

```python
# Pierwsze zapytanie - API call ($0.0004)
"Jaka jest stolica Polski?"

# Drugie zapytanie (w ciągu 1h) - z cache ($0.00!)
"Jaka jest stolica Polski?"
```

**Ustawienia:**
```bash
ENABLE_RESPONSE_CACHE=true
CACHE_TTL_SECONDS=3600  # 1 godzina
```

## 📉 Oszczędności w Liczbach

### Przykład: 100 zapytań/dzień

**PRZED optymalizacją** (gpt-4-turbo):
- Dziennie: $2-3
- Miesięcznie: **$60-90**
- Rocznie: **$720-1080**

**PO optymalizacji** (smart routing):
- Dziennie: $0.04-0.06 (95% gpt-4o-mini, 5% gpt-4o)
- Miesięcznie: **$1.20-1.80**
- Rocznie: **$14.40-21.60**

**OSZCZĘDNOŚCI: ~97% ($840/rok!)** 🎉

### Z Cachingiem (+50% hit rate):

- Miesięcznie: **$0.60-0.90**
- Rocznie: **$7.20-10.80**

**OSZCZĘDNOŚCI: ~99% ($990/rok!)** 🚀

## 🔧 Zaawansowane

### Custom Cost Limits

Dodaj daily cost limit:

```python
# backend/core/cost_tracker.py

DAILY_COST_LIMIT = 1.00  # $1/day

if cost_tracker.total_cost > DAILY_COST_LIMIT:
    raise Exception("Daily cost limit exceeded!")
```

### Cost Alerts

Email alert gdy koszt przekroczy threshold:

```python
from backend.core.cost_tracker import cost_tracker

if cost_tracker.total_cost > 10.00:
    send_email_alert(f"Cost exceeded $10: ${cost_tracker.total_cost}")
```

### Per-User Tracking

```python
# Rozszerz cost_tracker.py
cost_tracker.track_request(
    model="gpt-4o-mini",
    input_tokens=500,
    output_tokens=500,
    user_id="user123"  # Track per user
)
```

## 🎓 Best Practices

1. **Używaj gpt-4o-mini jako default** - wystarczy dla 95% zadań
2. **Włącz Smart Routing** - oszczędza bez straty jakości
3. **Włącz Caching** - zero-cost dla powtórzeń
4. **Monitoruj koszty** - sprawdzaj /api/v1/stats/costs
5. **Limituj tokeny** - MAX_TOKENS_DEFAULT=1000
6. **Testuj z mockami** - development bez API
7. **Review model selection** - czy decision agent naprawdę potrzebuje gpt-4o?

## 🐛 Troubleshooting

### Koszty nadal wysokie?

```bash
# Sprawdź statystyki
curl http://localhost:8000/api/v1/stats/costs

# Zobacz który model jest używany
# Logi: "Model: gpt-4o-mini" = GOOD ✅
# Logi: "Model: gpt-4-turbo" = BAD ❌
```

### Smart routing nie działa?

```bash
# Sprawdź .env
grep ENABLE_SMART_ROUTING .env

# Powinno być:
ENABLE_SMART_ROUTING=true
```

### Cache nie działa?

```bash
# Sprawdź logi - powinny być "Cache HIT!"
# Jeśli nie ma:

grep ENABLE_RESPONSE_CACHE .env
# Powinno być:
ENABLE_RESPONSE_CACHE=true
```

## 📊 ROI Calculator

Oszacuj swoje oszczędności:

```
Aktualne zapytania/dzień: _______
Średni koszt przed: $0.025
Średni koszt po: $0.0005

Miesięczne oszczędności:
  (zapytania × 30 × $0.0245) = $_______

Roczne oszczędności:
  (miesięczne × 12) = $_______
```

## 🎯 Roadmap

- [ ] Redis-based distributed caching
- [ ] Per-user cost limits
- [ ] Cost prediction model
- [ ] Auto-scaling based on budget
- [ ] Model performance tracking
- [ ] A/B testing model selection
- [ ] Cost anomaly detection

---

**Zredukowaliśmy koszty o 97%!** 💰✨

Pytania? Zobacz [GitHub Issues](https://github.com/Marksio90/LumenAI-Life-Intelligence-System/issues)
