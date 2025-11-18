"""
Comprehensive logging configuration for the automation agent

Provides structured logging with different levels for monitoring and debugging
backend communication, error handling, and retry logic.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import settings

class BackendClientFilter(logging.Filter):
    """Filter for backend client specific logs"""
    
    def filter(self, record):
        return record.name.startswith('src.backend_client')

class AgentFilter(logging.Filter):
    """Filter for agent specific logs"""
    
    def filter(self, record):
        return record.name.startswith('src.agent')

class CustomFormatter(logging.Formatter):
    """Custom formatter with color coding and structured format"""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to console output
        if hasattr(record, 'color') and record.color:
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
        
        # Add component information
        component = self._extract_component(record.name)
        record.component = component
        
        # Add request ID if available (for tracing backend requests)
        if hasattr(record, 'request_id'):
            record.request_info = f"[{record.request_id}]"
        else:
            record.request_info = ""
        
        return super().format(record)
    
    def _extract_component(self, logger_name: str) -> str:
        """Extract component name from logger name"""
        if 'backend_client' in logger_name:
            return 'BACKEND'
        elif 'agent' in logger_name:
            return 'AGENT'
        elif 'classroom_client' in logger_name:
            return 'CLASSROOM'
        elif 'gemini_client' in logger_name:
            return 'GEMINI'
        elif 'scheduler' in logger_name:
            return 'SCHEDULER'
        else:
            return 'SYSTEM'

def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_rotation: bool = True
):
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file path
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_rotation: Enable log file rotation
    """
    
    # Use settings defaults if not provided
    log_level = log_level or settings.LOG_LEVEL
    log_file = log_file or settings.LOG_FILE
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with color formatting
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        console_format = (
            "%(asctime)s - %(component)s - %(levelname)s - "
            "%(name)s:%(lineno)d - %(request_info)s%(message)s"
        )
        console_formatter = CustomFormatter(console_format)
        console_handler.setFormatter(console_formatter)
        
        # Add color attribute for console output
        class ColorFilter(logging.Filter):
            def filter(self, record):
                record.color = True
                return True
        
        console_handler.addFilter(ColorFilter())
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if enable_file:
        if enable_rotation:
            # Rotating file handler (10MB max, keep 5 backups)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
        else:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        file_handler.setLevel(logging.DEBUG)  # File gets all logs
        
        file_format = (
            "%(asctime)s - %(component)s - %(levelname)s - "
            "%(name)s:%(lineno)d - %(funcName)s - %(request_info)s%(message)s"
        )
        file_formatter = CustomFormatter(file_format)
        file_handler.setFormatter(file_formatter)
        
        # Add no-color attribute for file output
        class NoColorFilter(logging.Filter):
            def filter(self, record):
                record.color = False
                return True
        
        file_handler.addFilter(NoColorFilter())
        root_logger.addHandler(file_handler)
    
    # Separate backend client log file for detailed API communication
    backend_log_file = log_path.parent / f"backend_api_{datetime.now().strftime('%Y%m%d')}.log"
    backend_handler = logging.FileHandler(backend_log_file, encoding='utf-8')
    backend_handler.setLevel(logging.DEBUG)
    backend_handler.addFilter(BackendClientFilter())
    
    backend_format = (
        "%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - "
        "%(request_info)s%(message)s"
    )
    backend_formatter = logging.Formatter(backend_format)
    backend_handler.setFormatter(backend_formatter)
    root_logger.addHandler(backend_handler)
    
    # Separate agent workflow log file
    agent_log_file = log_path.parent / f"agent_workflow_{datetime.now().strftime('%Y%m%d')}.log"
    agent_handler = logging.FileHandler(agent_log_file, encoding='utf-8')
    agent_handler.setLevel(logging.INFO)
    agent_handler.addFilter(AgentFilter())
    
    agent_format = (
        "%(asctime)s - %(levelname)s - %(funcName)s - %(message)s"
    )
    agent_formatter = logging.Formatter(agent_format)
    agent_handler.setFormatter(agent_formatter)
    root_logger.addHandler(agent_handler)
    
    # Configure third-party library logging levels
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.INFO)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")
    logger.info(f"Backend API logs: {backend_log_file}")
    logger.info(f"Agent workflow logs: {agent_log_file}")

def get_request_logger(request_id: str) -> logging.LoggerAdapter:
    """
    Get a logger adapter that includes request ID in all log messages
    
    Args:
        request_id: Unique identifier for the request/operation
        
    Returns:
        LoggerAdapter with request ID context
    """
    logger = logging.getLogger('src.backend_client')
    
    class RequestAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            # Add request ID to the log record
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['request_id'] = self.extra['request_id']
            return msg, kwargs
    
    return RequestAdapter(logger, {'request_id': request_id})

def log_api_request(method: str, url: str, data: dict = None, request_id: str = None):
    """
    Log API request details
    
    Args:
        method: HTTP method
        url: Request URL
        data: Request data (sensitive fields will be masked)
        request_id: Request identifier
    """
    logger = get_request_logger(request_id) if request_id else logging.getLogger('src.backend_client')
    
    # Mask sensitive data
    safe_data = {}
    if data:
        for key, value in data.items():
            if key.lower() in ['password', 'token', 'api_key', 'secret']:
                safe_data[key] = '***MASKED***'
            else:
                safe_data[key] = value
    
    logger.info(f"API Request: {method} {url} - Data: {safe_data}")

def log_api_response(status_code: int, response_data: dict = None, request_id: str = None, duration: float = None):
    """
    Log API response details
    
    Args:
        status_code: HTTP status code
        response_data: Response data
        request_id: Request identifier
        duration: Request duration in seconds
    """
    logger = get_request_logger(request_id) if request_id else logging.getLogger('src.backend_client')
    
    duration_str = f" ({duration:.2f}s)" if duration else ""
    
    if 200 <= status_code < 300:
        logger.info(f"API Response: {status_code}{duration_str} - Success")
    elif 400 <= status_code < 500:
        logger.warning(f"API Response: {status_code}{duration_str} - Client Error - Data: {response_data}")
    elif 500 <= status_code < 600:
        logger.error(f"API Response: {status_code}{duration_str} - Server Error - Data: {response_data}")
    else:
        logger.info(f"API Response: {status_code}{duration_str} - Data: {response_data}")

def log_retry_attempt(attempt: int, max_attempts: int, error: Exception, request_id: str = None):
    """
    Log retry attempt information
    
    Args:
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        error: Exception that caused the retry
        request_id: Request identifier
    """
    logger = get_request_logger(request_id) if request_id else logging.getLogger('src.backend_client')
    
    logger.warning(f"Retry attempt {attempt}/{max_attempts} - Error: {error}")

def log_operation_metrics(operation: str, duration: float, success: bool, details: dict = None):
    """
    Log operation performance metrics
    
    Args:
        operation: Operation name
        duration: Operation duration in seconds
        success: Whether operation succeeded
        details: Additional operation details
    """
    logger = logging.getLogger('src.agent')
    
    status = "SUCCESS" if success else "FAILED"
    details_str = f" - Details: {details}" if details else ""
    
    logger.info(f"METRICS: {operation} - {status} - Duration: {duration:.2f}s{details_str}")