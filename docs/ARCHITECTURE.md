# 🏗️ LumenAI Architecture

## System Overview

LumenAI is a multi-agent AI system designed to assist users with various aspects of daily life. The architecture follows a microservices pattern with specialized agents handling different domains.

## Core Components

### 1. Gateway Layer
- **FastAPI WebSocket Gateway** (`backend/gateway/main.py`)
  - Real-time bidirectional communication
  - REST API fallback
  - Connection management
  - Request routing

### 2. Core Systems

#### Orchestrator (`backend/core/orchestrator.py`)
- Central intelligence hub
- Intent analysis and classification
- Agent routing and coordination
- Response aggregation

#### Memory Manager (`backend/core/memory.py`)
- Short-term conversation memory
- Long-term user profile storage
- Context retrieval and caching
- Privacy-aware data handling

#### LLM Engine (`backend/core/llm_engine.py`)
- Unified interface for multiple LLM providers
- Support for OpenAI, Anthropic Claude
- Streaming response capability
- Context injection

### 3. Multi-Agent System

All agents inherit from `BaseAgent` and specialize in different domains:

#### Cognitive Agents
- **Planner Agent**: Task management, scheduling, productivity
- **Decision Agent**: Life choices, pros/cons analysis, decision frameworks

#### Emotional Agents
- **Mood Agent**: Emotional support, mood tracking, CBT/DBT techniques

#### Multimodal Agents (Planned)
- **Vision Agent**: Image analysis, OCR
- **Speech Agent**: Voice recognition, text-to-speech

#### Functional Agents (Planned)
- **Finance Agent**: Budget tracking, expense analysis
- **Automation Agent**: Email, calendar, external integrations

## Data Flow

```
User Input (Text/Voice/Image)
         │
         ▼
   Gateway (WebSocket)
         │
         ▼
    Orchestrator
    │
    ├─ Intent Analysis (LLM)
    ├─ Context Retrieval (Memory)
    │
    ▼
Agent Selection & Routing
    │
    ├─ Planner Agent
    ├─ Mood Agent
    ├─ Decision Agent
    └─ General LLM
         │
         ▼
   Response Generation
         │
         ▼
    Memory Storage
         │
         ▼
  Return to User (WebSocket)
```

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python)
- **WebSocket**: Native FastAPI WebSocket support
- **LLM Integration**: LangChain, OpenAI SDK, Anthropic SDK
- **Vector DB**: ChromaDB for semantic search
- **Cache**: Redis for session and response caching
- **Database**: MongoDB for user data and history

### Frontend
- **Framework**: Next.js 14 (App Router)
- **UI**: React 18 + TailwindCSS
- **State**: Zustand
- **Real-time**: Socket.io-client
- **Markdown**: react-markdown for rich responses

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes-ready (planned)
- **Monitoring**: Prometheus + Grafana (planned)

## Agent Architecture

### Base Agent Pattern

```python
class BaseAgent(ABC):
    - process(user_id, message, context, metadata) -> str
    - can_handle(message, context) -> float
    - get_info() -> Dict
```

### Specialized Agent Example

```python
class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Planner", description="...")

    async def process(...):
        # 1. Classify request type
        # 2. Extract entities
        # 3. Execute action (create task, view schedule, etc.)
        # 4. Generate response
        return response
```

## Memory System

### Three-Tier Memory

1. **Short-term (Conversation Context)**
   - Last 10-20 messages
   - Current session state
   - In-memory cache

2. **Medium-term (User Profile)**
   - Preferences and settings
   - Habits and patterns
   - MongoDB storage

3. **Long-term (Semantic Memory)**
   - Vector embeddings of all interactions
   - Semantic search capability
   - ChromaDB storage

### Memory Retrieval

```python
context = {
    "recent_messages": [...],      # Last 10 messages
    "user_profile": {...},          # Preferences, habits
    "relevant_memories": [...],     # Vector search results
    "recent_summary": "..."         # LLM-generated summary
}
```

## Security & Privacy

### Data Protection
- End-to-end encryption for sensitive data
- User-controlled data retention
- Anonymization of training data
- GDPR-compliant data deletion

### Authentication (Planned)
- JWT tokens
- OAuth2 integration
- Multi-factor authentication

### Authorization
- Role-based access control
- Per-agent permissions
- API rate limiting

## Scalability Considerations

### Horizontal Scaling
- Stateless backend services
- Session data in Redis
- Load balancer ready

### Performance Optimization
- Response caching
- LLM result memoization
- Database query optimization
- Connection pooling

## Extension Points

### Adding New Agents
1. Create agent class inheriting from `BaseAgent`
2. Implement `process()` method
3. Register in `orchestrator.py`
4. Update intent classification

### Adding New LLM Providers
1. Add provider to `llm_engine.py`
2. Implement `_generate_<provider>()` method
3. Update configuration

### Adding External Integrations
1. Create service module in `backend/services/integrations/`
2. Implement OAuth/API authentication
3. Add agent action methods
4. Register with Automation Agent

## Future Enhancements

- [ ] Multi-language support
- [ ] Advanced personalization with local ML models
- [ ] Integration with wearables (health data)
- [ ] Proactive suggestions based on patterns
- [ ] Plugin system for community extensions
- [ ] Mobile app (React Native)
- [ ] Voice-first interface

## Directory Structure

```
LumenAI/
├── backend/
│   ├── gateway/          # API entry point
│   ├── core/             # Core systems
│   │   ├── orchestrator  # Agent routing
│   │   ├── memory        # Memory management
│   │   └── llm_engine    # LLM interface
│   ├── agents/           # Specialized agents
│   │   ├── cognitive/    # Planner, Decision
│   │   ├── emotional/    # Mood, Therapy
│   │   ├── vision/       # Image analysis
│   │   └── speech/       # Voice processing
│   ├── ml/               # ML models
│   ├── services/         # External integrations
│   └── shared/           # Shared utilities
├── frontend/             # Next.js app
├── infra/                # Infrastructure
│   ├── docker/           # Dockerfiles
│   ├── kubernetes/       # K8S manifests
│   └── monitoring/       # Observability
└── docs/                 # Documentation
```

## Performance Metrics

### Target SLAs
- API Response Time: < 200ms (p95)
- LLM Response Time: < 3s (p95)
- WebSocket Latency: < 50ms
- System Uptime: 99.9%

## Monitoring & Observability

### Metrics to Track
- Request rate and latency
- Agent invocation frequency
- LLM token usage and cost
- Error rates by agent
- User engagement metrics

### Logging Strategy
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized log aggregation (planned)
- PII redaction in logs

---

For implementation details, see source code and inline documentation.
