from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from .assignment import PyObjectId

class SolutionModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    assignment_id: PyObjectId
    content: str
    explanation: str
    step_by_step: List[str] = []
    reasoning: str
    generated_by: str
    ai_model_used: str = "gemini-pro"
    confidence_score: float = 0.0
    processing_time: float = 0.0
    subject_area: str
    quality_validated: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    feedback_rating: Optional[int] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }

class SolutionCreate(BaseModel):
    assignment_id: str
    content: str
    explanation: str
    step_by_step: List[str] = []
    reasoning: str
    generated_by: str = "automation_agent"
    ai_model_used: str = "gemini-pro"
    confidence_score: float = 0.0
    processing_time: float = 0.0
    subject_area: str
    quality_validated: bool = False