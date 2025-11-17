"""
Backend API Client for Automation Agent

This module provides HTTP client functionality for communicating with the backend API.
Includes error handling, retry logic, and comprehensive logging for monitoring.
"""

import asyncio
import logging
import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import httpx
from httpx import AsyncClient, Response, HTTPStatusError, RequestError, TimeoutException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import settings
from .models import ProcessedAssignment, GeneratedSolution
from .logging_config import (
    log_api_request, 
    log_api_response, 
    log_retry_attempt, 
    log_operation_metrics,
    get_request_logger
)

logger = logging.getLogger(__name__)

class BackendAPIError(Exception):
    """Base exception for backend API errors"""
    pass

class BackendAuthenticationError(BackendAPIError):
    """Authentication-related errors"""
    pass

class BackendValidationError(BackendAPIError):
    """Data validation errors"""
    pass

class BackendServerError(BackendAPIError):
    """Server-side errors (5xx)"""
    pass

class BackendClient:
    """HTTP client for backend API communication with retry logic and error handling"""
    
    def __init__(self):
        self.base_url = settings.BACKEND_API_URL.rstrip('/')
        self.api_key = settings.BACKEND_API_KEY
        self.client: Optional[AsyncClient] = None
        self.session_headers = {}
        
        # Configure retry settings
        self.max_retries = 3
        self.retry_delay_base = 1  # Base delay in seconds
        self.retry_delay_max = 60  # Maximum delay in seconds
        
        logger.info(f"Initialized BackendClient with base URL: {self.base_url}")
    
    async def initialize(self) -> bool:
        """Initialize the HTTP client and authenticate if needed"""
        try:
            logger.info("Initializing backend API client...")
            
            # Create HTTP client with timeout configuration
            timeout = httpx.Timeout(
                connect=10.0,  # Connection timeout
                read=30.0,     # Read timeout
                write=10.0,    # Write timeout
                pool=5.0       # Pool timeout
            )
            
            self.client = AsyncClient(
                base_url=self.base_url,
                timeout=timeout,
                headers={
                    "User-Agent": "AutomationAgent/1.0",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            # Add API key to headers if provided
            if self.api_key:
                self.session_headers["X-API-Key"] = self.api_key
                logger.info("API key authentication configured")
            
            # Test connection with health check
            await self._health_check()
            
            logger.info("Backend API client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize backend client: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client connection"""
        if self.client:
            await self.client.aclose()
            logger.info("Backend API client connection closed")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((RequestError, HTTPStatusError, TimeoutException))
    )
    async def _health_check(self):
        """Perform health check to verify backend connectivity"""
        logger.info("Performing backend API health check...")
        
        try:
            response = await self.client.get("/health", headers=self.session_headers)
            response.raise_for_status()
            
            logger.info("Backend API health check successful")
            
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                # Health endpoint might not exist, try root endpoint
                logger.warning("Health endpoint not found, trying root endpoint...")
                response = await self.client.get("/", headers=self.session_headers)
                response.raise_for_status()
            else:
                raise
        except Exception as e:
            logger.error(f"Backend API health check failed: {e}")
            raise BackendAPIError(f"Backend API is not accessible: {e}")
    
    async def upload_assignment(self, assignment: ProcessedAssignment) -> Dict[str, Any]:
        """Upload a processed assignment to the backend API"""
        logger.info(f"Uploading assignment: {assignment.title}")
        
        try:
            # Prepare assignment data for API
            assignment_data = {
                "google_classroom_id": assignment.google_classroom_id,
                "title": assignment.title,
                "description": assignment.description,
                "subject": assignment.subject,
                "course_name": assignment.course_name,
                "instructor": assignment.instructor,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "assignment_type": assignment.assignment_type,
                "user_id": assignment.user_id,
                "source": "google_classroom",
                "status": "processing",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Upload assignment
            response_data = await self._make_request(
                method="POST",
                endpoint="/api/v1/assignments",
                data=assignment_data
            )
            
            logger.info(f"Successfully uploaded assignment: {assignment.title} (ID: {response_data.get('id')})")
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to upload assignment {assignment.title}: {e}")
            raise BackendAPIError(f"Assignment upload failed: {e}")
    
    async def upload_solution(self, assignment_id: str, solution: GeneratedSolution) -> Dict[str, Any]:
        """Upload a generated solution to the backend API"""
        logger.info(f"Uploading solution for assignment ID: {assignment_id}")
        
        try:
            # Prepare solution data for API
            solution_data = {
                "assignment_id": assignment_id,
                "content": solution.content,
                "explanation": solution.explanation,
                "step_by_step": solution.step_by_step,
                "reasoning": solution.reasoning,
                "generated_by": solution.generated_by,
                "ai_model_used": solution.ai_model_used,
                "confidence_score": solution.confidence_score,
                "processing_time": solution.processing_time,
                "subject_area": solution.subject_area,
                "quality_validated": solution.quality_validated,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Upload solution via internal endpoint
            response_data = await self._make_request(
                method="POST",
                endpoint=f"/api/v1/assignments/_internal/{assignment_id}/solution",
                data=solution_data
            )
            
            logger.info(f"Successfully uploaded solution for assignment ID: {assignment_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to upload solution for assignment {assignment_id}: {e}")
            raise BackendAPIError(f"Solution upload failed: {e}")
    
    async def update_assignment_status(self, assignment_id: str, status: str) -> Dict[str, Any]:
        """Update assignment status in the backend"""
        logger.info(f"Updating assignment {assignment_id} status to: {status}")
        
        try:
            status_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Use internal endpoint for status updates
            response_data = await self._make_request(
                method="PUT",
                endpoint=f"/api/v1/assignments/_internal/{assignment_id}/status",
                data=status_data
            )
            
            logger.info(f"Successfully updated assignment {assignment_id} status to: {status}")
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to update assignment {assignment_id} status: {e}")
            raise BackendAPIError(f"Status update failed: {e}")
    
    async def check_assignment_exists(self, google_classroom_id: str) -> Optional[Dict[str, Any]]:
        """Check if an assignment already exists in the backend"""
        logger.debug(f"Checking if assignment exists: {google_classroom_id}")
        
        try:
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/api/v1/assignments/search",
                params={"google_classroom_id": google_classroom_id}
            )
            
            assignments = response_data.get("assignments", [])
            if assignments:
                logger.debug(f"Assignment {google_classroom_id} already exists")
                return assignments[0]
            
            logger.debug(f"Assignment {google_classroom_id} does not exist")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to check assignment existence: {e}")
            return None
    
    async def get_assignments(self, user_id: str = None, status: str = None, limit: int = 100) -> Dict[str, Any]:
        """Get assignments from backend, optionally filtered by user_id and status"""
        logger.info(f"Fetching assignments (user_id={user_id}, status={status})")
        
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            endpoint = f"/api/v1/users/{user_id}/assignments" if user_id else "/api/v1/assignments"
            
            response_data = await self._make_request(
                method="GET",
                endpoint=endpoint,
                params=params
            )
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to fetch assignments: {e}")
            raise BackendAPIError(f"Failed to fetch assignments: {e}")
    
    async def get_assignment(self, assignment_id: str) -> Dict[str, Any]:
        """Get a single assignment by ID from backend (using internal agent endpoint)"""
        logger.info(f"Fetching assignment {assignment_id}")
        
        try:
            # Use internal endpoint with API key authentication
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/api/v1/assignments/_internal/{assignment_id}"
            )
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to fetch assignment {assignment_id}: {e}")
            raise BackendAPIError(f"Failed to fetch assignment {assignment_id}: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((RequestError, HTTPStatusError, TimeoutException))
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and error handling"""
        
        if not self.client:
            raise BackendAPIError("Client not initialized. Call initialize() first.")
        
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request_logger = get_request_logger(request_id)
        
        # Prepare request parameters
        request_kwargs = {
            "headers": self.session_headers,
            "params": params
        }
        
        if data:
            request_kwargs["json"] = data
        
        # Log request details
        full_url = f"{self.base_url}{endpoint}"
        log_api_request(method, full_url, data, request_id)
        
        start_time = time.time()
        
        try:
            # Make the HTTP request
            response: Response = await self.client.request(
                method=method.upper(),
                url=endpoint,
                **request_kwargs
            )
            
            duration = time.time() - start_time
            
            # Handle different response status codes
            if response.status_code == 200 or response.status_code == 201:
                # Success - parse JSON response
                try:
                    response_data = response.json()
                    log_api_response(response.status_code, response_data, request_id, duration)
                    return response_data
                except json.JSONDecodeError:
                    # Handle non-JSON responses
                    response_data = {"message": "Success", "data": response.text}
                    log_api_response(response.status_code, response_data, request_id, duration)
                    return response_data
            
            elif response.status_code == 400:
                # Bad request - validation error
                error_detail = self._extract_error_detail(response)
                log_api_response(response.status_code, {"error": error_detail}, request_id, duration)
                raise BackendValidationError(f"Validation error: {error_detail}")
            
            elif response.status_code == 401:
                # Unauthorized
                log_api_response(response.status_code, {"error": "Unauthorized"}, request_id, duration)
                raise BackendAuthenticationError("Authentication failed - invalid API key")
            
            elif response.status_code == 404:
                # Not found
                log_api_response(response.status_code, {"error": "Not found"}, request_id, duration)
                raise BackendAPIError(f"Endpoint not found: {endpoint}")
            
            elif response.status_code == 429:
                # Rate limited
                retry_after = response.headers.get("Retry-After", "60")
                log_api_response(response.status_code, {"retry_after": retry_after}, request_id, duration)
                request_logger.warning(f"Rate limited. Retry after {retry_after} seconds")
                await asyncio.sleep(int(retry_after))
                raise HTTPStatusError("Rate limited", request=response.request, response=response)
            
            elif 500 <= response.status_code < 600:
                # Server error
                error_detail = self._extract_error_detail(response)
                log_api_response(response.status_code, {"error": error_detail}, request_id, duration)
                raise BackendServerError(f"Server error ({response.status_code}): {error_detail}")
            
            else:
                # Other errors
                log_api_response(response.status_code, None, request_id, duration)
                response.raise_for_status()
                
        except HTTPStatusError as e:
            duration = time.time() - start_time
            request_logger.error(f"HTTP error: {e}")
            log_api_response(e.response.status_code if hasattr(e, 'response') else 0, 
                           {"error": str(e)}, request_id, duration)
            raise
        except RequestError as e:
            duration = time.time() - start_time
            request_logger.error(f"Request error: {e}")
            log_api_response(0, {"error": str(e)}, request_id, duration)
            raise BackendAPIError(f"Network error: {e}")
        except TimeoutException as e:
            duration = time.time() - start_time
            request_logger.error(f"Timeout error: {e}")
            log_api_response(0, {"error": str(e)}, request_id, duration)
            raise BackendAPIError(f"Request timeout: {e}")
        except Exception as e:
            duration = time.time() - start_time
            request_logger.error(f"Unexpected error: {e}")
            log_api_response(0, {"error": str(e)}, request_id, duration)
            raise BackendAPIError(f"Unexpected error: {e}")
    
    def _extract_error_detail(self, response: Response) -> str:
        """Extract error details from response"""
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                return error_data.get("message", error_data.get("detail", str(error_data)))
            return str(error_data)
        except:
            return response.text or f"HTTP {response.status_code}"
    
    async def upload_assignment_and_solution(
        self,
        assignment: ProcessedAssignment,
        solution: GeneratedSolution
    ) -> Dict[str, Any]:
        """Upload both assignment and solution in a single transaction"""
        logger.info(f"Uploading assignment and solution: {assignment.title}")
        
        try:
            # Check if assignment already exists
            existing_assignment = await self.check_assignment_exists(assignment.google_classroom_id)
            
            if existing_assignment:
                logger.info(f"Assignment {assignment.title} already exists, updating solution only")
                assignment_id = existing_assignment["id"]
                
                # Update assignment status to processing
                await self.update_assignment_status(assignment_id, "processing")
            else:
                # Upload new assignment
                assignment_response = await self.upload_assignment(assignment)
                assignment_id = assignment_response["id"]
            
            # Upload solution
            solution_response = await self.upload_solution(assignment_id, solution)
            
            # Update assignment status to completed
            await self.update_assignment_status(assignment_id, "completed")
            
            result = {
                "assignment_id": assignment_id,
                "solution_uploaded": True,
                "status": "completed"
            }
            
            logger.info(f"Successfully uploaded assignment and solution: {assignment.title}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload assignment and solution {assignment.title}: {e}")
            
            # Try to update status to failed if we have an assignment ID
            try:
                if 'assignment_id' in locals():
                    await self.update_assignment_status(assignment_id, "failed")
            except:
                pass  # Don't fail the main operation if status update fails
            
            raise BackendAPIError(f"Upload transaction failed: {e}")
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics from the backend"""
        logger.debug("Fetching processing statistics")
        
        try:
            response_data = await self._make_request(
                method="GET",
                endpoint="/api/v1/stats/processing"
            )
            
            logger.debug("Successfully fetched processing statistics")
            return response_data
            
        except Exception as e:
            logger.warning(f"Failed to fetch processing statistics: {e}")
            return {"error": str(e)}
    
    async def get_user_google_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user's Google OAuth credentials from backend.
        Uses API key authentication.
        
        Args:
            user_id: The user ID to fetch credentials for
            
        Returns:
            Dictionary with google_access_token, google_refresh_token, etc.
        """
        try:
            logger.info(f"Fetching Google credentials for user {user_id}")
            
            # Temporarily add X-API-Key header to session headers
            original_headers = self.session_headers.copy()
            self.session_headers["X-API-Key"] = self.api_key
            
            try:
                response_data = await self._make_request(
                    method="GET",
                    endpoint=f"/api/v1/users/{user_id}/google-credentials"
                )
                
                logger.info(f"Successfully fetched Google credentials for user {user_id}")
                return response_data
            finally:
                # Restore original headers
                self.session_headers = original_headers
            
        except Exception as e:
            logger.error(f"Failed to fetch Google credentials for user {user_id}: {e}")
            return None
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Fetch list of all users from backend.
        
        Returns:
            List of user dictionaries
        """
        try:
            logger.info("Fetching all users from backend")
            
            response_data = await self._make_request(
                method="GET",
                endpoint="/api/v1/users"
            )
            
            users = response_data.get('users', [])
            logger.info(f"Successfully fetched {len(users)} users")
            return users
            
        except Exception as e:
            logger.error(f"Failed to fetch users: {e}")
            return []
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.client:
            asyncio.create_task(self.close())
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()