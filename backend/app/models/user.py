from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from .assignment import PyObjectId

class CourseModel(BaseModel):
    id: str
    name: str
    section: str = ""
    description_heading: str = ""
    room: str = ""
    owner_id: str

class UserPreferences(BaseModel):
    auto_sync_enabled: bool = True
    notification_settings: Dict[str, Any] = {}
    preferred_ai_model: str = "gemini-pro"
    solution_detail_level: str = "detailed"

class UserModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    google_id: str
    email: EmailStr
    name: str
    profile_picture: str = ""
    google_access_token: Optional[str] = None
    google_refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    classroom_courses: List[CourseModel] = []
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }

class UserCreate(BaseModel):
    google_id: str
    email: EmailStr
    name: str
    profile_picture: str = ""
    google_access_token: Optional[str] = None
    google_refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    preferences: Optional[UserPreferences] = None