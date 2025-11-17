from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__("users")
    
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user"""
        user_data["created_at"] = datetime.utcnow()
        user_data["last_login"] = datetime.utcnow()
        return await self.create(user_data)
    
    async def get_user_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Google ID"""
        collection = await self.get_collection()
        return await collection.find_one({"google_id": google_id})
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        collection = await self.get_collection()
        return await collection.find_one({"email": email})
    
    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        return await self.update(user_id, {"last_login": datetime.utcnow()})
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user with arbitrary data"""
        return await self.update(user_id, update_data)
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        return await self.update(user_id, {"preferences": preferences})
    
    async def add_classroom_course(self, user_id: str, course_data: Dict[str, Any]) -> bool:
        """Add a Google Classroom course to user"""
        collection = await self.get_collection()
        result = await collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$addToSet": {"classroom_courses": course_data}}
        )
        return result.modified_count > 0
    
    async def remove_classroom_course(self, user_id: str, course_id: str) -> bool:
        """Remove a Google Classroom course from user"""
        collection = await self.get_collection()
        result = await collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"classroom_courses": {"id": course_id}}}
        )
        return result.modified_count > 0