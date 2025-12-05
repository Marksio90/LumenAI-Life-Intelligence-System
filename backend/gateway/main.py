"""
LumenAI Gateway - Main FastAPI Application
WebSocket-enabled real-time AI assistant gateway
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Form, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
from typing import Dict, List, Optional
import base64
import json
import asyncio
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append('..')

from backend.shared.config.settings import settings
from backend.core.orchestrator import Orchestrator
from backend.core.memory import MemoryManager
from backend.services.mongodb_service import init_mongodb_service, get_mongodb_service
from backend.services.chromadb_service import init_chromadb_service, get_chromadb_service
from backend.services.embedding_service import init_embedding_service, get_embedding_service
from backend.services.analytics_service import init_analytics_service, get_analytics_service
from backend.services.notification_service import init_notification_service, get_notification_service
from backend.services.auth_service import init_auth_service, get_auth_service
from backend.services.user_repository import init_user_repository, get_user_repository
from backend.ml.feature_engineering import FeatureEngineer
from backend.ml.training_service import init_training_service, get_training_service
from backend.models.user import UserCreate, UserLogin, UserPublic, UserUpdate, Token, PasswordChange, UserSettingsUpdate
from backend.middleware.auth_middleware import (
    get_current_user_from_token,
    get_current_active_user,
    get_current_verified_user,
    get_current_superuser
)
from backend.middleware.rate_limit_middleware import RateLimitMiddleware, get_rate_limiter
from backend.middleware.error_middleware import register_exception_handlers
from backend.core.exceptions import LumenAIException


# Connection Manager for WebSocket
class ConnectionManager:
    """Manages active WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)


# Initialize core components
manager = ConnectionManager()
orchestrator = None
memory_manager = None
mongodb_service = None
chromadb_service = None
embedding_service = None
analytics_service = None
notification_service = None
feature_engineer = None
training_service = None
auth_service = None
user_repository = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator, memory_manager, mongodb_service, chromadb_service, embedding_service, analytics_service, notification_service, feature_engineer, training_service, auth_service, user_repository

    logger.info("🚀 Starting LumenAI...")

    # Initialize Authentication Service
    try:
        auth_service = init_auth_service(secret_key=settings.SECRET_KEY)
        logger.info("✅ Authentication Service initialized")
    except Exception as e:
        logger.warning(f"⚠️  Auth Service initialization failed: {e}")
        auth_service = None

    # Initialize MongoDB
    try:
        mongodb_service = init_mongodb_service(
            connection_string=settings.MONGODB_URL,
            database_name=settings.MONGODB_DB_NAME
        )
        await mongodb_service.connect()
        logger.info("✅ MongoDB connected")

        # Initialize User Repository (requires MongoDB)
        if mongodb_service:
            user_repository = init_user_repository(mongodb_service.db)
            await user_repository.ensure_indexes()
            logger.info("✅ User Repository initialized")
    except Exception as e:
        logger.warning(f"⚠️  MongoDB connection failed: {e}. Running without persistence.")
        mongodb_service = None
        user_repository = None

    # Initialize ChromaDB
    try:
        chromadb_service = init_chromadb_service(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        await chromadb_service.connect()
        logger.info("✅ ChromaDB connected")
    except Exception as e:
        logger.warning(f"⚠️  ChromaDB connection failed: {e}. Running without vector search.")
        chromadb_service = None

    # Initialize Embedding Service
    try:
        if settings.OPENAI_API_KEY:
            embedding_service = init_embedding_service(
                api_key=settings.OPENAI_API_KEY
            )
            logger.info("✅ Embedding Service initialized")
        else:
            logger.warning("⚠️  No OpenAI API key - embeddings disabled")
            embedding_service = None
    except Exception as e:
        logger.warning(f"⚠️  Embedding Service failed: {e}")
        embedding_service = None

    # Initialize core systems
    memory_manager = MemoryManager()
    orchestrator = Orchestrator(memory_manager)

    # Initialize Analytics Service (requires all other services)
    try:
        if chromadb_service and embedding_service:
            analytics_service = init_analytics_service(
                llm_engine=orchestrator.llm_engine,
                memory_manager=memory_manager,
                chromadb_service=chromadb_service,
                embedding_service=embedding_service
            )
            logger.info("✅ Analytics Service initialized")
        else:
            logger.warning("⚠️  Analytics Service disabled (requires ChromaDB + Embeddings)")
            analytics_service = None
    except Exception as e:
        logger.warning(f"⚠️  Analytics Service failed: {e}")
        analytics_service = None

    # Initialize ML Services (Feature Engineering + Training)
    try:
        feature_engineer = FeatureEngineer(
            memory_manager=memory_manager,
            embedding_service=embedding_service
        )
        logger.info("✅ Feature Engineer initialized")

        training_service = init_training_service(
            memory_manager=memory_manager,
            feature_engineer=feature_engineer,
            models_dir="backend/ml/models"
        )
        logger.info("✅ ML Training Service initialized")
    except Exception as e:
        logger.warning(f"⚠️  ML Services failed: {e}. Running without ML capabilities.")
        feature_engineer = None
        training_service = None

    # Initialize Notification Service
    try:
        notification_service = init_notification_service(
            memory_manager=memory_manager,
            training_service=training_service,
            analytics_service=analytics_service
        )
        logger.info("✅ Notification Service initialized")
    except Exception as e:
        logger.warning(f"⚠️  Notification Service failed: {e}. Running without notifications.")
        notification_service = None

    logger.info("✅ LumenAI initialized successfully")

    yield

    # Cleanup
    logger.info("🛑 Shutting down LumenAI...")
    if mongodb_service:
        await mongodb_service.disconnect()
        logger.info("✅ MongoDB disconnected")
    if chromadb_service:
        await chromadb_service.disconnect()
        logger.info("✅ ChromaDB disconnected")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,  # 100 requests per minute (global)
    window_seconds=60,
    exclude_paths=["/health", "/docs", "/redoc", "/openapi.json", "/"]
)

# Register Exception Handlers
register_exception_handlers(app)


# Health Check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "🌟 Welcome to LumenAI - Your Life Intelligence System",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# ============================================================================
# AUTHENTICATION ENDPOINTS - User Registration and Login
# ============================================================================

@app.post("/api/v1/auth/register", response_model=dict)
async def register(user_create: UserCreate):
    """
    Register a new user account.

    Creates a new user with hashed password and returns access token.

    Example:
        POST /api/v1/auth/register
        Body: {
            "email": "user@example.com",
            "username": "john_doe",
            "password": "SecurePassword123",
            "full_name": "John Doe"
        }

    Response:
        {
            "status": "success",
            "message": "User registered successfully",
            "user": {...},
            "token": {
                "access_token": "eyJ...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }
    """
    try:
        user_repo = get_user_repository()
        if not user_repo:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User registration unavailable. Database not connected."
            )

        # Create user
        user = await user_repo.create_user(user_create)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        # Generate access token
        auth = get_auth_service()
        access_token = auth.create_access_token(user.user_id, user.email)
        refresh_token = auth.create_refresh_token(user.user_id, user.email)

        # Create public user response
        user_public = UserPublic(**user.model_dump())

        logger.info(f"✅ New user registered: {user.email}")

        return {
            "status": "success",
            "message": "User registered successfully! Welcome to LumenAI 🌟",
            "user": user_public.model_dump(),
            "token": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 86400  # 24 hours
            }
        }

    except ValueError as e:
        # User already exists or validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@app.post("/api/v1/auth/login")
