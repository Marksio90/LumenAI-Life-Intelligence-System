"""
User Repository - MongoDB User Operations
Handles all database operations for user management
"""

from typing import Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from loguru import logger

from models.user import UserInDB, UserCreate, UserUpdate, UserPublic
from services.auth_service import get_auth_service


class UserRepository:
    """
    Repository for user database operations.

    Manages user CRUD operations in MongoDB with proper indexing and validation.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize user repository.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db["users"]
        self.auth_service = get_auth_service()

    async def ensure_indexes(self):
        """Create database indexes for efficient queries."""
        try:
            # Unique index on email
            await self.collection.create_index("email", unique=True)

            # Unique index on username
            await self.collection.create_index("username", unique=True)

            # Index on user_id for fast lookups
            await self.collection.create_index("user_id", unique=True)

            # Compound index for active users
            await self.collection.create_index([("is_active", 1), ("created_at", -1)])

            logger.info("✅ User collection indexes created")

        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    # ============================================================================
    # CREATE OPERATIONS
    # ============================================================================

    async def create_user(self, user_create: UserCreate) -> Optional[UserInDB]:
        """
        Create a new user.

        Args:
            user_create: User registration data

        Returns:
            Created user or None if email/username exists

        Raises:
            ValueError: If user already exists
        """
        try:
            # Check if email already exists
            existing_email = await self.collection.find_one({"email": user_create.email})
            if existing_email:
                raise ValueError(f"User with email {user_create.email} already exists")

            # Check if username already exists
            existing_username = await self.collection.find_one({"username": user_create.username})
            if existing_username:
                raise ValueError(f"Username {user_create.username} already taken")

            # Create user object
            user_in_db = self.auth_service.create_user_from_registration(user_create)

            # Insert into database
            result = await self.collection.insert_one(user_in_db.model_dump())

            if result.inserted_id:
                logger.info(f"✅ User created: {user_in_db.email} ({user_in_db.user_id})")
                return user_in_db
            else:
                logger.error("Failed to create user: insert returned no ID")
                return None

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    # ============================================================================
    # READ OPERATIONS
    # ============================================================================

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """
        Get user by email address.

        Args:
            email: User's email

        Returns:
            User if found, None otherwise
        """
        try:
            user_doc = await self.collection.find_one({"email": email})
            if user_doc:
                return UserInDB(**user_doc)
            return None
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Get user by user ID.

        Args:
            user_id: User's unique ID

        Returns:
            User if found, None otherwise
        """
        try:
            user_doc = await self.collection.find_one({"user_id": user_id})
            if user_doc:
                return UserInDB(**user_doc)
            return None
        except Exception as e:
            logger.error(f"Error fetching user by ID: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Get user by username.

        Args:
            username: User's username

        Returns:
            User if found, None otherwise
        """
        try:
            user_doc = await self.collection.find_one({"username": username})
            if user_doc:
                return UserInDB(**user_doc)
            return None
        except Exception as e:
            logger.error(f"Error fetching user by username: {e}")
            return None

    async def get_public_user(self, user_id: str) -> Optional[UserPublic]:
        """
        Get public user profile (no sensitive data).

        Args:
            user_id: User's unique ID

        Returns:
            Public user profile if found, None otherwise
        """
        user = await self.get_user_by_id(user_id)
        if user:
            return UserPublic(**user.model_dump())
        return None

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[UserPublic]:
        """
        List users with pagination.

        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return
            active_only: Only return active users

        Returns:
            List of public user profiles
        """
        try:
            query = {"is_active": True} if active_only else {}

            cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)

            users = []
            async for user_doc in cursor:
                user = UserInDB(**user_doc)
                users.append(UserPublic(**user.model_dump()))

            return users

        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

    # ============================================================================
    # UPDATE OPERATIONS
    # ============================================================================

    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """
        Update user profile.

        Args:
            user_id: User's unique ID
            user_update: Fields to update

        Returns:
            Updated user if successful, None otherwise
        """
        try:
            # Prepare update data (exclude None values)
            update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}

            if not update_data:
                # Nothing to update
                return await self.get_user_by_id(user_id)

            # Add updated_at timestamp
            update_data["updated_at"] = datetime.utcnow()

            # Update in database
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.info(f"✅ User updated: {user_id}")
                return await self.get_user_by_id(user_id)
            else:
                logger.warning(f"No changes made for user: {user_id}")
                return await self.get_user_by_id(user_id)

        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None

    async def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp.

        Args:
            user_id: User's unique ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False

    async def increment_conversation_count(self, user_id: str) -> bool:
        """
        Increment user's total conversation count.

        Args:
            user_id: User's unique ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$inc": {"total_conversations": 1}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error incrementing conversation count: {e}")
            return False

    async def increment_message_count(self, user_id: str, count: int = 1) -> bool:
        """
        Increment user's total message count.

        Args:
            user_id: User's unique ID
            count: Number of messages to add

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$inc": {"total_messages": count}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error incrementing message count: {e}")
            return False

    async def change_password(self, user_id: str, new_password_hash: str) -> bool:
        """
        Change user's password.

        Args:
            user_id: User's unique ID
            new_password_hash: New hashed password

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "hashed_password": new_password_hash,
                    "updated_at": datetime.utcnow()
                }}
            )

            if result.modified_count > 0:
                logger.info(f"✅ Password changed for user: {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False

    # ============================================================================
    # DELETE OPERATIONS
    # ============================================================================

    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate user account (soft delete).

        Args:
            user_id: User's unique ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }}
            )

            if result.modified_count > 0:
                logger.info(f"✅ User deactivated: {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return False

    async def delete_user(self, user_id: str) -> bool:
        """
        Permanently delete user account (hard delete).

        ⚠️ WARNING: This permanently removes user data!

        Args:
            user_id: User's unique ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.delete_one({"user_id": user_id})

            if result.deleted_count > 0:
                logger.warning(f"⚠️  User permanently deleted: {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

    # ============================================================================
    # VERIFICATION & STATS
    # ============================================================================

    async def verify_user(self, user_id: str) -> bool:
        """
        Mark user as verified (e.g., after email verification).

        Args:
            user_id: User's unique ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_verified": True}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error verifying user: {e}")
            return False

    async def get_user_count(self, active_only: bool = True) -> int:
        """
        Get total number of users.

        Args:
            active_only: Only count active users

        Returns:
            Number of users
        """
        try:
            query = {"is_active": True} if active_only else {}
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0


# ============================================================================
# GLOBAL USER REPOSITORY INSTANCE
# ============================================================================

_user_repository: Optional[UserRepository] = None


def init_user_repository(db: AsyncIOMotorDatabase) -> UserRepository:
    """
    Initialize the global user repository.

    Args:
        db: MongoDB database instance

    Returns:
        Initialized UserRepository instance
    """
    global _user_repository
    _user_repository = UserRepository(db)
    logger.info("✅ User Repository initialized")
    return _user_repository


def get_user_repository() -> Optional[UserRepository]:
    """
    Get the global user repository instance.

    Returns:
        UserRepository instance or None if not initialized
    """
    return _user_repository
