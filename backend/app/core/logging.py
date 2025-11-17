"""
Logging configuration for the backend application
"""
import logging
import logging.config
import sys
import asyncio
from typing import Dict, Any
from app.core.config import settings
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

def setup_logging() -> None:
    """Configure application logging"""
    
    # Sentry configuration for error tracking
    if settings.SENTRY_DSN:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(auto_enabling_integrations=False),
                sentry_logging,
            ],
            traces_sample_rate=0.1,  # Capture 10% of transactions for performance monitoring
            environment=settings.ENVIRONMENT,
        )
    
    # Logging configuration
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(module)s %(funcName)s %(lineno)d %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "default",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "detailed",
                "filename": "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "app": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
        },
    }
    
    # Use JSON formatter in production
    if settings.is_production:
        logging_config["handlers"]["console"]["formatter"] = "json"
    
    logging.config.dictConfig(logging_config)

class RequestLoggingMiddleware:
    """Middleware to log API requests and responses"""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("app.requests")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Log request
            method = scope["method"]
            path = scope["path"]
            query_string = scope.get("query_string", b"").decode()
            
            self.logger.info(
                f"Request: {method} {path}",
                extra={
                    "method": method,
                    "path": path,
                    "query_string": query_string,
                    "client": scope.get("client"),
                }
            )
            
            # Capture response
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                    self.logger.info(
                        f"Response: {method} {path} - {status_code}",
                        extra={
                            "method": method,
                            "path": path,
                            "status_code": status_code,
                        }
                    )
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(f"app.{name}")

# Performance monitoring decorator
def log_performance(func_name: str = None):
    """Decorator to log function performance"""
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger("performance")
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"Function {name} completed in {execution_time:.3f}s",
                    extra={
                        "function": name,
                        "execution_time": execution_time,
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function {name} failed after {execution_time:.3f}s: {str(e)}",
                    extra={
                        "function": name,
                        "execution_time": execution_time,
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger("performance")
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"Function {name} completed in {execution_time:.3f}s",
                    extra={
                        "function": name,
                        "execution_time": execution_time,
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function {name} failed after {execution_time:.3f}s: {str(e)}",
                    extra={
                        "function": name,
                        "execution_time": execution_time,
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator