from typing import Optional, List
from pydantic import BaseModel, validator
import os
import json
from pathlib import Path

class Settings(BaseModel):
    # Google Classroom API (deprecated - now uses backend tokens)
    GOOGLE_CREDENTIALS_FILE: Optional[str] = None
    GOOGLE_TOKEN_FILE: Optional[str] = None
    GOOGLE_SCOPES: List[str] = [
        'https://www.googleapis.com/auth/classroom.courses.readonly',
        'https://www.googleapis.com/auth/classroom.coursework.students.readonly'
    ]
    
    # Google Gemini API
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Groq API (free fallback)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    
    # Together.ai API (additional fallback)
    TOGETHER_API_KEY: Optional[str] = None
    TOGETHER_MODEL: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    
    # HuggingFace API (additional fallback)
    HF_API_TOKEN: Optional[str] = None
    HF_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.2"
    
    # LLM Provider Settings
    LLM_PROVIDER_PRIORITY: str = "gemini,groq"  # Comma-separated priority order
    ENABLE_LOCAL_FALLBACK: bool = False
    
    # Backend API - auto-detect port from environment
    BACKEND_API_URL: str = f"http://localhost:{os.getenv('PORT', '8000')}"
    BACKEND_API_KEY: Optional[str] = None
    
    # Rate Limiting & Duplicate Detection
    SIMILARITY_THRESHOLD: float = 0.85
    ENABLE_DUPLICATE_DETECTION: bool = True
    AUTO_DETECT_SUBJECT: bool = True
    
    # Scheduling
    SYNC_SCHEDULE_CRON: str = "0 8 * * *"  # Daily at 8 AM
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "agent.log"
    
    # Authentication settings
    AUTH_RETRY_ATTEMPTS: int = 3
    AUTH_TIMEOUT_SECONDS: int = 300  # 5 minutes for OAuth flow
    
    @validator('GOOGLE_CREDENTIALS_FILE')
    def validate_credentials_file(cls, v):
        """Validate that credentials file exists and has correct format (optional now)"""
        if not v or not Path(v).exists():
            return v  # Return as-is if not provided or doesn't exist
        
        try:
            with open(v, 'r') as f:
                creds_data = json.load(f)
            
            if 'installed' not in creds_data:
                raise ValueError("Invalid credentials format - must be OAuth client credentials")
            
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            installed = creds_data['installed']
            
            for field in required_fields:
                if field not in installed:
                    raise ValueError(f"Missing required field in credentials: {field}")
            
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in credentials file")
        
        return v
    
    @validator('GOOGLE_SCOPES')
    def validate_scopes(cls, v):
        """Validate that required scopes are present"""
        required_scopes = [
            'https://www.googleapis.com/auth/classroom.courses.readonly',
            'https://www.googleapis.com/auth/classroom.coursework.students.readonly'
        ]
        
        for scope in required_scopes:
            if scope not in v:
                raise ValueError(f"Missing required scope: {scope}")
        
        return v
    
    class Config:
        env_file = ".env"
        validate_assignment = True

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def create_settings() -> Settings:
    """Create settings instance with environment variable loading"""
    # Get port from environment (Render sets this)
    port = os.getenv('PORT', '8000')
    default_backend_url = f"http://localhost:{port}"
    
    try:
        return Settings(
            GOOGLE_CREDENTIALS_FILE=os.getenv("GOOGLE_CREDENTIALS_FILE"),
            GOOGLE_TOKEN_FILE=os.getenv("GOOGLE_TOKEN_FILE"),
            GEMINI_API_KEY=os.getenv("GEMINI_API_KEY"),
            GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            GROQ_API_KEY=os.getenv("GROQ_API_KEY"),
            GROQ_MODEL=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
            TOGETHER_API_KEY=os.getenv("TOGETHER_API_KEY"),
            TOGETHER_MODEL=os.getenv("TOGETHER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            HF_API_TOKEN=os.getenv("HF_API_TOKEN"),
            HF_MODEL=os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"),
            LLM_PROVIDER_PRIORITY=os.getenv("LLM_PROVIDER_PRIORITY", "gemini,groq"),
            ENABLE_LOCAL_FALLBACK=os.getenv("ENABLE_LOCAL_FALLBACK", "false").lower() == "true",
            BACKEND_API_URL=os.getenv("BACKEND_API_URL", default_backend_url),
            BACKEND_API_KEY=os.getenv("BACKEND_API_KEY"),
            SIMILARITY_THRESHOLD=float(os.getenv("SIMILARITY_THRESHOLD", "0.85")),
            ENABLE_DUPLICATE_DETECTION=os.getenv("ENABLE_DUPLICATE_DETECTION", "true").lower() == "true",
            AUTO_DETECT_SUBJECT=os.getenv("AUTO_DETECT_SUBJECT", "true").lower() == "true",
            SYNC_SCHEDULE_CRON=os.getenv("SYNC_SCHEDULE_CRON", "0 8 * * *"),
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
            LOG_FILE=os.getenv("LOG_FILE", "agent.log"),
            AUTH_RETRY_ATTEMPTS=int(os.getenv("AUTH_RETRY_ATTEMPTS", "3")),
            AUTH_TIMEOUT_SECONDS=int(os.getenv("AUTH_TIMEOUT_SECONDS", "300"))
        )
    except Exception as e:
        # Fallback to basic settings if validation fails
        print(f"Warning: Settings validation failed: {e}")
        # Return minimal settings without Google credentials file
        port = os.getenv('PORT', '8000')
        return Settings(
            GEMINI_API_KEY=os.getenv("GEMINI_API_KEY"),
            BACKEND_API_URL=os.getenv("BACKEND_API_URL", f"http://localhost:{port}"),
            BACKEND_API_KEY=os.getenv("BACKEND_API_KEY"),
        )
        return Settings()

# Global settings instance
settings = create_settings()