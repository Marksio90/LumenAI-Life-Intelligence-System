# Rate Limiting 🛡️

## Overview

LumenAI implements comprehensive rate limiting to protect API resources, ensure fair usage, and prevent abuse.

## Global Rate Limits

All API endpoints (except health/docs) are protected with global rate limiting:

- **100 requests per minute** per IP address
- **429 Too Many Requests** response when exceeded
- Automatic retry-after headers

### Rate Limit Headers

Every API response includes rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1733312400
```

When rate limited:
```
Retry-After: 45
```

## Rate Limit Tiers

### Free Tier
- **20 requests/minute**
- **100 requests/hour**
- **1,000 requests/day**

### Personal ($19/month)
- **60 requests/minute**
- **1,000 requests/hour**
- **10,000 requests/day**

### Professional ($79/month)
- **120 requests/minute**
- **5,000 requests/hour**
- **50,000 requests/day**

### Enterprise (Custom)
- **300 requests/minute**
- **20,000 requests/hour**
- **200,000 requests/day**

## Rate Limit Response

When rate limit is exceeded:

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Try again in 45 seconds.",
  "retry_after": 45,
  "limit": 100,
  "window": 60
}
```

**Status Code:** `429 Too Many Requests`

## Excluded Endpoints

These endpoints are NOT rate limited:
- `/health` - Health check
- `/docs` - API documentation
- `/redoc` - Alternative API docs
- `/openapi.json` - OpenAPI schema
- `/` - Root endpoint

## For Developers

### Adding Rate Limits to Endpoints

```python
from backend.middleware.rate_limit_middleware import rate_limit

@app.get("/api/v1/expensive-operation")
@rate_limit(max_requests=10, window_seconds=60)
async def expensive_operation(request: Request):
    # Only 10 requests per minute allowed
    return {"result": "success"}
```

### User-Specific Rate Limiting

```python
from backend.middleware.rate_limit_middleware import check_user_rate_limit

@app.get("/api/v1/user/action")
async def user_action(
    request: Request,
    current_user = Depends(get_current_active_user)
):
    # Check user's tier-based limits
    await check_user_rate_limit(
        request,
        user_id=current_user.user_id,
        tier=current_user.tier  # "free", "personal", "professional", "enterprise"
    )

    return {"result": "success"}
```

### Custom Identifier

By default, rate limiting uses IP address. Use custom identifiers:

```python
def get_user_identifier(request: Request) -> str:
    # Extract from JWT token or session
    return request.state.user_id

@app.get("/api/v1/endpoint")
@rate_limit(max_requests=50, window_seconds=60, identifier=get_user_identifier)
async def endpoint(request: Request):
    return {"result": "success"}
```

## Algorithm

LumenAI uses the **Token Bucket Algorithm**:

1. Each user starts with a bucket of tokens
2. Each request consumes one token
3. Tokens regenerate over time
4. When bucket is empty, requests are rejected

This allows for burst traffic while maintaining long-term limits.

## Storage

**Current:** In-memory storage (fast, simple)
**Production:** Migrate to Redis for:
- Distributed rate limiting across servers
- Persistent rate limit state
- Better performance at scale

## Configuration

### Environment Variables

```bash
# Global rate limit (requests per minute)
RATE_LIMIT_REQUESTS=100

# Rate limit window (seconds)
RATE_LIMIT_WINDOW=60
```

### Updating Middleware

In `backend/gateway/main.py`:

```python
app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,  # Requests per window
    window_seconds=60,  # Window size
    exclude_paths=["/health", "/docs"]
)
```

## Monitoring

Rate limit metrics are automatically logged:

```
⛔ Rate limit exceeded for 192.168.1.100 on /api/v1/chat: 101/100 requests
```

## Best Practices

### For Users

1. **Check rate limit headers** - Monitor remaining requests
2. **Implement exponential backoff** - Don't retry immediately
3. **Batch requests** - Combine multiple operations
4. **Upgrade tier** - Get higher limits for production use

### For Developers

1. **Set appropriate limits** - Balance protection vs usability
2. **Exclude health endpoints** - Allow monitoring
3. **Use user-specific limits** - Tier-based access
4. **Log rate limit violations** - Monitor abuse patterns
5. **Test with load** - Verify limits work as expected

## Client-Side Handling

### JavaScript/TypeScript

```javascript
async function makeRequest(url, options) {
  const response = await fetch(url, options);

  if (response.status === 429) {
    // Rate limited
    const retryAfter = parseInt(response.headers.get('Retry-After') || '60');

    console.log(`Rate limited. Retry after ${retryAfter}s`);

    // Wait and retry
    await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
    return makeRequest(url, options);
  }

  return response;
}
```

### Python

```python
import time
import requests

def make_request(url):
    response = requests.get(url)

    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after}s...")
        time.sleep(retry_after)
        return make_request(url)

    return response
```

## Upgrading to Redis

For production deployments, use Redis for distributed rate limiting:

```python
from redis import asyncio as aioredis

class RedisRateLimiter:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)

    async def is_rate_limited(self, key: str, max_requests: int, window: int):
        pipe = self.redis.pipeline()
        now = time.time()
        window_start = now - window

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count requests in window
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Set expiry
        pipe.expire(key, window)

        results = await pipe.execute()
        request_count = results[1]

        return request_count >= max_requests
```

## FAQ

### Q: Why am I getting rate limited?

**A:** You've exceeded your tier's rate limit. Check the `X-RateLimit-Limit` and `X-RateLimit-Remaining` headers. Upgrade your tier or wait for the limit to reset.

### Q: Can I increase my rate limit?

**A:** Yes! Upgrade to a higher tier:
- Personal: 60 req/min
- Professional: 120 req/min
- Enterprise: 300 req/min

### Q: Does rate limiting apply to WebSockets?

**A:** WebSocket connections have separate limits. Each message sent through WebSocket counts toward your limit.

### Q: What happens if I repeatedly hit the rate limit?

**A:** Persistent abuse may result in temporary IP blocking. Use appropriate retry logic and respect rate limits.

### Q: Can I whitelist my IP?

**A:** Enterprise customers can request IP whitelisting. Contact support for details.

---

**Built with ❤️ by the LumenAI Team**
