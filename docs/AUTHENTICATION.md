# LumenAI Authentication System 🔒

## Overview

LumenAI now features a complete JWT-based authentication system with secure password hashing, user management, and protected API endpoints.

## Features ✨

- **JWT Token Authentication** - Secure token-based authentication
- **Password Hashing** - Bcrypt password hashing for security
- **User Registration & Login** - Complete user lifecycle management
- **Token Refresh** - Long-lived refresh tokens for seamless authentication
- **Protected Endpoints** - Middleware for securing API routes
- **User Profiles** - Full user profile management
- **Password Management** - Secure password change functionality

---

## Quick Start

### 1. Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "username": "john_doe",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "User registered successfully! Welcome to LumenAI 🌟",
  "user": {
    "user_id": "user_a3f8b2c1d5e9",
    "email": "john@example.com",
    "username": "john_doe",
    "full_name": "John Doe",
    "is_active": true,
    "is_verified": false,
    "created_at": "2025-12-04T10:00:00",
    "total_conversations": 0,
    "total_messages": 0
  },
  "token": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123"
  }'
```

### 3. Use Access Token

Include the access token in the `Authorization` header for protected endpoints:

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login with credentials | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | No |
| GET | `/api/v1/auth/me` | Get current user profile | Yes |
| PUT | `/api/v1/auth/me` | Update user profile | Yes |
| POST | `/api/v1/auth/change-password` | Change password | Yes |

### Register User

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "SecurePassword123",
  "full_name": "John Doe"  // Optional
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

**Response:** Returns user object and JWT tokens

---

### Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response:** Returns user object and JWT tokens

---

### Refresh Token

**Endpoint:** `POST /api/v1/auth/refresh`

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

### Get Current User Profile

**Endpoint:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** Returns current user's profile

---

### Update Profile

**Endpoint:** `PUT /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "full_name": "John Smith",
  "bio": "AI enthusiast and developer",
  "timezone": "America/New_York",
  "language": "en",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

---

### Change Password

**Endpoint:** `POST /api/v1/auth/change-password`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "current_password": "OldPassword123",
  "new_password": "NewSecurePassword456"
}
```

---

## For Developers: Protecting Endpoints

### Adding Authentication to Existing Endpoints

To protect an endpoint, add the `Depends(get_current_active_user)` dependency:

```python
from backend.middleware.auth_middleware import get_current_active_user

@app.get("/api/v1/protected-endpoint")
async def protected_endpoint(
    current_user = Depends(get_current_active_user)
):
    """
    This endpoint requires authentication.
    current_user will contain the authenticated user's data.
    """
    return {
        "message": f"Hello {current_user.username}!",
        "user_id": current_user.user_id
    }
```

### Available Dependencies

```python
from backend.middleware.auth_middleware import (
    get_current_active_user,      # Requires active user
    get_current_verified_user,    # Requires verified email
    get_current_superuser,        # Requires superuser privileges
    get_current_user_optional     # Optional authentication (returns None if not authenticated)
)
```

### Example: Optional Authentication

```python
@app.get("/api/v1/public-with-auth")
async def public_endpoint(
    current_user = Depends(get_current_user_optional)
):
    """
    This endpoint works for both authenticated and anonymous users.
    """
    if current_user:
        return {"message": f"Welcome back, {current_user.username}!"}
    else:
        return {"message": "Welcome, guest!"}
```

### Example: Superuser-Only Endpoint

```python
@app.get("/api/v1/admin/stats")
async def admin_stats(
    current_user = Depends(get_current_superuser)
):
    """
    Only superusers can access this endpoint.
    """
    return {"admin_data": "sensitive information"}
```

---

## Database Schema

### Users Collection

```json
{
  "user_id": "user_a3f8b2c1d5e9",
  "email": "user@example.com",
  "username": "john_doe",
  "full_name": "John Doe",
  "hashed_password": "$2b$12$...",
  "is_active": true,
  "is_verified": false,
  "is_superuser": false,
  "created_at": "2025-12-04T10:00:00",
  "updated_at": "2025-12-04T10:00:00",
  "last_login": "2025-12-04T10:05:00",
  "avatar_url": null,
  "bio": null,
  "timezone": "UTC",
  "language": "en",
  "total_conversations": 5,
  "total_messages": 42,
  "preferences": {}
}
```

### Indexes

- `email` - Unique index for fast lookup
- `username` - Unique index for fast lookup
- `user_id` - Unique index for fast lookup
- `is_active + created_at` - Compound index for querying active users

---

## Security Features

### Password Hashing

- **Algorithm:** Bcrypt
- **Rounds:** 12 (configurable)
- **Salt:** Automatically generated per password

### JWT Tokens

- **Algorithm:** HS256
- **Access Token Expiry:** 24 hours
- **Refresh Token Expiry:** 30 days
- **Secret Key:** Configurable via `SECRET_KEY` environment variable

### Token Structure

```json
{
  "sub": "user_a3f8b2c1d5e9",  // User ID
  "email": "user@example.com",
  "exp": 1733312400,           // Expiration timestamp
  "iat": 1733226000,           // Issued at timestamp
  "type": "access"             // Token type (access/refresh)
}
```

---

## Configuration

### Environment Variables

```bash
# JWT Secret Key (CHANGE IN PRODUCTION!)
SECRET_KEY=your-super-secret-key-min-32-characters

# Token Expiration (optional, defaults shown)
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS=30      # 30 days

# MongoDB Connection (required for auth)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=lumenai
```

⚠️ **IMPORTANT:** Always change `SECRET_KEY` in production! Generate a secure key:

```bash
# Generate secure secret key
openssl rand -hex 32
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "User with email user@example.com already exists"
}
```

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "User account is inactive"
}
```

### 503 Service Unavailable

```json
{
  "detail": "Authentication unavailable. Database not connected."
}
```

---

## Frontend Integration

### Storing Tokens

Store tokens securely in the browser:

```javascript
// After successful login/register
const { access_token, refresh_token } = response.token;

// Store in localStorage (or better: httpOnly cookies)
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);
```

### Making Authenticated Requests

```javascript
const accessToken = localStorage.getItem('access_token');

fetch('http://localhost:8000/api/v1/auth/me', {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log('User profile:', data));
```

### Handling Token Expiration

```javascript
async function makeAuthenticatedRequest(url, options = {}) {
  let accessToken = localStorage.getItem('access_token');

  // Try request with current token
  let response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`
    }
  });

  // If unauthorized, try refreshing token
  if (response.status === 401) {
    const refreshToken = localStorage.getItem('refresh_token');

    // Refresh access token
    const refreshResponse = await fetch('http://localhost:8000/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (refreshResponse.ok) {
      const { access_token } = await refreshResponse.json();
      localStorage.setItem('access_token', access_token);

      // Retry original request with new token
      response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${access_token}`
        }
      });
    } else {
      // Refresh failed, redirect to login
      window.location.href = '/login';
    }
  }

  return response;
}
```

---

## Testing

### Manual Testing with curl

```bash
# 1. Register
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"TestPass123"}' \
  | jq -r '.token.access_token')

# 2. Get profile
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 3. Update profile
curl -X PUT http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User Updated","bio":"Testing the auth system"}'

# 4. Change password
curl -X POST http://localhost:8000/api/v1/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"TestPass123","new_password":"NewPass456"}'
```

---

## Migration from Old System

### Before (No Auth)

```python
@app.get("/api/v1/user/{user_id}/history")
async def get_user_history(user_id: str):
    # Anyone could access any user's history!
    history = await memory_manager.get_user_history(user_id)
    return {"history": history}
```

### After (With Auth)

```python
@app.get("/api/v1/user/history")
async def get_user_history(
    current_user = Depends(get_current_active_user)
):
    # Only authenticated user can access their own history
    history = await memory_manager.get_user_history(current_user.user_id)
    return {"history": history}
```

---

## Best Practices

### Security

1. **Always use HTTPS in production** - JWT tokens are bearer tokens and must be protected
2. **Set strong SECRET_KEY** - Use at least 32 random characters
3. **Implement rate limiting** - Prevent brute force attacks on login
4. **Add email verification** - Set `is_verified` to True after email confirmation
5. **Use refresh tokens** - Keep access tokens short-lived

### Performance

1. **Cache user lookups** - Use Redis to cache frequently accessed user data
2. **Index database fields** - Email, username, user_id should all be indexed
3. **Minimize token payload** - Only include essential data in JWT

### UX

1. **Provide clear error messages** - Help users understand what went wrong
2. **Implement "Remember me"** - Use refresh tokens for persistent login
3. **Add password reset** - Allow users to recover access
4. **Show password strength** - Help users create secure passwords

---

## Next Steps

- [ ] Implement email verification
- [ ] Add password reset functionality
- [ ] Add OAuth providers (Google, GitHub, etc.)
- [ ] Implement 2FA/MFA support
- [ ] Add session management dashboard
- [ ] Implement account deletion (GDPR compliance)
- [ ] Add audit logging for security events

---

## Support

For issues or questions:
- 📖 Check the main [README.md](../README.md)
- 🐛 Report bugs in GitHub Issues
- 💬 Join our Discord community

---

**Built with ❤️ by the LumenAI Team**
