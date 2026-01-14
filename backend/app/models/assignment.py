from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId

class AssignmentSource(str, Enum):
    GOOGLE_CLASSROOM = "google_classroom"
    MANUAL_UPLOAD = "manual_upload"

class AssignmentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AssignmentType(str, Enum):
    PROBLEM_SET = "problem_set"
    ESSAY = "essay"
    LAB_REPORT = "lab_report"
    SHORT_ANSWER = "short_answer"
    MULTIPLE_CHOICE = "multiple_choice"
    PROJECT = "project"
    PRESENTATION = "presentation"
    GENERAL = "general"

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema

class AttachmentModel(BaseModel):
    filename: str
    file_type: str
    storage_url: str
    size_bytes: int
    content_extracted: bool = False

class AssignmentModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    google_classroom_id: Optional[str] = None
    title: str
    description: str
    subject: Optional[str] = None  # Made optional - can be auto-detected
    course_name: str
    instructor: Optional[str] = None
    due_date: Optional[datetime] = None
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    source: AssignmentSource
    status: AssignmentStatus = AssignmentStatus.PENDING
    assignment_type: AssignmentType = AssignmentType.GENERAL
    attachments: List[AttachmentModel] = []
    
    # Duplicate detection fields
    content_hash: Optional[str] = None
    content_embedding: Optional[List[float]] = None
    is_duplicate_of: Optional[str] = None
    similarity_score: Optional[float] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }

class AssignmentCreate(BaseModel):
    title: str
    description: str
    subject: Optional[str] = None  # Optional - will be auto-detected if not provided
    course_name: str = "Manual Upload"
    instructor: Optional[str] = None
    due_date: Optional[datetime] = None
    assignment_type: AssignmentType = AssignmentType.GENERAL

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[AssignmentStatus] = None