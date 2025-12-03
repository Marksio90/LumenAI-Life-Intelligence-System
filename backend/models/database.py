"""
MongoDB Models dla LumenAI

Ten plik definiuje strukturę danych, które zapisujemy w bazie MongoDB.
Używamy Pydantic - biblioteki, która:
- Waliduje dane (sprawdza czy są poprawne)
- Konwertuje typy (np. string na datetime)
- Generuje JSON automatycznie
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


# ============================================================================
# HELPER: ObjectId dla MongoDB
# ============================================================================
# MongoDB używa specjalnego typu ID - ObjectId
# Musimy go obsłużyć w Pydantic

class PyObjectId(ObjectId):
    """
    Wrapper dla MongoDB ObjectId, żeby działał z Pydantic.

    Przykład ObjectId: 507f1f77bcf86cd799439011
    """
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


# ============================================================================
# MODEL 1: USER - Profil Użytkownika
# ============================================================================

class UserProfile(BaseModel):
    """
    Profil użytkownika - podstawowe informacje.
    """
    name: Optional[str] = None  # Imię użytkownika
    timezone: str = "Europe/Warsaw"  # Strefa czasowa
    language: str = "pl"  # Język (pl, en, etc.)


class UserPreferences(BaseModel):
    """
    Preferencje użytkownika - jak chce używać LumenAI.
    """
    model: str = "gpt-4o-mini"  # Domyślny model LLM
    temperature: float = 0.7  # Kreatywność odpowiedzi (0-1)
    notification_enabled: bool = True  # Czy wysyłać powiadomienia


class UserMetadata(BaseModel):
    """
    Statystyki użycia systemu.
    """
    total_conversations: int = 0  # Ile rozmów przeprowadzono
    total_messages: int = 0  # Ile wiadomości wysłano
    last_active: Optional[datetime] = None  # Kiedy ostatnio aktywny


class User(BaseModel):
    """
    Główny model użytkownika.

    Przykład użycia:
        user = User(user_id="user_123", profile=UserProfile(name="Marek"))
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)  # MongoDB _id
    user_id: str  # Unikalny identyfikator użytkownika (np. "user_123")
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Kiedy utworzono
    updated_at: datetime = Field(default_factory=datetime.utcnow)  # Ostatnia aktualizacja
    profile: UserProfile = Field(default_factory=UserProfile)  # Dane profilowe
    preferences: UserPreferences = Field(default_factory=UserPreferences)  # Ustawienia
    metadata: UserMetadata = Field(default_factory=UserMetadata)  # Statystyki

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# ============================================================================
# MODEL 2: CONVERSATION - Rozmowa (sesja czatu)
# ============================================================================

class Conversation(BaseModel):
    """
    Metadane o rozmowie (sesji czatu).

    Każda rozmowa to osobna sesja - np. "Planowanie tygodnia",
    "Rozmowa o nastroju", etc.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    conversation_id: str  # Unikalny ID rozmowy (np. "conv_abc123")
    user_id: str  # Do kogo należy rozmowa
    title: Optional[str] = "Nowa rozmowa"  # Tytuł (generowany automatycznie)
    started_at: datetime = Field(default_factory=datetime.utcnow)  # Początek
    last_message_at: datetime = Field(default_factory=datetime.utcnow)  # Ostatnia wiadomość
    message_count: int = 0  # Liczba wiadomości
    primary_agent: Optional[str] = None  # Główny agent (planner/mood/decision)
    agents_used: List[str] = []  # Lista użytych agentów
    tags: List[str] = []  # Tagi (np. "produktywność", "emocje")
    summary: Optional[str] = None  # Podsumowanie rozmowy
    status: str = "active"  # Status: active/archived

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# ============================================================================
# MODEL 3: MESSAGE - Wiadomość
# ============================================================================

class MessageMetadata(BaseModel):
    """
    Metadane wiadomości - dodatkowe informacje techniczne.
    """
    tokens: Optional[int] = None  # Ile tokenów użyto
    cost: Optional[float] = None  # Koszt wygenerowania (USD)
    model: Optional[str] = None  # Jaki model użyto (np. "gpt-4o-mini")
    duration_ms: Optional[int] = None  # Jak długo trwało generowanie (ms)


class Message(BaseModel):
    """
    Pojedyncza wiadomość w rozmowie.

    Może być od użytkownika (role="user") lub od asystenta (role="assistant").

    Przykład:
        msg = Message(
            message_id="msg_123",
            conversation_id="conv_abc",
            user_id="user_123",
            role="user",
            content="Jak się masz?"
        )
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    message_id: str  # Unikalny ID wiadomości
    conversation_id: str  # Do jakiej rozmowy należy
    user_id: str  # Właściciel
    role: str  # "user" lub "assistant"
    content: str  # Treść wiadomości
    timestamp: datetime = Field(default_factory=datetime.utcnow)  # Kiedy wysłano
    agent: Optional[str] = None  # Który agent odpowiedział (null dla user)
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)  # Dodatkowe dane
    attachments: List[Dict[str, Any]] = []  # Załączniki (obrazy, pliki)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# ============================================================================
