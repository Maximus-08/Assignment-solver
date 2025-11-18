"""
Google Classroom API endpoints for syncing assignments from classroom.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.deps import get_current_user, get_assignment_repository
from app.models.user import UserModel
from app.models.assignment import AssignmentModel, AssignmentType, AssignmentStatus, AssignmentSource
from app.repositories.assignment import AssignmentRepository

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/sync")
async def sync_google_classroom(
    current_user: UserModel = Depends(get_current_user),
    assignment_repo: AssignmentRepository = Depends(get_assignment_repository)
) -> Dict:
    """
    Sync assignments from Google Classroom for the current user.
    Fetches all coursework from all courses and stores them in the database.
    """
    logger.info(f"Starting Google Classroom sync for user: {current_user.email}")
    
    # Check if user has Google credentials
    if not current_user.google_access_token:
        logger.error(f"User {current_user.email} has no Google credentials")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no Google credentials. Please sign in with Google."
        )
    
    try:
        # Build credentials from stored tokens
        from app.core.config import settings
        credentials = Credentials(
            token=current_user.google_access_token,
            refresh_token=current_user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=[
                'https://www.googleapis.com/auth/classroom.courses.readonly',
                'https://www.googleapis.com/auth/classroom.coursework.students.readonly'
            ]
        )
        
        # Build the Classroom API service
        service = build('classroom', 'v1', credentials=credentials)
        
        # Fetch all courses
        courses_result = service.courses().list(
            pageSize=100,
            courseStates=['ACTIVE']
        ).execute()
        
        courses = courses_result.get('courses', [])
        logger.info(f"Found {len(courses)} active courses")
        
        synced_count = 0
        skipped_count = 0
        
        # Iterate through each course and fetch coursework
        for course in courses:
            course_id = course['id']
            course_name = course.get('name', 'Unknown Course')
            
            try:
                # Fetch coursework for this course
                coursework_result = service.courses().courseWork().list(
                    courseId=course_id,
                    pageSize=100
                ).execute()
                
                coursework_items = coursework_result.get('courseWork', [])
                logger.info(f"Found {len(coursework_items)} assignments in course: {course_name}")
                
                for coursework in coursework_items:
                    # Check if assignment already exists
                    google_classroom_id = f"{course_id}_{coursework['id']}"
                    existing = await assignment_repo.find_by_google_classroom_id(
                        google_classroom_id, 
                        str(current_user.id)
                    )
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Parse due date
                    due_date = None
                    if 'dueDate' in coursework:
                        due_info = coursework['dueDate']
                        due_time = coursework.get('dueTime', {'hours': 23, 'minutes': 59})
                        due_date = datetime(
                            year=due_info['year'],
                            month=due_info['month'],
                            day=due_info['day'],
                            hour=due_time.get('hours', 23),
                            minute=due_time.get('minutes', 59)
                        )
                    
                    # Determine assignment type
                    work_type = coursework.get('workType', 'ASSIGNMENT')
                    assignment_type = _map_work_type_to_assignment_type(work_type)
                    
                    # Create new assignment
                    new_assignment = AssignmentModel(
                        user_id=str(current_user.id),
                        title=coursework.get('title', 'Untitled Assignment'),
                        description=coursework.get('description', ''),
                        subject=_extract_subject_from_course(course),
                        course_name=course_name,
                        instructor=course.get('ownerId', 'Unknown'),
                        due_date=due_date,
                        source=AssignmentSource.GOOGLE_CLASSROOM,
                        status=AssignmentStatus.PENDING,
                        assignment_type=assignment_type,
                        google_classroom_id=google_classroom_id,
                        attachments=[]
                    )
                    
                    # Save to database
                    assignment_dict = new_assignment.dict(by_alias=True, exclude={'id'})
                    logger.info(f"Saving assignment with user_id: {assignment_dict.get('user_id')}")
                    created_id = await assignment_repo.create(assignment_dict)
                    logger.info(f"Created assignment {created_id} for user {current_user.id}")
                    synced_count += 1
                    
            except HttpError as course_error:
                logger.error(f"Error fetching coursework for course {course_name}: {course_error}")
                continue
        
        # Auto-cleanup duplicates after sync
        try:
            collection = await assignment_repo.get_collection()
            pipeline = [
                {"$match": {"user_id": str(current_user.id), "google_classroom_id": {"$exists": True}}},
                {"$group": {
                    "_id": "$google_classroom_id",
                    "count": {"$sum": 1},
                    "ids": {"$push": "$_id"}
                }},
                {"$match": {"count": {"$gt": 1}}}
            ]
            duplicates = await collection.aggregate(pipeline).to_list(length=None)
            cleaned_count = 0
            for dup in duplicates:
                ids_to_delete = dup["ids"][1:]
                result = await collection.delete_many({"_id": {"$in": ids_to_delete}})
                cleaned_count += result.deleted_count
            if cleaned_count > 0:
                logger.info(f"Auto-cleaned {cleaned_count} duplicate assignments")
        except Exception as cleanup_error:
            logger.warning(f"Failed to auto-cleanup duplicates: {cleanup_error}")
        
        logger.info(f"Sync completed: {synced_count} new, {skipped_count} skipped")
        
        return {
            "success": True,
            "synced": synced_count,
            "skipped": skipped_count,
            "total_courses": len(courses)
        }
        
    except HttpError as e:
        logger.error(f"Google Classroom API error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Google Classroom: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


def _map_work_type_to_assignment_type(work_type: str) -> AssignmentType:
    """Map Google Classroom work type to our assignment type"""
    mapping = {
        'ASSIGNMENT': AssignmentType.PROBLEM_SET,
        'SHORT_ANSWER_QUESTION': AssignmentType.SHORT_ANSWER,
        'MULTIPLE_CHOICE_QUESTION': AssignmentType.MULTIPLE_CHOICE,
    }
    return mapping.get(work_type, AssignmentType.GENERAL)


def _extract_subject_from_course(course: Dict) -> str:
    """Extract subject from course information"""
    # Try to get from section or name
    section = course.get('section', '')
    name = course.get('name', '')
    
    # Common subject keywords
    subjects = [
        'Mathematics', 'Math', 'Science', 'English', 'History',
        'Physics', 'Chemistry', 'Biology', 'Computer Science',
        'Programming', 'Literature', 'Art', 'Music'
    ]
    
    for subject in subjects:
        if subject.lower() in name.lower() or subject.lower() in section.lower():
            return subject
    
    return 'General'
