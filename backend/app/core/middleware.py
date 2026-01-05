from fastapi import Request, HTTPException, status as http_status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from app.core.security import verify_token

logger = logging.getLogger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for request authentication and validation"""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/google/token",
            "/api/v1/auth/google/code"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Get authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                return JSONResponse(
                    status_code=http_status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authorization header required"}
                )
            
            # Parse authorization header
            scheme, token = get_authorization_scheme_param(authorization)
            if scheme.lower() != "bearer":
                return JSONResponse(
                    status_code=http_status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authentication scheme"}
                )
            
            if not token:
                return JSONResponse(
                    status_code=http_status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token required"}
                )
            
            # Verify token
            payload = verify_token(token)
            
            # Add user info to request state
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
            request.state.google_id = payload.get("google_id")
            
            return await call_next(request)
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Authentication middleware error: {str(e)}")
            return JSONResponse(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and logging"""
    
    async def dispatch(self, request: Request, call_next):
        # Log request
        logger.info(f"{request.method} {request.url.path}")
        
        # Add request ID for tracing
        import uuid
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            
            # Log response
            logger.info(f"Request {request_id} completed with status {response.status_code}")
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            logger.error(f"Request {request_id} failed: {str(e)}", exc_info=True)
            from fastapi import status as http_status
            return JSONResponse(
                status_code=http_http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id
                }
            )
