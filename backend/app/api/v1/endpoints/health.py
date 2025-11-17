"""
Health check endpoints for system monitoring
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Dict, Any
import psutil
import asyncio
from app.core.database import get_database
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "assignment-solver-backend",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(db=Depends(get_database)) -> Dict[str, Any]:
    """Detailed health check with system metrics"""
    try:
        # Database connectivity check
        db_status = "healthy"
        db_response_time = None
        try:
            start_time = datetime.utcnow()
            await db.command("ping")
            end_time = datetime.utcnow()
            db_response_time = (end_time - start_time).total_seconds() * 1000  # ms
        except Exception as e:
            db_status = "unhealthy"
            logger.error(f"Database health check failed: {e}")
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics
        uptime = datetime.utcnow()  # This would be calculated from app start time in real implementation
        
        health_data = {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "assignment-solver-backend",
            "version": "1.0.0",
            "checks": {
                "database": {
                    "status": db_status,
                    "response_time_ms": db_response_time
                },
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available // (1024 * 1024),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free // (1024 * 1024 * 1024)
                }
            },
            "environment": settings.ENVIRONMENT,
            "uptime": uptime.isoformat()
        }
        
        # Return 503 if any critical service is unhealthy
        if db_status != "healthy":
            raise HTTPException(status_code=503, detail=health_data)
        
        return health_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )

@router.get("/health/ready")
async def readiness_check(db=Depends(get_database)) -> Dict[str, Any]:
    """Readiness check for Kubernetes/container orchestration"""
    try:
        # Check database connectivity
        await db.command("ping")
        
        # Check if required environment variables are set
        required_vars = ["MONGODB_URL", "SECRET_KEY"]
        missing_vars = [var for var in required_vars if not getattr(settings, var, None)]
        
        if missing_vars:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "missing_config": missing_vars
                }
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "error": str(e)
            }
        )

@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes/container orchestration"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }