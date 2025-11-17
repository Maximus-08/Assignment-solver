"""
Google Classroom API client for authentication and assignment fetching.
Implements OAuth 2.0 flow and credential management with token refresh logic.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import settings
from .models import ClassroomAssignment
from .auth_manager import AuthenticationManager

logger = logging.getLogger(__name__)

class ClassroomClient:
    """Google Classroom API client with OAuth 2.0 authentication"""
    
    def __init__(self):
        self.service = None
        self.service_credentials = None  # Credentials provided externally (from backend)
        self.auth_manager = AuthenticationManager()  # Fallback for old method
        self._auth_lock = asyncio.Lock()
    
    def set_credentials(self, credentials):
        """Set Google OAuth credentials from external source (backend)"""
        self.service_credentials = credentials
        self.service = None  # Force rebuild with new credentials
        
    async def build_service(self):
        """Build Google Classroom service with current credentials"""
        if not self.service_credentials:
            raise RuntimeError("No credentials available. Call set_credentials() first.")
        
        from googleapiclient.discovery import build
        self.service = build('classroom', 'v1', credentials=self.service_credentials)
        logger.info("Google Classroom API service initialized")
        
    async def authenticate(self) -> bool:
        """
        Authenticate with Google Classroom API.
        If service_credentials are set (from backend), use those.
        Otherwise fall back to old OAuth flow with credentials.json.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        async with self._auth_lock:
            try:
                # Use externally provided credentials if available
                if self.service_credentials:
                    logger.info("Using credentials from backend")
                    await self.build_service()
                    await self._test_connection()
                    logger.info("Google Classroom API authentication completed successfully")
                    return True
                
                # Fallback to old auth method (credentials.json)
                logger.warning("No backend credentials found, falling back to credentials.json")
                success = self.auth_manager.authenticate()
                
                if not success:
                    logger.error("Authentication with Google Classroom API failed")
                    return False
                
                # Build the Google Classroom service
                credentials = self.auth_manager.get_credentials()
                if not credentials:
                    logger.error("No valid credentials available after authentication")
                    return False
                
                self.service = build('classroom', 'v1', credentials=credentials)
                logger.info("Google Classroom API service initialized successfully")
                
                # Test the connection
                await self._test_connection()
                
                logger.info("Google Classroom API authentication completed successfully")
                return True
                
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                return False
    
    async def refresh_credentials(self) -> bool:
        """
        Manually refresh credentials if they are expired.
        
        Returns:
            bool: True if refresh successful, False otherwise
        """
        return self.auth_manager.refresh_credentials()
    
    def revoke_credentials(self):
        """Revoke stored credentials and remove token file"""
        self.auth_manager.revoke_credentials()
        self.service = None
    
    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get detailed authentication status information.
        
        Returns:
            Dict containing authentication status details
        """
        status = self.auth_manager.get_auth_status()
        status['service_initialized'] = self.service is not None
        return status
    
    async def _test_connection(self):
        """Test the API connection by fetching user profile"""
        try:
            # Test connection by getting user profile
            profile = self.service.userProfiles().get(userId='me').execute()
            logger.info(f"Connected as: {profile.get('name', {}).get('fullName', 'Unknown')}")
            logger.info(f"Email: {profile.get('emailAddress', 'Unknown')}")
        except HttpError as e:
            logger.error(f"API connection test failed: {e}")
            raise
    
    async def get_courses(self) -> List[dict]:
        """
        Fetch all courses the authenticated user has access to.
        
        Returns:
            List[dict]: List of course objects from Classroom API
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            logger.info("Fetching courses from Google Classroom...")
            
            courses = []
            page_token = None
            
            while True:
                results = self.service.courses().list(
                    pageToken=page_token,
                    pageSize=100,
                    courseStates=['ACTIVE']
                ).execute()
                
                batch_courses = results.get('courses', [])
                courses.extend(batch_courses)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(courses)} active courses")
            return courses
            
        except HttpError as e:
            logger.error(f"Failed to fetch courses: {e}")
            raise
    
    async def get_course_assignments(self, course_id: str) -> List[ClassroomAssignment]:
        """
        Fetch all assignments (coursework) for a specific course.
        
        Args:
            course_id (str): The ID of the course
            
        Returns:
            List[ClassroomAssignment]: List of assignments from the course
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            logger.info(f"Fetching assignments for course: {course_id}")
            
            assignments = []
            page_token = None
            
            while True:
                results = self.service.courses().courseWork().list(
                    courseId=course_id,
                    pageToken=page_token,
                    pageSize=100,
                    courseWorkStates=['PUBLISHED']
                ).execute()
                
                batch_assignments = results.get('courseWork', [])
                
                # Convert to our ClassroomAssignment model
                for assignment_data in batch_assignments:
                    try:
                        assignment = self._convert_to_classroom_assignment(assignment_data, course_id)
                        assignments.append(assignment)
                    except Exception as e:
                        logger.warning(f"Failed to convert assignment {assignment_data.get('id', 'unknown')}: {e}")
                        continue
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(assignments)} assignments in course {course_id}")
            return assignments
            
        except HttpError as e:
            logger.error(f"Failed to fetch assignments for course {course_id}: {e}")
            raise
    
    def _convert_to_classroom_assignment(self, assignment_data: dict, course_id: str) -> ClassroomAssignment:
        """
        Convert Google Classroom API assignment data to our ClassroomAssignment model.
        
        Args:
            assignment_data (dict): Raw assignment data from Classroom API
            course_id (str): The course ID
            
        Returns:
            ClassroomAssignment: Converted assignment object
        """
        from datetime import datetime
        
        # Parse creation and update times
        creation_time = datetime.fromisoformat(
            assignment_data.get('creationTime', '').replace('Z', '+00:00')
        )
        update_time = datetime.fromisoformat(
            assignment_data.get('updateTime', '').replace('Z', '+00:00')
        )
        
        # Parse due date if available
        due_date = None
        due_date_data = assignment_data.get('dueDate')
        due_time_data = assignment_data.get('dueTime')
        
        if due_date_data:
            try:
                year = due_date_data.get('year')
                month = due_date_data.get('month')
                day = due_date_data.get('day')
                
                hour = 23
                minute = 59
                
                if due_time_data:
                    hour = due_time_data.get('hours', 23)
                    minute = due_time_data.get('minutes', 59)
                
                due_date = datetime(year, month, day, hour, minute)
            except Exception as e:
                logger.warning(f"Failed to parse due date for assignment {assignment_data.get('id')}: {e}")
        
        # Extract materials/attachments
        materials = assignment_data.get('materials', [])
        
        return ClassroomAssignment(
            id=assignment_data['id'],
            course_id=course_id,
            title=assignment_data.get('title', 'Untitled Assignment'),
            description=assignment_data.get('description', ''),
            creation_time=creation_time,
            update_time=update_time,
            due_date=due_date,
            materials=materials,
            state=assignment_data.get('state', 'PUBLISHED')
        )
    
    async def get_assignment_details(self, course_id: str, assignment_id: str) -> Optional[dict]:
        """
        Get detailed information about a specific assignment.
        
        Args:
            course_id (str): The course ID
            assignment_id (str): The assignment ID
            
        Returns:
            Optional[dict]: Assignment details or None if not found
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            logger.info(f"Fetching details for assignment: {assignment_id}")
            
            assignment = self.service.courses().courseWork().get(
                courseId=course_id,
                id=assignment_id
            ).execute()
            
            return assignment
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Assignment {assignment_id} not found in course {course_id}")
                return None
            logger.error(f"Failed to fetch assignment details: {e}")
            raise
    
    async def get_course_details(self, course_id: str) -> dict:
        """
        Get detailed information about a specific course.
        
        Args:
            course_id (str): The course ID
            
        Returns:
            dict: Course details including name, description, and teachers
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            logger.info(f"Fetching details for course: {course_id}")
            
            course = self.service.courses().get(id=course_id).execute()
            
            # Also fetch teachers for the course
            teachers = self.service.courses().teachers().list(courseId=course_id).execute()
            course['teachers'] = teachers.get('teachers', [])
            
            return course
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Course {course_id} not found")
                return {'id': course_id, 'name': 'Unknown Course', 'teachers': []}
            logger.error(f"Failed to fetch course details: {e}")
            raise
    
    def is_authenticated(self) -> bool:
        """Check if the client is properly authenticated"""
        return self.service is not None and self.auth_manager.is_authenticated()