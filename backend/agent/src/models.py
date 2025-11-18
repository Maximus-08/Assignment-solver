from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class ClassroomAssignment(BaseModel):
    """Assignment data from Google Classroom API"""
    id: str
    course_id: str
    title: str
    description: str
    creation_time: datetime
    update_time: datetime
    due_date: Optional[datetime] = None
    materials: List[Dict[str, Any]] = []
    state: str
    
class ProcessedAssignment(BaseModel):
    """Assignment data processed for backend API"""
    id: Optional[str] = None  # Backend assignment ID
    google_classroom_id: Optional[str] = None
    title: str
    description: str
    subject: str
    course_name: str
    instructor: Optional[str] = None
    due_date: Optional[datetime] = None
    assignment_type: str
    user_id: Optional[str] = None
    processed_materials: List[Dict[str, Any]] = []
    
class GeneratedSolution(BaseModel):
    """AI-generated solution data"""
    assignment_id: str
    content: str
    explanation: str
    step_by_step: List[str]
    reasoning: str
    generated_by: str = "automation_agent"
    ai_model_used: str = "gemini-pro"
    confidence_score: float
    processing_time: float
    subject_area: str
    quality_validated: bool = False