async def login(user_login: UserLogin):
    """
    Login with email and password.

    Validates credentials and returns access token.

    Example:
        POST /api/v1/auth/login
        Body: {
            "email": "user@example.com",
            "password": "SecurePassword123"
        }

    Response:
        {
            "status": "success",
            "message": "Login successful",
            "user": {...},
            "token": {
                "access_token": "eyJ...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }
    """
    try:
        user_repo = get_user_repository()
        if not user_repo:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication unavailable. Database not connected."
            )

        # Get user by email
        user = await user_repo.get_user_by_email(user_login.email)

        if not user:
            logger.warning(f"Login attempt with non-existent email: {user_login.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        auth = get_auth_service()
        if not auth.verify_password(user_login.password, user.hashed_password):
            logger.warning(f"Failed login attempt for: {user_login.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive. Contact support."
            )

        # Update last login
        await user_repo.update_last_login(user.user_id)

        # Generate tokens
        access_token = auth.create_access_token(user.user_id, user.email)
        refresh_token = auth.create_refresh_token(user.user_id, user.email)

        # Create public user response
        user_public = UserPublic(**user.model_dump())

        logger.info(f"✅ User logged in: {user.email}")

        return {
            "status": "success",
            "message": f"Welcome back, {user.username}! 👋",
            "user": user_public.model_dump(),
            "token": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 86400  # 24 hours
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@app.post("/api/v1/auth/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token.

    Example:
        POST /api/v1/auth/refresh
        Body: {"refresh_token": "eyJ..."}

    Response:
        {
            "access_token": "eyJ...",
            "token_type": "bearer",
            "expires_in": 86400
        }
    """
    try:
        auth = get_auth_service()
        new_access_token = auth.refresh_access_token(refresh_token)

        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 86400
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@app.get("/api/v1/auth/me", response_model=UserPublic)
async def get_current_user_profile(
    current_user: UserPublic = Depends(get_current_active_user)
):
    """
    Get current authenticated user's profile.

    Requires valid JWT token in Authorization header.

    Example:
        GET /api/v1/auth/me
        Headers: {"Authorization": "Bearer eyJ..."}

    Response:
        {
            "user_id": "user_123",
            "email": "user@example.com",
            "username": "john_doe",
            ...
        }
    """
    return current_user


@app.put("/api/v1/auth/me")
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_active_user)
):
    """
    Update current user's profile.

    Example:
        PUT /api/v1/auth/me
        Headers: {"Authorization": "Bearer eyJ..."}
        Body: {
            "full_name": "John Smith",
            "bio": "AI enthusiast",
            "timezone": "America/New_York"
        }

    Response:
        {
            "status": "success",
            "message": "Profile updated successfully",
            "user": {...}
        }
    """
    try:
        user_repo = get_user_repository()
        if not user_repo:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable"
            )

        updated_user = await user_repo.update_user(current_user.user_id, user_update)

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )

        user_public = UserPublic(**updated_user.model_dump())

        return {
            "status": "success",
            "message": "Profile updated successfully ✅",
            "user": user_public.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@app.post("/api/v1/auth/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user = Depends(get_current_active_user)
):
    """
    Change user's password.

    Example:
        POST /api/v1/auth/change-password
        Headers: {"Authorization": "Bearer eyJ..."}
        Body: {
            "current_password": "OldPassword123",
            "new_password": "NewSecurePassword456"
        }

    Response:
        {
            "status": "success",
            "message": "Password changed successfully"
        }
    """
    try:
        user_repo = get_user_repository()
        auth = get_auth_service()

        if not user_repo or not auth:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable"
            )

        # Get full user data (including hashed password)
        user = await user_repo.get_user_by_id(current_user.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not auth.verify_password(password_change.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        # Hash new password
        new_password_hash = auth.hash_password(password_change.new_password)

        # Update password in database
        success = await user_repo.change_password(user.user_id, new_password_hash)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )

        logger.info(f"✅ Password changed for user: {user.email}")

        return {
            "status": "success",
            "message": "Password changed successfully 🔒"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@app.get("/api/v1/user/settings")
async def get_user_settings(
    current_user = Depends(get_current_active_user)
):
    """
    Get current user's settings and preferences.

    Returns all user preferences including:
    - UI preferences (theme, language, etc.)
    - Notification settings
    - Integration configurations
    - API keys (masked)

    Example:
        GET /api/v1/user/settings
        Headers: {"Authorization": "Bearer eyJ..."}

    Response:
        {
            "preferences": {...},
            "notifications": {...},
            "integrations": {...}
        }
    """
    try:
        user_repo = get_user_repository()
        if not user_repo:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable"
            )

        user = await user_repo.get_user_by_id(current_user.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Return preferences with defaults
        preferences = user.preferences or {}

        return {
            "status": "success",
            "settings": preferences
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch settings"
        )


@app.put("/api/v1/user/settings")
async def update_user_settings(
    settings: UserSettingsUpdate,  # Now using validated Pydantic model
    current_user = Depends(get_current_active_user)
):
    """
    Update current user's settings and preferences.

    Security: All inputs are validated against strict schema
    Unknown fields are rejected to prevent injection attacks

    Example:
        PUT /api/v1/user/settings
        Headers: {"Authorization": "Bearer eyJ..."}
        Body: {
            "preferences": {
                "theme": "dark",
                "language": "pl",
                "compact_mode": false
            },
            "notifications": {
                "email_notifications": true,
                "push_notifications": false,
                "notification_frequency": "daily"
            }
        }

    Response:
        {
            "status": "success",
            "message": "Settings updated successfully"
        }
    """
    try:
        user_repo = get_user_repository()
        if not user_repo:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable"
            )

        # Get current user
        user = await user_repo.get_user_by_id(current_user.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get current preferences
        current_preferences = user.preferences or {}

        # Merge new validated settings
        if settings.preferences:
            current_preferences.setdefault('preferences', {})
            current_preferences['preferences'].update(
                settings.preferences.model_dump(exclude_none=True)
            )

        if settings.notifications:
            current_preferences.setdefault('notifications', {})
            current_preferences['notifications'].update(
                settings.notifications.model_dump(exclude_none=True)
            )

        # Update user with validated preferences
        user_update = UserUpdate(preferences=current_preferences)
        updated_user = await user_repo.update_user(current_user.user_id, user_update)

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update settings"
            )

        logger.info(f"✅ Settings updated for user: {current_user.user_id}")

        return {
            "status": "success",
            "message": "Settings updated successfully",
            "settings": updated_user.preferences
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Settings update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"  # Don't leak error details
        )


# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time bidirectional communication + notifications

    Authentication: Requires valid JWT token as query parameter
    Example: ws://localhost:8000/ws/chat?token=YOUR_JWT_TOKEN

    Security: User identity is derived from JWT token, not URL parameter
    """
    # Authenticate user with JWT token BEFORE accepting connection
    try:
        from backend.core.auth import get_current_user_ws
        user_data = await get_current_user_ws(token)
        user_id = user_data["user_id"]
        logger.info(f"WebSocket authentication successful for user: {user_id}")
    except HTTPException as e:
        logger.error(f"WebSocket authentication failed: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, user_id)

    # Register notification callback for real-time push
    if notification_service:
        async def notification_callback(notification):
            """Send notification through WebSocket"""
            await manager.send_message(user_id, {
                "type": "notification",
                "notification": notification.to_dict()
            })
        notification_service.register_callback(user_id, notification_callback)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            logger.info(f"Received from {user_id}: {data}")

            # Extract message content
            message = data.get("message", "")
            message_type = data.get("type", "text")  # text, voice, image
            metadata = data.get("metadata", {})

            # Send typing indicator
            await manager.send_message(user_id, {
                "type": "status",
                "status": "typing"
            })

            # Process through orchestrator
            response = await orchestrator.process_message(
                user_id=user_id,
                message=message,
                message_type=message_type,
                metadata=metadata
            )

            # Send response back to client
            await manager.send_message(user_id, {
                "type": "message",
                "content": response["content"],
                "agent": response.get("agent", "unknown"),
                "metadata": response.get("metadata", {})
            })

            # Check for smart notifications after message processing
            if notification_service:
                # Check mood-based notifications if mood was tracked
                if metadata.get("mood"):
                    await notification_service.detect_mood_drop(user_id, metadata["mood"])
                    await notification_service.detect_mood_improvement(user_id, metadata["mood"])

                # Check ML predictions
                await notification_service.check_ml_predictions(user_id, message)

    except WebSocketDisconnect:
        if notification_service:
            notification_service.unregister_callback(user_id)
        manager.disconnect(user_id)
        logger.info(f"Client {user_id} disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket for {user_id}: {e}")
        if notification_service:
            notification_service.unregister_callback(user_id)
        manager.disconnect(user_id)


# REST API Endpoints

@app.post("/api/v1/chat")
async def chat(request: dict):
    """
    REST endpoint for chat (alternative to WebSocket)
    """
    try:
        user_id = request.get("user_id")
        message = request.get("message")
        message_type = request.get("type", "text")

        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id and message are required")

        response = await orchestrator.process_message(
            user_id=user_id,
            message=message,
            message_type=message_type
        )

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat/stream")
async def chat_stream(request: dict):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time AI responses.

    NOW WITH TRUE STREAMING! 🌊
    Streams tokens directly from LLM APIs (OpenAI/Anthropic) as they're generated.
    """
    try:
        user_id = request.get("user_id")
        message = request.get("message")
        message_type = request.get("type", "text")
        conversation_id = request.get("conversationId")

        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id and message are required")

        async def generate_stream():
            """Generator function for TRUE SSE streaming"""
            try:
                # Send start event
                yield f"data: {json.dumps({'type': 'start', 'message': 'Connecting to AI...'})}\n\n"

                # Classify intent to determine agent
                intent_result = await orchestrator.classify_intent(message)
                agent_name = intent_result.get("agent", "cognitive")

                logger.info(f"🎯 Intent classified: {agent_name} for message: {message[:50]}")

                # Get the appropriate agent
                agent = orchestrator.agents.get(agent_name)
                if not agent:
                    agent = orchestrator.agents["cognitive"]  # Fallback

                # Get conversation context
                context = await memory_manager.get_user_context(user_id) if memory_manager else None

                # Send agent info
                yield f"data: {json.dumps({'type': 'agent', 'agent': agent_name})}\n\n"

                # TRUE STREAMING: Stream tokens directly from LLM
                full_response = ""

                async for token in orchestrator.llm_engine.generate_stream(
                    prompt=message,
                    system_prompt=agent.system_prompt,
                    context=context,
                    temperature=0.7,
                    task_type=agent_name
                ):
                    # Send each token as it arrives
                    full_response += token

                    token_data = {
                        "type": "token",
                        "content": token,
                        "agent": agent_name
                    }
                    yield f"data: {json.dumps(token_data)}\n\n"

                # Store conversation in memory
                if memory_manager:
                    await memory_manager.add_message(
                        user_id=user_id,
                        user_message=message,
                        assistant_response=full_response,
                        agent=agent_name
                    )

                # Send completion event
                complete_data = {
                    "type": "complete",
                    "content": full_response,
                    "agent": agent_name,
                    "metadata": {
                        "tokens": len(full_response.split()),
                        "agent": agent_name
                    }
                }
                yield f"data: {json.dumps(complete_data)}\n\n"

                # Send done signal
                yield "data: [DONE]\n\n"

                logger.info(f"✅ Streaming complete for user {user_id}")

            except Exception as e:
                logger.error(f"Error in stream generation: {e}")
                error_data = {
                    "type": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )

    except Exception as e:
        logger.error(f"Error in chat stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/user/{user_id}/history")
async def get_user_history(user_id: str, limit: int = 50):
    """Get user's conversation history"""
    try:
        history = await memory_manager.get_user_history(user_id, limit=limit)
        return {"user_id": user_id, "history": history}
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/user/memory")
async def clear_user_memory(current_user = Depends(get_current_active_user)):
    """
    Clear current user's memory (privacy feature)

    Requires: Active user authentication
    Security: Users can only delete their own memory
    """
    try:
        user_id = current_user.user_id
        await memory_manager.clear_user_memory(user_id)
        logger.info(f"Memory cleared for user {user_id}")
        return {"status": "success", "message": f"Memory cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/stats/costs")
async def get_cost_stats(current_user = Depends(get_current_superuser)):
    """
    Get LLM API cost statistics

    Requires: Superuser/Admin authentication
    Security: Cost data is sensitive business information
    """
    try:
        from backend.core.cost_tracker import cost_tracker
        stats = cost_tracker.get_stats()

        # Add estimated monthly cost
        if stats["total_requests"] > 0:
            stats["estimated_monthly_cost"] = cost_tracker.estimate_monthly_cost(
                requests_per_day=100
            )

        logger.info(f"Cost stats accessed by admin {current_user.user_id}")
        return {
            "status": "success",
            "data": stats,
            "message": f"💰 Total cost: ${stats['total_cost']:.4f}"
        }
    except Exception as e:
        logger.error(f"Error fetching cost stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# NEW: MongoDB-powered endpoints
# ============================================================================

@app.get("/api/v1/user/conversations")
async def get_user_conversations(
    limit: int = 20,
    skip: int = 0,
    current_user = Depends(get_current_active_user)
):
    """
    Get current user's conversations with MongoDB persistence

    Requires: Active user authentication
    Security: Users can only access their own conversations
    NEW FEATURE: Conversations now persist across restarts! 🎉
    """
    try:
        user_id = current_user.user_id
        db = get_mongodb_service()
        conversations = await db.get_user_conversations(user_id, limit=limit, skip=skip)

        return {
            "status": "success",
            "user_id": user_id,
            "total": len(conversations),
            "conversations": [
                {
                    "conversation_id": conv.conversation_id,
                    "title": conv.title,
                    "started_at": conv.started_at.isoformat(),
                    "last_message_at": conv.last_message_at.isoformat(),
                    "message_count": conv.message_count,
                    "agents_used": conv.agents_used,
                    "status": conv.status
                }
                for conv in conversations
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/conversation/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, limit: int = 100):
    """
    Get all messages from a conversation

    NEW FEATURE: Full conversation history from MongoDB! 💬
    """
    try:
        db = get_mongodb_service()
        messages = await db.get_conversation_messages(conversation_id, limit=limit)

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "total": len(messages),
            "messages": [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "agent": msg.agent,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": {
                        "tokens": msg.metadata.tokens,
                        "cost": msg.metadata.cost,
                        "model": msg.metadata.model
                    }
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/user/mood/history")
async def get_mood_history(
    days: int = 7,
    current_user = Depends(get_current_active_user)
):
    """
    Get current user's mood history

    Requires: Active user authentication
    Security: Users can only access their own sensitive mood data
    NEW FEATURE: Mood tracking with MongoDB! 😊
    """
    try:
        user_id = current_user.user_id
        mood_history = await memory_manager.get_mood_history(user_id, days=days)

        return {
            "status": "success",
            "user_id": user_id,
            "days": days,
            "total_entries": len(mood_history),
            "entries": mood_history
        }
    except Exception as e:
        logger.error(f"Error fetching mood history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/user/mood/stats")
async def get_mood_stats(
    days: int = 30,
    current_user = Depends(get_current_active_user)
):
    """
    Get mood statistics and insights for current user

    Requires: Active user authentication
    Security: Mood data is highly sensitive personal information
    NEW FEATURE: Analyze mood patterns! 📊
    """
    try:
        user_id = current_user.user_id
        stats = await memory_manager.get_mood_statistics(user_id, days=days)

        return {
            "status": "success",
            "user_id": user_id,
            "period_days": days,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error fetching mood stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/user/{user_id}/mood/entries")
async def add_mood_entry(user_id: str, mood_data: dict):
    """
    Add a new mood entry for user

    Body:
        {
            "mood": "happy|sad|anxious|calm|stressed|energetic|tired",
            "intensity": 1-10,
            "trigger": "Optional trigger description",
            "notes": "Optional notes"
        }

    Response:
        {
            "status": "success",
            "entry": {...},
            "message": "Mood entry saved"
        }
    """
    try:
        db = get_mongodb_service()

        # Create mood entry document
        entry = {
            "user_id": user_id,
            "mood": mood_data.get("mood"),
            "intensity": mood_data.get("intensity", 5),
            "trigger": mood_data.get("trigger"),
            "notes": mood_data.get("notes"),
            "timestamp": datetime.utcnow()
        }

        # Insert into database
        mood_collection = db.db["mood_entries"]
        result = await mood_collection.insert_one(entry)
        entry["_id"] = str(result.inserted_id)

        return {
            "status": "success",
            "entry": entry,
            "message": "Mood entry saved"
        }

    except Exception as e:
        logger.error(f"Add mood entry failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Alias endpoints for mood tracker (alternative paths)
@app.get("/api/v1/mood/{user_id}/entries")
async def get_mood_entries_alias(user_id: str, limit: int = 30):
    """
    Alias endpoint for mood entries.
    Redirects to /api/v1/user/{user_id}/mood/history
    """
    return await get_mood_history(user_id, days=limit)


@app.get("/api/v1/mood/{user_id}/stats")
async def get_mood_stats_alias(user_id: str):
    """
    Alias endpoint for mood stats.
    Redirects to /api/v1/user/{user_id}/mood/stats
    """
    return await get_mood_stats(user_id, days=30)


@app.post("/api/v1/mood/{user_id}/entries")
async def add_mood_entry_alias(user_id: str, mood_data: dict):
    """
    Alias endpoint for adding mood entry.
    Redirects to /api/v1/user/{user_id}/mood/entries
    """
    return await add_mood_entry(user_id, mood_data)


@app.get("/api/v1/db/health")
async def database_health():
    """Check MongoDB connection status"""
    try:
        db = get_mongodb_service()
        is_healthy = await db.health_check()

        if is_healthy:
            stats = await db.get_database_stats()
            return {
                "status": "healthy",
                "database": stats.get("database"),
                "collections": stats.get("collections"),
                "total_documents": stats.get("objects")
            }
        else:
            return {
                "status": "unhealthy",
                "message": "MongoDB connection failed"
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

# ============================================================================
# SEMANTIC SEARCH - ChromaDB-powered endpoints
# ============================================================================

@app.post("/api/v1/search/conversations")
async def search_conversations(user_id: str, query: str, n_results: int = 10):
    """
    Semantic search for conversations using ChromaDB.

    Example:
        POST /api/v1/search/conversations
        Body: {"user_id": "user_123", "query": "jak radzić sobie ze stresem?", "n_results": 5}

    Response:
        {
            "status": "success",
            "query": "jak radzić sobie ze stresem?",
            "total": 5,
            "results": [
                {
                    "content": "...",
                    "similarity": 0.92,
                    "metadata": {...}
                }
            ]
        }
    """
    try:
        results = await memory_manager.search_similar_conversations(
            user_id=user_id,
            query=query,
            n_results=n_results
        )

        return {
            "status": "success",
            "query": query,
            "user_id": user_id,
            "total": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/chromadb/health")
async def chromadb_health():
    """Check ChromaDB connection status and stats"""
    try:
        chromadb = get_chromadb_service()
        embedding_service = get_embedding_service()

        chromadb_status = await chromadb.health_check() if chromadb else False
        chromadb_stats = chromadb.get_stats() if chromadb else {}

        embedding_stats = embedding_service.get_cache_stats() if embedding_service else {}

        return {
            "chromadb": {
                "status": "healthy" if chromadb_status else "unavailable",
                **chromadb_stats
            },
            "embeddings": {
                "status": "available" if embedding_service else "unavailable",
                **embedding_stats
            }
        }

    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        return {
            "chromadb": {"status": "error", "message": str(e)},
            "embeddings": {"status": "unknown"}
        }


@app.post("/api/v1/embeddings/generate")
async def generate_embedding(text: str):
    """
    Generate embedding for text (utility endpoint for testing).

    Example:
        POST /api/v1/embeddings/generate
        Body: {"text": "Hello world"}

    Response:
        {
            "status": "success",
            "text": "Hello world",
            "embedding": [0.123, -0.456, ...],  # 1536 dimensions
            "dimensions": 1536
        }
    """
    try:
        embedding_service = get_embedding_service()
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not available")

        embedding = await embedding_service.generate(text)

        return {
            "status": "success",
            "text": text,
            "embedding": embedding,
            "dimensions": len(embedding)
        }

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALYTICS - Advanced Conversation Analysis
# ============================================================================

@app.post("/api/v1/analytics/conversation/{conversation_id}/summary")
async def summarize_conversation(conversation_id: str, max_length: int = 200):
    """
    Generate automatic conversation summary using LLM.

    Example:
        POST /api/v1/analytics/conversation/conv_123/summary?max_length=150

    Response:
        {
            "status": "success",
            "conversation_id": "conv_123",
            "summary": {
                "summary": "Użytkownik rozmawiał o stresie w pracy...",
                "key_topics": ["praca", "stres", "zarządzanie czasem"],
                "sentiment": "neutral",
                "action_items": ["Spróbuj techniki oddechowej..."],
                "insights": ["Wzrost stresu w ostatnich dniach"]
            }
        }
    """
    try:
        analytics = get_analytics_service()
        if not analytics:
            raise HTTPException(status_code=503, detail="Analytics service not available")

        summary = await analytics.summarize_conversation(
            conversation_id=conversation_id,
            max_length=max_length
        )

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Conversation summarization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/user/{user_id}/clusters")
async def get_topic_clusters(user_id: str, n_clusters: int = 5, min_conversations: int = 3):
    """
    Group user's conversations by topics using K-means clustering.

    Example:
        GET /api/v1/analytics/user/user_123/clusters?n_clusters=5

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "total_clusters": 3,
            "clusters": [
                {
                    "cluster_id": 0,
                    "label": "Praca i kariera",
                    "size": 12,
                    "sample_topics": ["rozmowa kwalifikacyjna", "zarządzanie czasem"]
                },
                ...
            ]
        }
    """
    try:
        analytics = get_analytics_service()
        if not analytics:
            raise HTTPException(status_code=503, detail="Analytics service not available")

        clusters = await analytics.cluster_conversations_by_topic(
            user_id=user_id,
            n_clusters=n_clusters,
            min_conversations=min_conversations
        )

        return {
            "status": "success",
            "user_id": user_id,
            "total_clusters": len(clusters["clusters"]),
            "clusters": clusters["clusters"]
        }

    except Exception as e:
        logger.error(f"Topic clustering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/user/{user_id}/trends")
async def get_mood_trends(user_id: str, days: int = 30):
    """
    Analyze mood trends over time with statistical analysis.

    Example:
        GET /api/v1/analytics/user/user_123/trends?days=30

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "period": "30 days",
            "trends": {
                "trend": "improving",  # improving/declining/stable
                "slope": 0.15,
                "statistics": {
                    "average_intensity": 7.2,
                    "volatility": "moderate",
                    "most_common_mood": "happy"
                },
                "data_points": [...],
                "insights": ["Mood improving over last 2 weeks", ...]
            }
        }
    """
    try:
        analytics = get_analytics_service()
        if not analytics:
            raise HTTPException(status_code=503, detail="Analytics service not available")

        trends = await analytics.analyze_mood_trends(
            user_id=user_id,
            days=days
        )

        return {
            "status": "success",
            "user_id": user_id,
            "period": f"{days} days",
            "trends": trends
        }

    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/user/{user_id}/recommendations")
async def get_recommendations(user_id: str, n_recommendations: int = 5):
    """
    Get personalized recommendations based on conversation patterns.

    Example:
        GET /api/v1/analytics/user/user_123/recommendations?n_recommendations=5

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "total": 5,
            "recommendations": [
                {
                    "type": "topic",
                    "title": "Eksploruj techniki mindfulness",
                    "description": "Na podstawie twoich rozmów o stresie...",
                    "confidence": 0.85,
                    "source": "topic_clustering"
                },
                {
                    "type": "mood",
                    "title": "Rozważ regularne ćwiczenia",
                    "description": "Twój nastrój poprawia się w dni, gdy wspominasz o aktywności",
                    "confidence": 0.72,
                    "source": "mood_trends"
                },
                ...
            ]
        }
    """
    try:
        analytics = get_analytics_service()
        if not analytics:
            raise HTTPException(status_code=503, detail="Analytics service not available")

        recommendations = await analytics.get_recommendations(
            user_id=user_id,
            n_recommendations=n_recommendations
        )

        return {
            "status": "success",
            "user_id": user_id,
            "total": len(recommendations["recommendations"]),
            "recommendations": recommendations["recommendations"]
        }

    except Exception as e:
        logger.error(f"Recommendations generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/health")
async def analytics_health():
    """Check Analytics Service status and dependencies"""
    try:
        analytics = get_analytics_service()

        if not analytics:
            return {
                "status": "unavailable",
                "message": "Analytics service not initialized (requires ChromaDB + Embeddings)"
            }

        # Check all dependencies
        chromadb_ok = await analytics.chromadb.health_check() if analytics.chromadb else False
        embedding_ok = analytics.embeddings is not None

        return {
            "status": "healthy" if (chromadb_ok and embedding_ok) else "degraded",
            "dependencies": {
                "chromadb": "healthy" if chromadb_ok else "unavailable",
                "embeddings": "available" if embedding_ok else "unavailable",
                "llm_engine": "available" if analytics.llm else "unavailable",
                "memory_manager": "available" if analytics.memory else "unavailable"
            },
            "features": {
                "summarization": analytics.llm is not None,
                "clustering": chromadb_ok and embedding_ok,
                "trends": True,  # Only needs MongoDB
                "recommendations": chromadb_ok and embedding_ok
            }
        }

    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# FILE UPLOAD - Image and Audio Processing
# ============================================================================

@app.post("/api/v1/upload/image")
async def upload_image(
    user_id: str = Form(...),
    message: str = Form(""),
    file: UploadFile = File(...)
):
    """
    Upload and process image with Vision Agent.

    Supports OCR, object detection, scene description.

    Example:
        POST /api/v1/upload/image
        Form data:
            - user_id: "user_123"
            - message: "Co jest na tym zdjęciu?"
            - file: image.jpg

    Response:
        {
            "status": "success",
            "response": "🔍 **Analiza obrazu:**\n\n...",
            "agent": "Vision"
        }
    """
    try:
        # Validate file type
        content_type = file.content_type
        if not content_type or not content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image data
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Add data URL prefix
        mime_type = content_type
        image_data = f"data:{mime_type};base64,{image_base64}"

        # Process with orchestrator
        response = await orchestrator.process_message(
            user_id=user_id,
            message=message or "Przeanalizuj to zdjęcie",
            message_type="image",
            metadata={
                "image": image_data,
                "filename": file.filename,
                "content_type": content_type
            }
        )

        return {
            "status": "success",
            "response": response["content"],
            "agent": response.get("agent", "unknown"),
            "metadata": response.get("metadata", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/upload/audio")
async def upload_audio(
    user_id: str = Form(...),
    message: str = Form(""),
    language: str = Form("pl"),
    file: UploadFile = File(...)
):
    """
    Upload and transcribe audio with Speech Agent.

    Supports multiple audio formats (mp3, wav, m4a, webm, etc.)

    Example:
        POST /api/v1/upload/audio
        Form data:
            - user_id: "user_123"
            - message: "Przetranskrybuj to nagranie"
            - language: "pl"
            - file: recording.mp3

    Response:
        {
            "status": "success",
            "response": "🎤 **Transkrypcja:**\n\n...",
            "agent": "Speech",
            "transcription": "..."
        }
    """
    try:
        # Validate file type
        content_type = file.content_type
        if not content_type or not content_type.startswith('audio/'):
            # Also accept video formats (some browsers send audio as video/webm)
            if not content_type.startswith('video/'):
                raise HTTPException(status_code=400, detail="File must be audio")

        # Read audio data
        audio_bytes = await file.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        # Get file extension
        filename = file.filename or "audio.mp3"
        audio_format = filename.split('.')[-1].lower()

        # Process with orchestrator
        response = await orchestrator.process_message(
            user_id=user_id,
            message=message or "Transkrybuj to nagranie",
            message_type="audio",
            metadata={
                "audio": audio_base64,
                "audio_format": audio_format,
                "filename": filename,
                "language": language,
                "content_type": content_type
            }
        )

        return {
            "status": "success",
            "response": response["content"],
            "agent": response.get("agent", "unknown"),
            "metadata": response.get("metadata", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tts")
async def text_to_speech(
    user_id: str,
    text: str,
    voice: str = "alloy",
    model: str = "tts-1"
):
    """
    Convert text to speech using OpenAI TTS.

    Available voices: alloy, echo, fable, onyx, nova, shimmer
    Models: tts-1 (fast), tts-1-hd (high quality)

    Example:
        POST /api/v1/tts
        Body: {
            "user_id": "user_123",
            "text": "Witaj w LumenAI!",
            "voice": "alloy",
            "model": "tts-1"
        }

    Response:
        {
            "status": "success",
            "audio_base64": "...",
            "audio_format": "mp3",
            "voice": "alloy"
        }
    """
    try:
        # Process with orchestrator (Speech Agent will handle TTS)
        response = await orchestrator.process_message(
            user_id=user_id,
            message=f"Przeczytaj: {text}",
            message_type="tts",
            metadata={
                "voice": voice,
                "tts_model": model
            }
        )

        # Check if response contains audio
        if isinstance(response.get("content"), dict) and "audio_base64" in response["content"]:
            return {
                "status": "success",
                **response["content"]
            }

        return {
            "status": "success",
            "message": response.get("content", "TTS generation completed")
        }

    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FINANCE - Budget and Expense Tracking
# ============================================================================

@app.post("/api/v1/finance/expense")
async def add_expense(
    user_id: str,
    amount: float,
    category: str,
    description: str = "",
    date: Optional[str] = None
):
    """
    Add expense entry for user.

    Example:
        POST /api/v1/finance/expense
        Body: {
            "user_id": "user_123",
            "amount": 45.50,
            "category": "jedzenie",
            "description": "Lunch w restauracji",
            "date": "2025-12-03"
        }

    Response:
        {
            "status": "success",
            "expense_id": "exp_123",
            "message": "Expense added successfully"
        }
    """
    try:
        expense_data = {
            "amount": amount,
            "category": category,
            "description": description,
            "date": date or datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }

        # Store in user context (in production, would be separate expenses collection)
        if memory_manager:
            await memory_manager.store_user_context(
                user_id=user_id,
                context_type="expense",
                key=f"expense_{datetime.utcnow().timestamp()}",
                value=expense_data,
                source="finance_api"
            )

        return {
            "status": "success",
            "expense_id": f"exp_{int(datetime.utcnow().timestamp())}",
            "expense": expense_data,
            "message": "💰 Wydatek dodany pomyślnie!"
        }

    except Exception as e:
        logger.error(f"Add expense failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/finance/expenses/{user_id}")
async def get_expenses(
    user_id: str,
    days: int = 30,
    category: Optional[str] = None
):
    """
    Get user's expenses for specified period.

    Example:
        GET /api/v1/finance/expenses/user_123?days=7&category=jedzenie

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "period_days": 7,
            "total_expenses": 345.50,
            "expenses": [...],
            "by_category": {...}
        }
    """
    try:
        # In production, fetch from expenses collection
        # For now, return helpful structure

        return {
            "status": "success",
            "user_id": user_id,
            "period_days": days,
            "category_filter": category,
            "total_expenses": 0.0,
            "expenses": [],
            "by_category": {},
            "message": "Zacznij dodawać wydatki, aby zobaczyć statystyki!"
        }

    except Exception as e:
        logger.error(f"Get expenses failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/finance/budget/{user_id}")
async def get_budget(user_id: str):
    """
    Get user's budget overview and spending statistics.

    Example:
        GET /api/v1/finance/budget/user_123

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "monthly_budget": 3000.0,
            "spent_this_month": 1234.56,
            "remaining": 1765.44,
            "top_categories": [...]
        }
    """
    try:
        # In production, calculate from actual expenses
        return {
            "status": "success",
            "user_id": user_id,
            "monthly_budget": None,
            "spent_this_month": 0.0,
            "remaining": None,
            "top_categories": [],
            "message": "Ustaw budżet miesięczny, aby śledzić wydatki!"
        }

    except Exception as e:
        logger.error(f"Get budget failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/finance/budget/{user_id}")
async def set_budget(user_id: str, monthly_amount: float):
    """
    Set monthly budget for user.

    Example:
        POST /api/v1/finance/budget/user_123
        Body: {"monthly_amount": 3000.0}

    Response:
        {
            "status": "success",
            "message": "Budget set to 3000 PLN/month"
        }
    """
    try:
        if memory_manager:
            await memory_manager.store_user_context(
                user_id=user_id,
                context_type="budget",
                key="monthly_budget",
                value=monthly_amount,
                source="finance_api"
            )

        return {
            "status": "success",
            "user_id": user_id,
            "monthly_budget": monthly_amount,
            "message": f"💰 Budżet ustawiony: {monthly_amount} PLN/miesiąc"
        }

    except Exception as e:
        logger.error(f"Set budget failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/finance/expenses/{user_id}/{expense_id}")
async def delete_expense(user_id: str, expense_id: str):
    """
    Delete an expense entry.

    Response:
        {
            "status": "success",
            "message": "Expense deleted successfully"
        }
    """
    try:
        db = get_mongodb_service()
        expenses_collection = db.db["finance_expenses"]

        # Delete expense
        result = await expenses_collection.delete_one(
            {"expense_id": expense_id, "user_id": user_id}
        )

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Expense not found")

        return {
            "status": "success",
            "message": "Expense deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete expense failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Alias endpoints for finance (alternative paths matching frontend expectations)
@app.get("/api/v1/finance/{user_id}/expenses")
async def get_expenses_alias(user_id: str, days: int = 30, category: Optional[str] = None):
    """
    Alias endpoint for expenses.
    Redirects to /api/v1/finance/expenses/{user_id}
    """
    return await get_expenses(user_id, days=days, category=category)


@app.post("/api/v1/finance/{user_id}/expenses")
async def add_expense_alias(user_id: str, expense_data: dict):
    """
    Alias endpoint for adding expense.
    Accepts expense data in request body.
    """
    return await add_expense(
        user_id=user_id,
        amount=expense_data.get("amount"),
        category=expense_data.get("category"),
        description=expense_data.get("description", ""),
        date=expense_data.get("date")
    )


@app.delete("/api/v1/finance/{user_id}/expenses/{expense_id}")
async def delete_expense_alias(user_id: str, expense_id: str):
    """
    Alias endpoint for deleting expense.
    Redirects to /api/v1/finance/expenses/{user_id}/{expense_id}
    """
    return await delete_expense(user_id, expense_id)


@app.get("/api/v1/finance/{user_id}/budgets")
async def get_budgets_alias(user_id: str):
    """
    Alias endpoint for budget (plural form).
    Redirects to /api/v1/finance/budget/{user_id}
    """
    return await get_budget(user_id)


@app.get("/api/v1/finance/{user_id}/stats")
async def get_finance_stats(user_id: str, days: int = 30):
    """
    Get financial statistics for user.

    Returns:
        - Total expenses
        - Average daily spending
        - Top spending categories
        - Budget status

    Response:
        {
            "status": "success",
            "total_expenses": 1234.56,
            "average_daily": 41.15,
            "top_categories": [...],
            "budget_status": {...}
        }
    """
    try:
        # Get expenses and budget
        expenses_response = await get_expenses(user_id, days=days)
        budget_response = await get_budget(user_id)

        total_expenses = expenses_response.get("total_expenses", 0.0)
        monthly_budget = budget_response.get("monthly_budget")

        # Calculate stats
        average_daily = total_expenses / days if days > 0 else 0.0

        budget_status = None
        if monthly_budget:
            spent_percent = (total_expenses / monthly_budget * 100) if monthly_budget > 0 else 0
            budget_status = {
                "monthly_budget": monthly_budget,
                "spent": total_expenses,
                "remaining": monthly_budget - total_expenses,
                "spent_percent": round(spent_percent, 2)
            }

        return {
            "status": "success",
            "user_id": user_id,
            "period_days": days,
            "total_expenses": round(total_expenses, 2),
            "average_daily": round(average_daily, 2),
            "top_categories": expenses_response.get("by_category", {}),
            "budget_status": budget_status
        }

    except Exception as e:
        logger.error(f"Get finance stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PLANNER - Task Management and Calendar
# ============================================================================

@app.get("/api/v1/planner/{user_id}/tasks")
async def get_user_tasks(user_id: str):
    """
    Get all tasks for a user.

    Returns list of tasks with their status, priority, and due dates.

    Example:
        GET /api/v1/planner/user_123/tasks

    Response:
        {
            "status": "success",
            "tasks": [
                {
                    "task_id": "task_123",
                    "title": "Complete report",
                    "description": "Finish quarterly report",
                    "priority": "high",
                    "status": "in_progress",
                    "due_date": "2025-12-10T17:00:00",
                    "category": "work",
                    "created_at": "2025-12-05T10:00:00",
                    "updated_at": "2025-12-05T10:00:00"
                }
            ]
        }
    """
    try:
        db = get_mongodb_service()

        # Get tasks from database
        tasks_collection = db.db["planner_tasks"]
        tasks_cursor = tasks_collection.find({"user_id": user_id}).sort("created_at", -1)
        tasks = []

        async for task in tasks_cursor:
            task["_id"] = str(task["_id"])
            tasks.append(task)

        return {
            "status": "success",
            "tasks": tasks
        }

    except Exception as e:
        logger.error(f"Get tasks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/planner/{user_id}/tasks")
async def create_task(user_id: str, task_data: dict):
    """
    Create a new task for user.

    Body:
        {
            "title": "Task title",
            "description": "Task description",
            "priority": "high|medium|low",
            "due_date": "2025-12-10T17:00:00",
            "category": "work"
        }

    Response:
        {
            "status": "success",
            "task": {...},
            "message": "Task created successfully"
        }
    """
    try:
        db = get_mongodb_service()

        # Create task document
        task_id = f"task_{user_id}_{datetime.utcnow().timestamp()}"
        task = {
            "task_id": task_id,
            "user_id": user_id,
            "title": task_data.get("title"),
            "description": task_data.get("description"),
            "priority": task_data.get("priority", "medium"),
            "status": "pending",
            "due_date": task_data.get("due_date"),
            "category": task_data.get("category"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None
        }

        # Insert into database
        tasks_collection = db.db["planner_tasks"]
        await tasks_collection.insert_one(task)

        task["_id"] = str(task["_id"])

        return {
            "status": "success",
            "task": task,
            "message": "Task created successfully"
        }

    except Exception as e:
        logger.error(f"Create task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/planner/{user_id}/tasks/{task_id}")
async def update_task(user_id: str, task_id: str, task_data: dict):
    """
    Update an existing task.

    Body can contain any of:
        {
            "title": "Updated title",
            "description": "Updated description",
            "priority": "high|medium|low",
            "status": "pending|in_progress|completed",
            "due_date": "2025-12-10T17:00:00",
            "category": "work"
        }

    Response:
        {
            "status": "success",
            "task": {...},
            "message": "Task updated successfully"
        }
    """
    try:
        db = get_mongodb_service()
        tasks_collection = db.db["planner_tasks"]

        # Prepare update data
        update_data = {
            "updated_at": datetime.utcnow()
        }

        # Add fields that are present in request
        if "title" in task_data:
            update_data["title"] = task_data["title"]
        if "description" in task_data:
            update_data["description"] = task_data["description"]
        if "priority" in task_data:
            update_data["priority"] = task_data["priority"]
        if "status" in task_data:
            update_data["status"] = task_data["status"]
            # If status is completed, set completed_at
            if task_data["status"] == "completed":
                update_data["completed_at"] = datetime.utcnow()
        if "due_date" in task_data:
            update_data["due_date"] = task_data["due_date"]
        if "category" in task_data:
            update_data["category"] = task_data["category"]

        # Update task
        result = await tasks_collection.update_one(
            {"task_id": task_id, "user_id": user_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get updated task
        updated_task = await tasks_collection.find_one({"task_id": task_id})
        updated_task["_id"] = str(updated_task["_id"])

        return {
            "status": "success",
            "task": updated_task,
            "message": "Task updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/planner/{user_id}/tasks/{task_id}")
async def delete_task(user_id: str, task_id: str):
    """
    Delete a task.

    Response:
        {
            "status": "success",
            "message": "Task deleted successfully"
        }
    """
    try:
        db = get_mongodb_service()
        tasks_collection = db.db["planner_tasks"]

        # Delete task
        result = await tasks_collection.delete_one(
            {"task_id": task_id, "user_id": user_id}
        )

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "status": "success",
            "message": "Task deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/planner/{user_id}/calendar/events")
async def get_calendar_events(user_id: str):
    """
    Get all calendar events for a user.

    Returns list of calendar events.

    Response:
        {
            "status": "success",
            "events": [
                {
                    "event_id": "event_123",
                    "title": "Team Meeting",
                    "description": "Weekly sync",
                    "start_time": "2025-12-06T10:00:00",
                    "end_time": "2025-12-06T11:00:00",
                    "location": "Conference Room A",
                    "color": "#3b82f6"
                }
            ]
        }
    """
    try:
        db = get_mongodb_service()

        # Get events from database
        events_collection = db.db["planner_calendar_events"]
        events_cursor = events_collection.find({"user_id": user_id}).sort("start_time", 1)
        events = []

        async for event in events_cursor:
            event["_id"] = str(event["_id"])
            events.append(event)

        return {
            "status": "success",
            "events": events
        }

    except Exception as e:
        logger.error(f"Get calendar events failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/planner/{user_id}/calendar/sync")
async def sync_google_calendar(user_id: str):
    """
    Sync with Google Calendar.

    This is a placeholder for future Google Calendar integration.
    Currently returns a mock success response.

    Response:
        {
            "status": "success",
            "message": "Calendar synced successfully",
            "events_synced": 0
        }
    """
    try:
        # TODO: Implement Google Calendar sync
        # For now, return success message
        return {
            "status": "success",
            "message": "Calendar sync feature coming soon",
            "events_synced": 0
        }

    except Exception as e:
        logger.error(f"Calendar sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DASHBOARD - Analytics and Visualization Data
# ============================================================================

@app.get("/api/v1/dashboard/stats/{user_id}")
async def get_dashboard_stats(user_id: str):
    """
    Get overall dashboard statistics for user.

    Returns key metrics for dashboard overview.

    Example:
        GET /api/v1/dashboard/stats/user_123

    Response:
        {
            "status": "success",
            "stats": {
                "total_conversations": 45,
                "total_messages": 342,
                "current_mood": "happy",
                "mood_trend": "improving",
                "total_expenses": 2340.50,
                "budget_used_percent": 78
            }
        }
    """
    try:
        db = get_mongodb_service()

        # Get conversation count
        conversations = await db.get_user_conversations(user_id, limit=1000)
        total_conversations = len(conversations)

        # Calculate total messages
        total_messages = sum(conv.message_count for conv in conversations)

        # Get mood stats
        mood_stats = await memory_manager.get_mood_statistics(user_id, days=7) if memory_manager else {}

        stats = {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "active_agents": 7,
            "current_mood": mood_stats.get("average_mood", "neutral"),
            "mood_trend": mood_stats.get("trend", "stable"),
            "total_expenses": 0.0,  # Would be calculated from expenses
            "budget_used_percent": 0,
            "messages_this_week": total_messages,  # Simplified
        }

        return {
            "status": "success",
            "user_id": user_id,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Get dashboard stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboard/expenses-chart/{user_id}")
async def get_expenses_chart_data(user_id: str, days: int = 30):
    """
    Get expense data formatted for charts.

    Returns both timeline data and category breakdown.

    Example:
        GET /api/v1/dashboard/expenses-chart/user_123?days=30

    Response:
        {
            "status": "success",
            "timeline": [
                {"date": "2025-12-01", "amount": 120.5},
                {"date": "2025-12-02", "amount": 85.0},
                ...
            ],
            "by_category": [
                {"category": "jedzenie", "amount": 450.0, "percentage": 35},
                {"category": "transport", "amount": 280.0, "percentage": 22},
                ...
            ],
            "total": 1280.0
        }
    """
    try:
        # In production, fetch from expenses collection
        # For now, return sample data structure

        from datetime import datetime, timedelta

        # Generate sample timeline data
        timeline = []
        base_date = datetime.now() - timedelta(days=days)
        for i in range(days):
            date = base_date + timedelta(days=i)
            timeline.append({
                "date": date.strftime("%Y-%m-%d"),
                "amount": 0.0  # Would be actual expenses
            })

        # Sample category data
        by_category = [
            {"category": "jedzenie", "amount": 0.0, "percentage": 0, "color": "#10b981"},
            {"category": "transport", "amount": 0.0, "percentage": 0, "color": "#3b82f6"},
            {"category": "dom", "amount": 0.0, "percentage": 0, "color": "#8b5cf6"},
            {"category": "rozrywka", "amount": 0.0, "percentage": 0, "color": "#f59e0b"},
            {"category": "zdrowie", "amount": 0.0, "percentage": 0, "color": "#ef4444"},
            {"category": "ubrania", "amount": 0.0, "percentage": 0, "color": "#ec4899"},
            {"category": "edukacja", "amount": 0.0, "percentage": 0, "color": "#14b8a6"},
            {"category": "inne", "amount": 0.0, "percentage": 0, "color": "#6b7280"},
        ]

        return {
            "status": "success",
            "user_id": user_id,
            "period_days": days,
            "timeline": timeline,
            "by_category": by_category,
            "total": 0.0,
            "message": "Zacznij dodawać wydatki, aby zobaczyć wykresy!"
        }

    except Exception as e:
        logger.error(f"Get expenses chart failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboard/mood-chart/{user_id}")
async def get_mood_chart_data(user_id: str, days: int = 30):
    """
    Get mood data formatted for timeline chart.

    Example:
        GET /api/v1/dashboard/mood-chart/user_123?days=30

    Response:
        {
            "status": "success",
            "data": [
                {
                    "date": "2025-12-01",
                    "mood": "happy",
                    "intensity": 7,
                    "activities": ["work", "exercise"]
                },
                ...
            ],
            "average_intensity": 6.5,
            "most_common_mood": "happy",
            "trend": "improving"
        }
    """
    try:
        # Get mood history from memory manager
        mood_history = []
        if memory_manager:
            mood_history = await memory_manager.get_mood_history(user_id, days=days)

        # Format for chart
        chart_data = []
        total_intensity = 0
        mood_counts = {}

        for entry in mood_history:
            intensity = entry.get("intensity", 5)
            mood = entry.get("mood", "neutral")

            chart_data.append({
                "date": entry.get("date", ""),
                "mood": mood,
                "intensity": intensity,
                "trigger": entry.get("trigger", ""),
            })

            total_intensity += intensity
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

        # Calculate stats
        avg_intensity = total_intensity / len(chart_data) if chart_data else 5.0
        most_common_mood = max(mood_counts.items(), key=lambda x: x[1])[0] if mood_counts else "neutral"

        # Simple trend calculation
        if len(chart_data) >= 2:
            first_half_avg = sum(d["intensity"] for d in chart_data[:len(chart_data)//2]) / (len(chart_data)//2)
            second_half_avg = sum(d["intensity"] for d in chart_data[len(chart_data)//2:]) / (len(chart_data) - len(chart_data)//2)

            if second_half_avg > first_half_avg + 0.5:
                trend = "improving"
            elif second_half_avg < first_half_avg - 0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "status": "success",
            "user_id": user_id,
            "period_days": days,
            "data": chart_data,
            "average_intensity": round(avg_intensity, 1),
            "most_common_mood": most_common_mood,
            "trend": trend,
            "total_entries": len(chart_data)
        }

    except Exception as e:
        logger.error(f"Get mood chart failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MACHINE LEARNING - Personalized ML Models
# ============================================================================

@app.post("/api/v1/ml/train/mood-predictor/{user_id}")
async def train_mood_predictor(user_id: str, min_samples: int = 50):
    """
    Trenuje personalizowany model przewidywania nastroju dla użytkownika.

    Model uczy się na historycznych danych użytkownika i potrafi przewidzieć
    przyszły nastrój na podstawie kontekstu rozmowy.

    Example:
        POST /api/v1/ml/train/mood-predictor/user_123?min_samples=50

    Response:
        {
            "success": true,
            "model_type": "mood_predictor",
            "user_id": "user_123",
            "n_samples": 150,
            "metrics": {
                "test_rmse": 1.23,
                "test_mae": 0.98
            },
            "top_features": [...]
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        result = await training.train_mood_predictor(
            user_id=user_id,
            min_samples=min_samples
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Training failed"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mood predictor training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ml/train/behavior-profiler/{user_id}")
async def train_behavior_profiler(user_id: str, min_samples: int = 50):
    """
    Trenuje personalizowany model profilowania zachowań użytkownika.

    Model klasyfikuje zachowania użytkownika (positive/neutral/negative)
    na podstawie wzorców w danych historycznych.

    Example:
        POST /api/v1/ml/train/behavior-profiler/user_123?min_samples=50

    Response:
        {
            "success": true,
            "model_type": "behavior_profiler",
            "user_id": "user_123",
            "n_samples": 150,
            "metrics": {
                "test_accuracy": 0.85,
                "test_f1": 0.82
            },
            "class_distribution": {...}
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        result = await training.train_behavior_profiler(
            user_id=user_id,
            min_samples=min_samples
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Training failed"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Behavior profiler training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ml/predict/mood")
async def predict_mood(user_id: str, message: str):
    """
    Przewiduje nastrój użytkownika na podstawie aktualnego kontekstu.

    Wymaga wcześniej wytrenowanego modelu dla tego użytkownika.

    Example:
        POST /api/v1/ml/predict/mood
        Body: {"user_id": "user_123", "message": "Czuję się dzisiaj świetnie!"}

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "prediction": {
                "predicted_mood": 8.2,
                "confidence": 0.75,
                "timestamp": "2025-12-03T12:00:00"
            }
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        prediction = await training.predict_mood(user_id=user_id, message=message)

        if prediction is None:
            raise HTTPException(
                status_code=404,
                detail=f"No trained mood predictor model found for user {user_id}. Please train first."
            )

        return {
            "status": "success",
            "user_id": user_id,
            "prediction": prediction
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mood prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ml/predict/behavior")
async def predict_behavior(user_id: str, message: str):
    """
    Klasyfikuje zachowanie użytkownika (positive/neutral/negative).

    Wymaga wcześniej wytrenowanego modelu dla tego użytkownika.

    Example:
        POST /api/v1/ml/predict/behavior
        Body: {"user_id": "user_123", "message": "Mam problem z pracą"}

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "prediction": {
                "predicted_class": "negative",
                "probabilities": {
                    "positive": 0.15,
                    "neutral": 0.25,
                    "negative": 0.60
                },
                "timestamp": "2025-12-03T12:00:00"
            }
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        prediction = await training.predict_behavior(user_id=user_id, message=message)

        if prediction is None:
            raise HTTPException(
                status_code=404,
                detail=f"No trained behavior profiler model found for user {user_id}. Please train first."
            )

        return {
            "status": "success",
            "user_id": user_id,
            "prediction": prediction
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Behavior prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ml/model/{user_id}/info")
async def get_model_info(user_id: str, model_type: str = "mood_predictor"):
    """
    Zwraca informacje o wytrenowanym modelu użytkownika.

    Args:
        user_id: ID użytkownika
        model_type: Typ modelu (mood_predictor lub behavior_profiler)

    Example:
        GET /api/v1/ml/model/user_123/info?model_type=mood_predictor

    Response:
        {
            "status": "success",
            "model_info": {
                "model_type": "mood_predictor",
                "trained_at": "2025-12-03T12:00:00",
                "n_samples": 150,
                "metrics": {...}
            }
        }
    """
    try:
        training = get_training_service()
        if not training:
            raise HTTPException(status_code=503, detail="ML Training Service not available")

        info = training.get_model_info(user_id, model_type)

        if info is None:
            raise HTTPException(
                status_code=404,
                detail=f"No {model_type} model found for user {user_id}"
            )

        return {
            "status": "success",
            "model_info": info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get model info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ml/health")
async def ml_health():
    """Check ML Services status"""
    try:
        training = get_training_service()
        feature_eng = feature_engineer

        return {
            "status": "healthy" if (training and feature_eng) else "unavailable",
            "services": {
                "feature_engineer": "available" if feature_eng else "unavailable",
                "training_service": "available" if training else "unavailable"
            },
            "capabilities": {
                "mood_prediction": training is not None,
                "behavior_profiling": training is not None,
                "feature_extraction": feature_eng is not None
            }
        }

    except Exception as e:
        logger.error(f"ML health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# NOTIFICATIONS - Real-time Smart Notifications
# ============================================================================

@app.get("/api/v1/notifications/{user_id}")
async def get_user_notifications(user_id: str, unread_only: bool = False, limit: int = 50):
    """
    Pobiera powiadomienia użytkownika.

    Example:
        GET /api/v1/notifications/user_123?unread_only=true&limit=20

    Response:
        {
            "status": "success",
            "user_id": "user_123",
            "total": 15,
            "notifications": [
                {
                    "notification_id": "mood_drop_user_123_...",
                    "type": "mood_drop",
                    "priority": "high",
                    "title": "Zauważyłem spadek nastroju",
                    "message": "...",
                    "created_at": "2025-12-03T12:00:00",
                    "read": false
                },
                ...
            ]
        }
    """
    try:
        notif_service = get_notification_service()
        if not notif_service:
            raise HTTPException(status_code=503, detail="Notification service not available")

        notifications = await notif_service.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit
        )

        return {
            "status": "success",
            "user_id": user_id,
            "total": len(notifications),
            "notifications": notifications
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get notifications failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """
    Oznacza powiadomienie jako przeczytane.

    Example:
        POST /api/v1/notifications/mood_drop_user_123_.../read

    Response:
        {
            "status": "success",
            "notification_id": "mood_drop_user_123_...",
            "read": true
        }
    """
    try:
        notif_service = get_notification_service()
        if not notif_service:
            raise HTTPException(status_code=503, detail="Notification service not available")

        success = await notif_service.mark_as_read(notification_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found")

        return {
            "status": "success",
            "notification_id": notification_id,
            "read": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark notification read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/notifications/generate/daily-summary/{user_id}")
async def generate_daily_summary(user_id: str):
    """
    Generuje codzienne podsumowanie dla użytkownika.

    Example:
        POST /api/v1/notifications/generate/daily-summary/user_123

    Response:
        {
            "status": "success",
            "notification": {
                "type": "daily_summary",
                "title": "Twoje podsumowanie dnia",
                "message": "..."
            }
        }
    """
    try:
        notif_service = get_notification_service()
        if not notif_service:
            raise HTTPException(status_code=503, detail="Notification service not available")

        notification = await notif_service.generate_daily_summary(user_id)

        if not notification:
            raise HTTPException(status_code=500, detail="Failed to generate daily summary")

        return {
            "status": "success",
            "notification": notification.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate daily summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/notifications/generate/weekly-summary/{user_id}")
async def generate_weekly_summary(user_id: str):
    """
    Generuje tygodniowe podsumowanie dla użytkownika.

    Example:
        POST /api/v1/notifications/generate/weekly-summary/user_123

    Response:
        {
            "status": "success",
            "notification": {
                "type": "weekly_summary",
                "title": "Twoje podsumowanie tygodnia",
                "message": "..."
            }
        }
    """
    try:
        notif_service = get_notification_service()
        if not notif_service:
            raise HTTPException(status_code=503, detail="Notification service not available")

        notification = await notif_service.generate_weekly_summary(user_id)

        if not notification:
            raise HTTPException(status_code=500, detail="Failed to generate weekly summary")

        return {
            "status": "success",
            "notification": notification.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate weekly summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/notifications/health")
async def notifications_health():
    """Check Notification Service status"""
    try:
        notif_service = get_notification_service()

        if not notif_service:
            return {
                "status": "unavailable",
                "message": "Notification service not initialized"
            }

        return {
            "status": "healthy",
            "services": {
                "memory_manager": "available" if notif_service.memory else "unavailable",
                "ml_service": "available" if notif_service.ml_service else "unavailable",
                "analytics_service": "available" if notif_service.analytics else "unavailable"
            },
            "capabilities": {
                "mood_detection": True,
                "pattern_detection": True,
                "ml_predictions": notif_service.ml_service is not None,
                "summaries": True,
                "real_time_push": True
            }
        }

    except Exception as e:
        logger.error(f"Notification health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

