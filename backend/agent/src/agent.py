import asyncio
import logging
import time
from typing import List, Optional, Dict
from .config import settings
from .models import ClassroomAssignment, ProcessedAssignment, GeneratedSolution
from .classroom_client import ClassroomClient
from .llm_provider import LLMProviderManager
from .backend_client import BackendClient, BackendAPIError
from .backend_auth import BackendAuthManager
from .logging_config import log_operation_metrics

logger = logging.getLogger(__name__)

class AutomationAgent:
    """Main automation agent for processing Google Classroom assignments"""
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.classroom_client = ClassroomClient()
        self.llm_provider = LLMProviderManager()  # Multi-provider LLM manager
        self.backend_client = BackendClient()
        self.backend_auth = None
    
    async def initialize(self):
        """Initialize all API clients and connections"""
        logger.info("Initializing automation agent...")
        
        # Initialize backend client first (needed for auth)
        backend_init_success = await self.backend_client.initialize()
        if not backend_init_success:
            raise RuntimeError("Failed to initialize backend API client")
        
        # Initialize backend auth manager
        self.backend_auth = BackendAuthManager(self.backend_client)
        
        # If user_id provided, try to authenticate with their Google credentials (optional)
        # This is only needed for Google Classroom sync, not for processing assignments
        if self.user_id:
            logger.info(f"Attempting to fetch Google credentials for user {self.user_id} from backend")
            credentials = await self.backend_auth.get_user_credentials(self.user_id)
            if credentials:
                logger.info(f"Google credentials found for user {self.user_id}, enabling Classroom sync")
                # Set credentials on classroom client
                self.classroom_client.set_credentials(credentials)
                await self.classroom_client.build_service()
            else:
                logger.info(f"No Google credentials found for user {self.user_id}, Classroom sync disabled")
                # This is OK - we can still process assignments without Google Classroom access
        else:
            # No user specified - will process all users
            logger.info("No specific user_id provided - will fetch credentials per user")
        
        # Initialize Google Gemini client
        llm_init_success = await self.llm_provider.initialize()
        if not llm_init_success:
            raise RuntimeError("Failed to initialize any LLM provider")
        
        logger.info("Agent initialization completed")
    
    async def cleanup(self):
        """Cleanup all API clients and connections"""
        logger.info("Cleaning up automation agent...")
        
        try:
            if self.backend_client:
                await self.backend_client.close()
        except Exception as e:
            logger.warning(f"Error closing backend client: {e}")
        
        logger.info("Agent cleanup completed")
    
    async def process_single_assignment(self, assignment_id: str):
        """Process a single assignment by ID"""
        logger.info(f"Processing single assignment: {assignment_id}")
        
        try:
            # Fetch assignment from backend
            assignment_data = await self.backend_client.get_assignment(assignment_id)
            
            if not assignment_data:
                raise ValueError(f"Assignment {assignment_id} not found")
            
            # Process the assignment
            await self._process_backend_assignment(assignment_data)
            
            logger.info(f"Successfully processed assignment {assignment_id}")
            
        except Exception as e:
            logger.error(f"Failed to process assignment {assignment_id}: {e}", exc_info=True)
            raise
    
    async def run_daily_sync(self):
        """Main workflow: fetch assignments for all users, generate solutions, upload results"""
        logger.info("Starting daily sync process...")
        
        try:
            # If specific user_id was provided, process only that user
            if self.user_id:
                logger.info(f"Processing assignments for user {self.user_id}")
                await self._process_user_assignments(self.user_id)
            else:
                # Process all users
                logger.info("Processing assignments for all users")
                await self._process_all_users()
            
            logger.info("Daily sync completed successfully")
            
        except Exception as e:
            logger.error(f"Daily sync failed: {e}")
            raise
    
    async def _process_all_users(self):
        """Fetch and process assignments for all users in the system"""
        try:
            # Get list of all users from backend
            users = await self.backend_client.get_all_users()
            logger.info(f"Found {len(users)} users to process")
            
            for user in users:
                user_id = user['id']
                try:
                    await self._process_user_assignments(user_id)
                except Exception as e:
                    logger.error(f"Failed to process assignments for user {user_id}: {e}")
                    # Continue with next user
                    
        except Exception as e:
            logger.error(f"Failed to fetch users: {e}")
            raise
    
    async def _process_user_assignments(self, user_id: str):
        """Process assignments for a specific user by fetching from backend DB"""
        logger.info(f"Processing assignments for user: {user_id}")
        
        try:
            # Fetch pending assignments for this user from backend
            assignments = await self._fetch_pending_assignments_from_backend(user_id)
            logger.info(f"Found {len(assignments)} pending assignments for user {user_id}")
            
            # Process each assignment through AI
            for assignment_data in assignments:
                await self._process_backend_assignment(assignment_data)
            
            logger.info(f"Completed processing for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to process user {user_id}: {e}")
            raise
    
    async def _fetch_pending_assignments_from_backend(self, user_id: str) -> List[Dict]:
        """Fetch pending assignments from backend API for a specific user"""
        logger.info(f"Fetching pending assignments from backend for user: {user_id}")
        
        try:
            # Call backend API to get pending assignments
            response = await self.backend_client.get_assignments(
                user_id=user_id,
                status="pending"
            )
            
            assignments = response.get('assignments', [])
            logger.info(f"Retrieved {len(assignments)} pending assignments from backend")
            return assignments
            
        except Exception as e:
            logger.error(f"Failed to fetch assignments from backend: {e}")
            raise
    
    async def _process_backend_assignment(self, assignment_data: Dict):
        """Process a single assignment from backend database"""
        assignment_id = assignment_data.get('id')
        title = assignment_data.get('title', 'Untitled')
        
        logger.info(f"Processing assignment: {title} (ID: {assignment_id})")
        
        try:
            # Update status to processing
            await self.backend_client.update_assignment_status(assignment_id, "processing")
            
            # Convert backend assignment to ProcessedAssignment format
            processed_assignment = self._convert_to_processed_assignment(assignment_data)
            
            # Generate AI solution
            solution = await self._generate_solution(processed_assignment)
            
            # Upload solution to backend
            await self._upload_solution_to_backend(assignment_id, solution)
            
            # Update status to completed
            await self.backend_client.update_assignment_status(assignment_id, "completed")
            
            logger.info(f"Successfully processed assignment: {title}")
            
        except Exception as e:
            logger.error(f"Failed to process assignment {title}: {e}")
            # Update status to failed
            try:
                await self.backend_client.update_assignment_status(assignment_id, "failed")
            except:
                pass
    
    def _convert_to_processed_assignment(self, assignment_data: Dict) -> ProcessedAssignment:
        """Convert backend assignment data to ProcessedAssignment format"""
        return ProcessedAssignment(
            id=assignment_data.get('id'),  # Backend assignment ID
            google_classroom_id=assignment_data.get('google_classroom_id'),
            title=assignment_data.get('title', 'Untitled'),
            description=assignment_data.get('description', ''),
            subject=assignment_data.get('subject', 'General'),
            course_name=assignment_data.get('course_name', 'Unknown'),
            instructor=assignment_data.get('instructor', 'Unknown'),
            due_date=assignment_data.get('due_date'),
            assignment_type=assignment_data.get('assignment_type', 'general'),
            user_id=assignment_data.get('user_id')
        )
    
    async def process_assignment(self, assignment: ClassroomAssignment):
        """Process a single assignment: generate solution and upload"""
        logger.info(f"Processing assignment: {assignment.title}")
        
        try:
            # 1. Extract assignment content and handle multimedia
            processed_assignment = await self._process_assignment_content(assignment)
            
            # 2. Generate AI solution
            solution = await self._generate_solution(processed_assignment)
            
            # 3. Upload to backend API
            await self._upload_results(processed_assignment, solution)
            
            logger.info(f"Successfully processed assignment: {assignment.title}")
            
        except Exception as e:
            logger.error(f"Failed to process assignment {assignment.title}: {e}")
            # Continue with other assignments
    
    async def _fetch_new_assignments(self) -> List[ClassroomAssignment]:
        """Fetch new assignments from Google Classroom"""
        logger.info("Fetching new assignments from Google Classroom...")
        
        try:
            # Get all courses the user has access to
            courses = await self.classroom_client.get_courses()
            logger.info(f"Found {len(courses)} courses")
            
            all_assignments = []
            
            # Fetch assignments from each course
            for course in courses:
                course_id = course['id']
                course_name = course.get('name', 'Unknown Course')
                
                try:
                    logger.info(f"Fetching assignments from course: {course_name}")
                    course_assignments = await self.classroom_client.get_course_assignments(course_id)
                    
                    # Filter for new assignments (created in the last 24 hours)
                    new_assignments = self._filter_new_assignments(course_assignments)
                    
                    if new_assignments:
                        logger.info(f"Found {len(new_assignments)} new assignments in {course_name}")
                        all_assignments.extend(new_assignments)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch assignments from course {course_name}: {e}")
                    continue
            
            logger.info(f"Total new assignments found: {len(all_assignments)}")
            return all_assignments
            
        except Exception as e:
            logger.error(f"Failed to fetch assignments: {e}")
            raise
    
    async def _process_assignment_content(self, assignment: ClassroomAssignment) -> ProcessedAssignment:
        """Process assignment content and extract relevant information"""
        logger.info(f"Processing content for assignment: {assignment.title}")
        
        try:
            # Get course details to extract subject and instructor information
            course_details = await self.classroom_client.get_course_details(assignment.course_id)
            
            # Extract subject from course name or description
            subject = self._extract_subject_from_course(course_details)
            
            # Determine assignment type based on content
            assignment_type = self._determine_assignment_type(assignment)
            
            # Process attachments and multimedia content
            processed_materials = await self._process_assignment_materials(assignment.materials)
            
            # Create processed assignment with extracted metadata
            processed_assignment = ProcessedAssignment(
                google_classroom_id=assignment.id,
                title=assignment.title,
                description=assignment.description,
                subject=subject,
                course_name=course_details.get('name', 'Unknown Course'),
                instructor=self._extract_instructor_name(course_details),
                due_date=assignment.due_date,
                assignment_type=assignment_type,
                user_id="default_user"  # Will be updated when user management is implemented
            )
            
            # Store processed materials for later use in solution generation
            processed_assignment.processed_materials = processed_materials
            
            logger.info(f"Successfully processed assignment: {assignment.title}")
            return processed_assignment
            
        except Exception as e:
            logger.error(f"Failed to process assignment content: {e}")
            # Return basic processed assignment as fallback
            return ProcessedAssignment(
                google_classroom_id=assignment.id,
                title=assignment.title,
                description=assignment.description,
                subject="General",
                course_name="Unknown Course",
                assignment_type="general",
                user_id="default_user"
            )
    
    async def _generate_solution(self, assignment: ProcessedAssignment) -> GeneratedSolution:
        """Generate AI solution using multi-provider LLM system"""
        logger.info(f"Generating solution for: {assignment.title}")
        
        try:
            # Use LLM provider manager with automatic failover
            solution = await self.llm_provider.generate_solution(assignment)
            
            logger.info(f"Successfully generated solution for: {assignment.title} "
                       f"(confidence: {solution.confidence_score:.2f})")
            
            return solution
            
        except Exception as e:
            logger.error(f"Failed to generate solution for {assignment.title}: {e}")
            
            # Return fallback solution to prevent complete failure
            return GeneratedSolution(
                assignment_id=assignment.id or assignment.google_classroom_id,
                content=f"Unable to generate solution automatically. Assignment: {assignment.title}",
                explanation="Solution generation failed due to technical issues. Please review manually.",
                step_by_step=["Review assignment requirements", "Research relevant concepts", "Develop solution approach"],
                reasoning="Fallback solution provided due to AI generation failure.",
                confidence_score=0.1,
                processing_time=0.0,
                subject_area=assignment.subject,
                quality_validated=False
            )
    
    async def _upload_results(self, assignment: ProcessedAssignment, solution: GeneratedSolution):
        """Upload processed assignment and solution to backend"""
        logger.info(f"Uploading results for: {assignment.title}")
        
        start_time = time.time()
        success = False
        
        try:
            # Upload assignment and solution using backend client
            result = await self.backend_client.upload_assignment_and_solution(assignment, solution)
            
            success = True
            duration = time.time() - start_time
            
            logger.info(f"Successfully uploaded results for: {assignment.title} "
                       f"(Assignment ID: {result['assignment_id']})")
            
            # Log operation metrics
            log_operation_metrics(
                operation="upload_results",
                duration=duration,
                success=True,
                details={
                    "assignment_title": assignment.title,
                    "assignment_id": result['assignment_id'],
                    "subject": assignment.subject,
                    "confidence_score": solution.confidence_score
                }
            )
            
            return result
            
        except BackendAPIError as e:
            duration = time.time() - start_time
            logger.error(f"Backend API error uploading {assignment.title}: {e}")
            
            # Log failure metrics
            log_operation_metrics(
                operation="upload_results",
                duration=duration,
                success=False,
                details={
                    "assignment_title": assignment.title,
                    "error_type": "BackendAPIError",
                    "error_message": str(e)
                }
            )
            raise
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Unexpected error uploading {assignment.title}: {e}")
            
            # Log failure metrics
            log_operation_metrics(
                operation="upload_results",
                duration=duration,
                success=False,
                details={
                    "assignment_title": assignment.title,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            raise
    
    async def _upload_solution_to_backend(self, assignment_id: str, solution: GeneratedSolution):
        """Upload solution to backend for an existing assignment"""
        logger.info(f"Uploading solution for assignment ID: {assignment_id}")
        
        try:
            # Upload solution using backend client
            await self.backend_client.upload_solution(assignment_id, solution)
            logger.info(f"Successfully uploaded solution for assignment {assignment_id}")
            
        except Exception as e:
            logger.error(f"Failed to upload solution: {e}")
            raise
    
    def _filter_new_assignments(self, assignments: List[ClassroomAssignment]) -> List[ClassroomAssignment]:
        """Filter assignments to only include new ones (created in last 24 hours)"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(days=1)
        new_assignments = []
        
        for assignment in assignments:
            # Check if assignment was created or updated recently
            if (assignment.creation_time > cutoff_time or 
                assignment.update_time > cutoff_time):
                new_assignments.append(assignment)
        
        return new_assignments
    
    def _extract_subject_from_course(self, course_details: dict) -> str:
        """Extract subject area from course information"""
        course_name = course_details.get('name', '').lower()
        description = course_details.get('description', '').lower()
        
        # Common subject mappings
        subject_keywords = {
            'mathematics': ['math', 'algebra', 'geometry', 'calculus', 'statistics'],
            'science': ['biology', 'chemistry', 'physics', 'science'],
            'english': ['english', 'literature', 'writing', 'language arts'],
            'history': ['history', 'social studies', 'government', 'civics'],
            'computer_science': ['computer', 'programming', 'coding', 'software'],
            'art': ['art', 'drawing', 'painting', 'design'],
            'music': ['music', 'band', 'orchestra', 'choir'],
            'physical_education': ['pe', 'physical education', 'gym', 'fitness']
        }
        
        # Check course name and description for subject keywords
        for subject, keywords in subject_keywords.items():
            for keyword in keywords:
                if keyword in course_name or keyword in description:
                    return subject
        
        # Default to general if no specific subject identified
        return 'general'
    
    def _determine_assignment_type(self, assignment: ClassroomAssignment) -> str:
        """Determine assignment type based on title and description"""
        title = assignment.title.lower()
        description = assignment.description.lower()
        
        # Check for common assignment type indicators
        if any(word in title or word in description for word in ['essay', 'paper', 'report', 'writing']):
            return 'essay'
        elif any(word in title or word in description for word in ['problem', 'exercise', 'homework', 'practice']):
            return 'problem_set'
        elif any(word in title or word in description for word in ['research', 'project', 'investigation']):
            return 'research'
        elif any(word in title or word in description for word in ['quiz', 'test', 'exam']):
            return 'assessment'
        elif any(word in title or word in description for word in ['lab', 'experiment']):
            return 'lab'
        else:
            return 'general'
    
    def _extract_instructor_name(self, course_details: dict) -> Optional[str]:
        """Extract instructor name from course details"""
        teachers = course_details.get('teachers', [])
        if teachers:
            # Get the first teacher's name
            teacher = teachers[0]
            profile = teacher.get('profile', {})
            name = profile.get('name', {})
            return name.get('fullName', 'Unknown Instructor')
        return None
    
    async def _process_assignment_materials(self, materials: List[dict]) -> List[dict]:
        """Process assignment materials and attachments"""
        processed_materials = []
        
        for material in materials:
            try:
                processed_material = await self._process_single_material(material)
                if processed_material:
                    processed_materials.append(processed_material)
            except Exception as e:
                logger.warning(f"Failed to process material: {e}")
                continue
        
        return processed_materials
    
    async def _process_single_material(self, material: dict) -> Optional[dict]:
        """Process a single material/attachment"""
        material_type = None
        content = None
        metadata = {}
        
        # Handle different material types
        if 'driveFile' in material:
            # Google Drive file
            drive_file = material['driveFile']
            material_type = 'drive_file'
            metadata = {
                'title': drive_file.get('driveFile', {}).get('title', 'Unknown File'),
                'mime_type': drive_file.get('driveFile', {}).get('mimeType', ''),
                'file_id': drive_file.get('driveFile', {}).get('id', '')
            }
            
            # Extract text content if it's a document
            if 'document' in metadata['mime_type'] or 'text' in metadata['mime_type']:
                content = await self._extract_document_content(metadata['file_id'])
        
        elif 'link' in material:
            # Web link
            link = material['link']
            material_type = 'link'
            metadata = {
                'url': link.get('url', ''),
                'title': link.get('title', 'Web Link')
            }
        
        elif 'youtubeVideo' in material:
            # YouTube video
            video = material['youtubeVideo']
            material_type = 'youtube_video'
            metadata = {
                'video_id': video.get('id', ''),
                'title': video.get('title', 'YouTube Video'),
                'thumbnail_url': video.get('thumbnailUrl', '')
            }
        
        elif 'form' in material:
            # Google Form
            form = material['form']
            material_type = 'form'
            metadata = {
                'form_url': form.get('formUrl', ''),
                'title': form.get('title', 'Google Form')
            }
        
        if material_type:
            return {
                'type': material_type,
                'content': content,
                'metadata': metadata
            }
        
        return None
    
    async def _extract_document_content(self, file_id: str) -> Optional[str]:
        """Extract text content from Google Drive documents"""
        # This would require Google Drive API integration
        # For now, return placeholder - will be enhanced in future iterations
        logger.info(f"Document content extraction not yet implemented for file: {file_id}")
        return None