# MODEL 4: MOOD ENTRY - Wpis Nastroju
# ============================================================================

class MoodData(BaseModel):
    """
    Dane o nastroju użytkownika.
    """
    primary: str  # Główny nastrój (np. "happy", "anxious", "sad")
    intensity: int  # Intensywność 1-10
    secondary: List[str] = []  # Dodatkowe emocje
    description: Optional[str] = None  # Opis użytkownika


class MoodContext(BaseModel):
    """
    Kontekst sytuacyjny - co się dzieje w życiu użytkownika.
    """
    triggers: List[str] = []  # Co wywołało nastrój
    situation: Optional[str] = None  # Sytuacja
    location: Optional[str] = None  # Lokalizacja
    activity: Optional[str] = None  # Co robił użytkownik


class MoodIntervention(BaseModel):
    """
    Interwencja terapeutyczna - co zrobił Mood Agent.
    """
    technique: Optional[str] = None  # Użyta technika (CBT/DBT)
    exercises: List[str] = []  # Ćwiczenia zalecone
    effectiveness: Optional[int] = None  # Czy pomogło (1-10, wypełniane później)


class MoodEntry(BaseModel):
    """
    Wpis o nastroju użytkownika.

    Zapisywany przez Mood Agent podczas rozmowy o emocjach.

    Przykład:
        entry = MoodEntry(
            entry_id="mood_123",
            user_id="user_123",
            mood=MoodData(primary="anxious", intensity=7),
            context=MoodContext(triggers=["work deadline"])
        )
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    entry_id: str  # Unikalny ID wpisu
    user_id: str  # Czyj nastrój
    timestamp: datetime = Field(default_factory=datetime.utcnow)  # Kiedy zapisano
    mood: MoodData  # Dane o nastroju
    context: MoodContext = Field(default_factory=MoodContext)  # Kontekst
    intervention: MoodIntervention = Field(default_factory=MoodIntervention)  # Interwencja
    conversation_id: Optional[str] = None  # Z jakiej rozmowy pochodzi
    message_id: Optional[str] = None  # Która wiadomość wywołała

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# ============================================================================
# MODEL 5: USER CONTEXT - Długoterminowy Kontekst
# ============================================================================

class UserContext(BaseModel):
    """
    Długoterminowy kontekst o użytkowniku - czego LumenAI się nauczył.

    Przykłady:
    - Praca: "Software Developer"
    - Hobby: "Fotografia"
    - Cel: "Schudnąć 5kg"
    - Nawyk: "Bieganie 3x w tygodniu"

    Przykład:
        ctx = UserContext(
            user_id="user_123",
            context_type="personal_info",
            key="job",
            value="Software Developer",
            confidence=0.95
        )
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str  # Czyj kontekst
    context_type: str  # Typ: personal_info/relationships/goals/habits/preferences/health/routines
    key: str  # Klucz (np. "job", "hobby")
    value: Any  # Wartość (może być string, list, dict)
    confidence: float = 1.0  # Pewność (0-1)
    source: str = "conversation"  # Skąd: conversation/user_input/inferred
    first_mentioned: datetime = Field(default_factory=datetime.utcnow)  # Kiedy po raz pierwszy
    last_updated: datetime = Field(default_factory=datetime.utcnow)  # Ostatnia aktualizacja
    mention_count: int = 1  # Ile razy wspomniano
    related_conversations: List[str] = []  # Powiązane rozmowy

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# ============================================================================
# HELPER FUNCTIONS - Konwersje
# ============================================================================

def model_to_dict(model: BaseModel) -> dict:
    """
    Konwertuje model Pydantic na dict gotowy do zapisu w MongoDB.

    Usuwa None values i konwertuje ObjectId na string.
    """
    data = model.model_dump(by_alias=True, exclude_none=True)
    if "_id" in data and data["_id"] is None:
        del data["_id"]
    return data


def dict_to_model(data: dict, model_class: type[BaseModel]) -> BaseModel:
    """
    Konwertuje dict z MongoDB na model Pydantic.
    """
    return model_class(**data)
