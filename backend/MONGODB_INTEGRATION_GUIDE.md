# 🎉 MongoDB Integration - Gotowe do użycia!

## ✅ Co zostało zaimplementowane

### 1. **Schemat Bazy Danych** (`DATABASE_SCHEMA.md`)
- 📦 5 kolekcji: users, conversations, messages, mood_entries, user_context
- 🗺️ Pełna dokumentacja struktury danych
- 📋 Przykłady zapytań

### 2. **Modele Pydantic** (`models/database.py`)
- ✅ User - Profile użytkowników
- ✅ Conversation - Sesje rozmów
- ✅ Message - Wiadomości (user + assistant)
- ✅ MoodEntry - Wpisy nastrojów
- ✅ UserContext - Długoterminowy kontekst
- ✅ Automatyczna walidacja danych
- ✅ Konwersje JSON

### 3. **MongoDB Service Layer** (`services/mongodb_service.py`)
- 📝 **35+ metod** do obsługi bazy danych
- 🔍 Indeksy dla szybkiego wyszukiwania
- ⚡ Async/await dla wydajności
- 🛡️ Bezpieczne operacje CRUD
- 📊 Statystyki bazy danych

### 4. **Memory Manager Updated** (`core/memory.py`)
- 💾 **Pełna persystencja** - dane nie giną po restarcie!
- 🔄 Automatyczne tworzenie użytkowników i rozmów
- 📝 Zapis każdej wiadomości do MongoDB
- 😊 Zapis wpisów nastrojów
- 📊 Statystyki nastrojów z MongoDB

### 5. **Agenty Zaktualizowane**
- ✅ PlannerAgent - otrzymuje memory_manager
- ✅ DecisionAgent - otrzymuje memory_manager
- ✅ **MoodAgent - ZAPISUJE NASTROJE DO MONGODB!** 🎯
  - `track_mood()` - zapisuje wpisy nastrojów
  - `get_mood_insights()` - prawdziwe statystyki z bazy

### 6. **Nowe API Endpoints** (`gateway/main.py`)
- 📝 `GET /api/v1/user/{user_id}/conversations` - Lista rozmów
- 💬 `GET /api/v1/conversation/{conversation_id}/messages` - Wiadomości z rozmowy
- 😊 `GET /api/v1/user/{user_id}/mood/history` - Historia nastrojów
- 📊 `GET /api/v1/user/{user_id}/mood/stats` - Statystyki nastrojów
- 🏥 `GET /api/v1/db/health` - Status połączenia z MongoDB

---

## 🚀 Jak Uruchomić i Przetestować

### Krok 1: Uruchom Docker Compose

```bash
cd /home/user/LumenAI-Life-Intelligence-System
docker-compose up -d
```

To uruchomi:
- ✅ MongoDB na porcie 27017
- ✅ Redis
- ✅ ChromaDB
- ✅ Backend (FastAPI)
- ✅ Frontend (Next.js)

### Krok 2: Sprawdź czy MongoDB działa

```bash
# Sprawdź status kontenerów
docker-compose ps

# Sprawdź logi MongoDB
docker-compose logs mongo

# Test połączenia z MongoDB
docker exec -it lumenai-mongo mongosh --eval "db.runCommand({ping: 1})"
```

**Oczekiwany wynik:**
```json
{ "ok": 1 }
```

### Krok 3: Sprawdź zdrowotność API

```bash
# Health check głównego API
curl http://localhost:8000/health

# Health check MongoDB
curl http://localhost:8000/api/v1/db/health
```

**Oczekiwany wynik (`/api/v1/db/health`):**
```json
{
  "status": "healthy",
  "database": "lumenai",
  "collections": 5,
  "total_documents": 0
}
```

### Krok 4: Przetestuj integrację przez czat

1. **Otwórz frontend:** http://localhost:3000

2. **Wyślij pierwszą wiadomość:**
   ```
   Cześć! Jak się masz?
   ```

3. **Sprawdź czy zapisało się w bazie:**
   ```bash
   # Sprawdź czy użytkownik został utworzony
   docker exec -it lumenai-mongo mongosh lumenai --eval "db.users.find().pretty()"

   # Sprawdź rozmowy
   docker exec -it lumenai-mongo mongosh lumenai --eval "db.conversations.find().pretty()"

   # Sprawdź wiadomości
   docker exec -it lumenai-mongo mongosh lumenai --eval "db.messages.find().pretty()"
   ```

### Krok 5: Przetestuj śledzenie nastrojów

1. **Wyślij wiadomość o emocjach:**
   ```
   Czuję się dziś trochę smutny i zmęczony
   ```

2. **Mood Agent powinien odpowiedzieć z empatią**

3. **Sprawdź wpisy nastrojów:**
   ```bash
   docker exec -it lumenai-mongo mongosh lumenai --eval "db.mood_entries.find().pretty()"
   ```

4. **Pobierz statystyki przez API:**
   ```bash
   curl "http://localhost:8000/api/v1/user/user_123/mood/stats?days=7"
   ```

---

## 🧪 Testy API z cURL

### Test 1: Pobierz rozmowy użytkownika
```bash
curl http://localhost:8000/api/v1/user/user_123/conversations
```

### Test 2: Pobierz wiadomości z rozmowy
```bash
# Najpierw pobierz conversation_id z powyższego zapytania
curl http://localhost:8000/api/v1/conversation/{conversation_id}/messages
```

### Test 3: Historia nastrojów
```bash
curl "http://localhost:8000/api/v1/user/user_123/mood/history?days=7"
```

### Test 4: Statystyki nastrojów
```bash
curl "http://localhost:8000/api/v1/user/user_123/mood/stats?days=30"
```

### Test 5: Historyczna metoda (stara, ale powinna działać)
```bash
curl "http://localhost:8000/api/v1/user/user_123/history?limit=10"
```

---

## 🔍 Debugowanie

### Problem: MongoDB nie łączy się

```bash
# Sprawdź logi backendu
docker-compose logs backend

# Sprawdź czy MongoDB jest gotowy
docker exec -it lumenai-mongo mongosh --eval "db.adminCommand('ping')"

# Sprawdź network
docker network inspect lumenai_lumenai-network
```

### Problem: Dane nie zapisują się

```bash
# Sprawdź logi podczas wysyłania wiadomości
docker-compose logs -f backend

# Powinieneś zobaczyć:
# ✅ MongoDB connected
# 💾 Stored interaction for user_123
# ✅ Created new user: user_123
```

### Problem: Błędy w logach

**Sprawdź common issues:**

1. **ImportError** - brakujące pakiety:
   ```bash
   docker-compose exec backend pip install motor pymongo pydantic
   ```

2. **Connection timeout**:
   - Sprawdź czy MongoDB działa: `docker-compose ps`
   - Restart: `docker-compose restart mongo backend`

3. **Indeksy duplikują się**:
   - To normalne przy restartach - MongoDB ignoruje już istniejące indeksy

---

## 📊 Weryfikacja Danych w MongoDB

### Sprawdź wszystkie bazy danych
```bash
docker exec -it lumenai-mongo mongosh --eval "show dbs"
```

### Sprawdź kolekcje w bazie lumenai
```bash
docker exec -it lumenai-mongo mongosh lumenai --eval "show collections"
```

**Powinny być:**
- users
- conversations
- messages
- mood_entries
- user_context

### Policz dokumenty
```bash
docker exec -it lumenai-mongo mongosh lumenai --eval "
  db.users.countDocuments(),
  db.conversations.countDocuments(),
  db.messages.countDocuments(),
  db.mood_entries.countDocuments()
"
```

### Zobacz przykładowy dokument z każdej kolekcji
```bash
docker exec -it lumenai-mongo mongosh lumenai --eval "
  printjson(db.users.findOne());
  printjson(db.conversations.findOne());
  printjson(db.messages.findOne());
  printjson(db.mood_entries.findOne());
"
```

---

## 🎯 Testy Funkcjonalne

### Scenariusz 1: Nowy użytkownik, pierwsza rozmowa

1. Otwórz frontend
2. Wyślij wiadomość: "Cześć!"
3. Sprawdź w MongoDB:
   - ✅ Utworzono użytkownika (users)
   - ✅ Utworzono rozmowę (conversations)
   - ✅ Zapisano 2 wiadomości (messages): user + assistant

### Scenariusz 2: Kontynuacja rozmowy

1. Wyślij kolejną wiadomość: "Jak się masz?"
2. Sprawdź w MongoDB:
   - ✅ Ten sam conversation_id
   - ✅ message_count zwiększył się
   - ✅ last_message_at zaktualizowany

### Scenariusz 3: Śledzenie nastroju

