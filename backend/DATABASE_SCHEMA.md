# LumenAI - MongoDB Schema Design

## 📋 Przegląd

Ta dokumentacja opisuje strukturę bazy danych MongoDB dla systemu LumenAI.

## 🗄️ Baza Danych: `lumenai_db`

---

## 📚 Collections (Kolekcje)

### 1️⃣ **users** - Profile Użytkowników

Przechowuje informacje o użytkownikach systemu.

```json
{
  "_id": "ObjectId(auto-generated)",
  "user_id": "user_123",
  "created_at": "2025-12-03T10:30:00Z",
  "updated_at": "2025-12-03T15:45:00Z",
  "profile": {
    "name": "Marek",
    "timezone": "Europe/Warsaw",
    "language": "pl"
  },
  "preferences": {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "notification_enabled": true
  },
  "metadata": {
    "total_conversations": 42,
    "total_messages": 523,
    "last_active": "2025-12-03T15:45:00Z"
  }
}
```

**Pola:**
- `_id`: Automatyczne MongoDB ID
- `user_id`: Unikalny identyfikator użytkownika (string)
- `created_at`: Kiedy utworzono profil
- `updated_at`: Ostatnia aktualizacja
- `profile`: Dane profilowe
- `preferences`: Ustawienia użytkownika
- `metadata`: Statystyki użycia

**Indeksy:**
- `user_id` (unique) - szybkie wyszukiwanie po user_id

---

### 2️⃣ **conversations** - Rozmowy

Przechowuje metadane o rozmowach (sesje czatu).

```json
{
  "_id": "ObjectId(auto-generated)",
  "conversation_id": "conv_abc123",
  "user_id": "user_123",
  "title": "Planowanie tygodnia",
  "started_at": "2025-12-03T10:00:00Z",
  "last_message_at": "2025-12-03T10:45:00Z",
  "message_count": 12,
  "primary_agent": "planner",
  "agents_used": ["planner", "mood"],
  "tags": ["planowanie", "produktywność"],
  "summary": "Użytkownik planował tydzień, ustalił priorytety...",
  "status": "active"
}
```

**Pola:**
- `conversation_id`: Unikalny ID rozmowy
- `user_id`: Do kogo należy rozmowa
- `title`: Tytuł rozmowy (generowany automatycznie)
- `started_at`: Początek rozmowy
- `last_message_at`: Ostatnia wiadomość
- `message_count`: Liczba wiadomości
- `primary_agent`: Główny agent w rozmowie
- `agents_used`: Lista użytych agentów
- `tags`: Tagi do kategoryzacji
- `summary`: Podsumowanie rozmowy
- `status`: active/archived

**Indeksy:**
- `conversation_id` (unique)
- `user_id` + `started_at` (wyszukiwanie rozmów użytkownika)

---

### 3️⃣ **messages** - Wiadomości

Przechowuje wszystkie wiadomości w rozmowach.

```json
{
  "_id": "ObjectId(auto-generated)",
  "message_id": "msg_xyz789",
  "conversation_id": "conv_abc123",
  "user_id": "user_123",
  "role": "user",
  "content": "Jak zaplanować jutrzejszy dzień?",
  "timestamp": "2025-12-03T10:30:00Z",
  "agent": null,
  "metadata": {
    "tokens": 8,
    "cost": 0.0001,
    "model": null,
    "duration_ms": null
  },
  "attachments": []
}
```

```json
{
  "_id": "ObjectId(auto-generated)",
  "message_id": "msg_xyz790",
  "conversation_id": "conv_abc123",
  "user_id": "user_123",
  "role": "assistant",
  "content": "Pomogę Ci zaplanować jutrzejszy dzień...",
  "timestamp": "2025-12-03T10:30:15Z",
  "agent": "planner",
  "metadata": {
    "tokens": 150,
    "cost": 0.0023,
    "model": "gpt-4o-mini",
    "duration_ms": 1200
  },
  "attachments": []
}
```

**Pola:**
- `message_id`: Unikalny ID wiadomości
- `conversation_id`: Do jakiej rozmowy należy
- `user_id`: Właściciel
- `role`: "user" lub "assistant"
- `content`: Treść wiadomości
- `timestamp`: Kiedy wysłano
- `agent`: Który agent odpowiedział (null dla user)
- `metadata`: Dodatkowe dane (tokeny, koszt, model)
- `attachments`: Lista załączników (obrazy, pliki)

**Indeksy:**
- `message_id` (unique)
- `conversation_id` + `timestamp` (chronologiczne wiadomości)
- `user_id` + `timestamp` (historia użytkownika)

---

### 4️⃣ **mood_entries** - Wpisy Nastrojów

Przechowuje dane o nastrojach użytkownika (z Mood Agent).

```json
{
  "_id": "ObjectId(auto-generated)",
  "entry_id": "mood_def456",
  "user_id": "user_123",
  "timestamp": "2025-12-03T14:30:00Z",
  "mood": {
    "primary": "anxious",
    "intensity": 7,
    "secondary": ["stressed", "overwhelmed"],
    "description": "Czuję się przytłoczony pracą"
  },
  "context": {
    "triggers": ["deadline at work", "lack of sleep"],
    "situation": "Zbliżający się termin projektu",
    "location": null,
    "activity": "working"
  },
  "intervention": {
    "technique": "CBT - Cognitive Restructuring",
    "exercises": ["breathing exercise", "thought challenging"],
    "effectiveness": null
  },
  "conversation_id": "conv_abc123",
  "message_id": "msg_xyz791"
}
```

**Pola:**
- `entry_id`: Unikalny ID wpisu nastroju
- `user_id`: Czyj nastrój
- `timestamp`: Kiedy zapisano
- `mood`: Dane o nastroju
  - `primary`: Główny nastrój
  - `intensity`: Intensywność (1-10)
  - `secondary`: Dodatkowe emocje
  - `description`: Opis użytkownika
- `context`: Kontekst sytuacyjny
  - `triggers`: Co wywołało nastrój
  - `situation`: Sytuacja
  - `location`: Lokalizacja (opcjonalne)
  - `activity`: Co robił użytkownik
- `intervention`: Interwencja terapeutyczna
  - `technique`: Użyta technika (CBT/DBT)
  - `exercises`: Ćwiczenia
  - `effectiveness`: Czy pomogło (wypełniane później)
- `conversation_id`: Z jakiej rozmowy pochodzi
- `message_id`: Która wiadomość wywołała

**Indeksy:**
- `entry_id` (unique)
- `user_id` + `timestamp` (chronologia nastrojów)
- `user_id` + `mood.primary` (analiza wzorców)

---

### 5️⃣ **user_context** - Długoterminowy Kontekst

Przechowuje nauczony kontekst o użytkowniku.

```json
{
  "_id": "ObjectId(auto-generated)",
  "user_id": "user_123",
  "context_type": "personal_info",
  "key": "job",
  "value": "Software Developer",
  "confidence": 0.95,
  "source": "conversation",
  "first_mentioned": "2025-11-15T10:00:00Z",
  "last_updated": "2025-12-01T14:30:00Z",
  "mention_count": 8,
  "related_conversations": ["conv_abc123", "conv_def456"]
}
```

**Typy kontekstu (`context_type`):**
- `personal_info`: Informacje osobiste (imię, praca, hobby)
- `relationships`: Relacje (rodzina, przyjaciele)
- `goals`: Cele życiowe
- `habits`: Nawyki
- `preferences`: Preferencje
- `health`: Zdrowie i samopoczucie
- `routines`: Rutyny codzienne

**Pola:**
- `user_id`: Czyj kontekst
- `context_type`: Typ informacji
- `key`: Klucz (np. "job", "hobby")
- `value`: Wartość
- `confidence`: Pewność (0-1)
- `source`: Skąd pochodzi (conversation/user_input/inferred)
- `first_mentioned`: Kiedy po raz pierwszy
- `last_updated`: Ostatnia aktualizacja
- `mention_count`: Ile razy wspomniano
- `related_conversations`: Powiązane rozmowy

**Indeksy:**
- `user_id` + `context_type` + `key` (unique compound)
- `user_id` + `confidence` (wysokiej jakości kontekst)

---

## 🔍 Przykładowe Zapytania

### Pobranie ostatnich 10 rozmów użytkownika:
```python
conversations = await db.conversations.find(
    {"user_id": "user_123"}
).sort("last_message_at", -1).limit(10).to_list(10)
```

### Pobranie wszystkich wiadomości z rozmowy:
```python
messages = await db.messages.find(
    {"conversation_id": "conv_abc123"}
).sort("timestamp", 1).to_list(None)
```

### Analiza nastrojów z ostatniego tygodnia:
```python
from datetime import datetime, timedelta

week_ago = datetime.utcnow() - timedelta(days=7)
mood_entries = await db.mood_entries.find({
    "user_id": "user_123",
    "timestamp": {"$gte": week_ago}
}).sort("timestamp", 1).to_list(None)
```

### Pobranie kontekstu użytkownika:
```python
context = await db.user_context.find({
    "user_id": "user_123",
    "confidence": {"$gte": 0.7}  # tylko pewne informacje
}).to_list(None)
```

---

## 📈 Rozszerzalność

W przyszłości możemy dodać:

- **tasks** - Zadania i projekty
- **habits** - Śledzenie nawyków
- **decisions** - Historia podejmowanych decyzji
- **integrations** - Dane z zewnętrznych serwisów (kalendarz, Gmail)
- **analytics** - Agregowane statystyki

---

## 🔒 Bezpieczeństwo

- Wszystkie dane użytkownika powinny być izolowane przez `user_id`
- Hasła (jeśli dodamy auth) TYLKO jako hash (bcrypt)
- Wrażliwe dane (mood, personal context) wymagają dodatkowej ochrony
- Backup bazy danych codziennie

---

## 🚀 Następne Kroki

1. ✅ Zaprojektować schemat (TEN DOKUMENT)
2. ⏳ Stworzyć modele Pydantic
3. ⏳ Stworzyć MongoDB service layer
4. ⏳ Zintegrować z memory.py
5. ⏳ Dodać API endpoints
6. ⏳ Testy
