from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.middleware import RequestValidationMiddleware
from app.core.logging import setup_logging, RequestLoggingMiddleware, get_logger
from app.api.v1.api import api_router

# Setup comprehensive logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Assignment Solver API...")
    await connect_to_mongo()
    yield
    # Shutdown
    logger.info("Shutting down Assignment Solver API...")
    await close_mongo_connection()

app = FastAPI(
    title="Assignment Solver API",
    description="Backend API for the Automated Assignment Solver system",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Type", "Authorization"],
)

# Add request validation middleware
app.add_middleware(RequestValidationMiddleware)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Assignment Solver API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "assignment-solver-api"}