1. Wyślij: "Czuję się dziś smutny"
2. Mood Agent odpowie
3. Sprawdź w MongoDB:
   - ✅ Wpis w mood_entries
   - ✅ primary: "sad"
   - ✅ intensity: 5-10
   - ✅ conversation_id powiązany

### Scenariusz 4: Restart i persystencja

1. Wyślij kilka wiadomości
2. Zatrzymaj backend: `docker-compose stop backend`
3. Uruchom ponownie: `docker-compose start backend`
4. Sprawdź przez API czy dane są dostępne:
   ```bash
   curl http://localhost:8000/api/v1/user/user_123/conversations
   ```
5. ✅ **Wszystkie rozmowy powinny być widoczne!**

---

## 📈 Co Dalej?

Po pomyślnych testach MongoDB, możesz przejść do:

1. **ChromaDB Integration** (Faza 2) - Semantyczne wyszukiwanie
   - Vector embeddings dla wiadomości
   - Inteligentne wyszukiwanie w pamięci
   - Rekomendacje oparte na kontekście

2. **Multimodal Features** (Faza 3)
   - Voice input/output
   - Image analysis (Vision Agent)
   - OCR dla dokumentów

3. **Finance Agent** (Faza 3)
   - Śledzenie wydatków w MongoDB
   - Budżety i kategorie
   - Wizualizacje finansów

4. **External Integrations** (Faza 4)
   - Google Calendar → zapisywanie eventów do MongoDB
   - Gmail → indeksowanie emaili
   - Notion → sync notatek

---

## 🐛 Known Issues & Fixes

### Issue 1: "RuntimeError: MongoDB service not initialized"

**Przyczyna:** Backend uruchomił się przed MongoDB

**Fix:**
```bash
docker-compose restart backend
```

### Issue 2: Duplikaty w conversation

**Przyczyna:** Cache w memory_manager nie jest czyszczony

**Fix:** To jest normalne - cache jest per-proces. Po restarcie backendu nowa rozmowa zostanie utworzona.

**Jeśli chcesz kontynuować ostatnią rozmowę:** Dodaj parametr `conversation_id` do request.

### Issue 3: Mood entries nie zapisują się

**Przyczyna:** Mood Agent nie dostaje memory_manager

**Fix:** Sprawdź czy orchestrator przekazuje memory_manager:
```python
"mood": MoodAgent(memory_manager=self.memory_manager)
```

---

## 📝 Podsumowanie Zmian

### Pliki Stworzone:
- ✅ `backend/DATABASE_SCHEMA.md`
- ✅ `backend/models/__init__.py`
- ✅ `backend/models/database.py`
- ✅ `backend/services/__init__.py`
- ✅ `backend/services/mongodb_service.py`

### Pliki Zmodyfikowane:
- ✅ `backend/gateway/main.py` - Inicjalizacja MongoDB + nowe endpointy
- ✅ `backend/core/memory.py` - Pełna integracja z MongoDB
- ✅ `backend/core/orchestrator.py` - Przekazywanie memory_manager do agentów
- ✅ `backend/agents/base.py` - Parametr memory_manager
- ✅ `backend/agents/cognitive/planner_agent.py` - Konstruktor
- ✅ `backend/agents/cognitive/decision_agent.py` - Konstruktor
- ✅ `backend/agents/emotional/mood_agent.py` - Zapis nastrojów do MongoDB

### Funkcjonalności Dodane:
- 💾 **Persystencja danych** - wszystko zapisywane do MongoDB
- 😊 **Mood tracking** - śledzenie emocji użytkownika
- 📊 **Statystyki** - analiza nastrojów
- 💬 **Historia rozmów** - pełny dostęp do przeszłych konwersacji
- 🔍 **Wyszukiwanie** - keyword search w wiadomościach
- 👤 **Profile użytkowników** - preferencje i kontekst

---

## 🎉 Gratulacje!

MongoDB jest **W PEŁNI ZINTEGROWANY** z LumenAI!

Teraz Twój asystent ma **pamięć trwałą** i może:
- ✅ Zapamiętywać wszystkie rozmowy
- ✅ Śledzić nastroje w czasie
- ✅ Budować długoterminowy kontekst użytkownika
- ✅ Generować statystyki i insights
- ✅ Nigdy nie zapomina danych (dopóki MongoDB działa)

**Następny krok:** ChromaDB dla semantycznego wyszukiwania! 🚀
