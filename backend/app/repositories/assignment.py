from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.repositories.base import BaseRepository
from app.models.assignment import AssignmentModel, AssignmentStatus, AssignmentSource

class AssignmentRepository(BaseRepository):
    def __init__(self):
        super().__init__("assignments")
    
    async def create_assignment(self, assignment_data: Dict[str, Any]) -> str:
        """Create a new assignment"""
        assignment_data["created_at"] = datetime.utcnow()
        assignment_data["updated_at"] = datetime.utcnow()
        return await self.create(assignment_data)
    
    async def get_assignments_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get assignments for a specific user"""
        collection = await self.get_collection()
        cursor = collection.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def search_assignments(self, user_id: str, query: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Search assignments by text query"""
        search_filter = {
            "user_id": user_id,
            "$text": {"$search": query}
        }
        return await self.find(search_filter, skip=skip, limit=limit)
    
    async def filter_assignments(self, user_id: str, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Filter assignments by various criteria"""
        filter_dict = {"user_id": user_id}
        
        if "subject" in filters:
            filter_dict["subject"] = {"$regex": filters["subject"], "$options": "i"}
        
        if "status" in filters:
            filter_dict["status"] = filters["status"]
        
        if "source" in filters:
            filter_dict["source"] = filters["source"]
        
        if "assignment_type" in filters:
            filter_dict["assignment_type"] = filters["assignment_type"]
        
        if "date_from" in filters:
            filter_dict["created_at"] = {"$gte": filters["date_from"]}
        
        if "date_to" in filters:
            if "created_at" not in filter_dict:
                filter_dict["created_at"] = {}
            filter_dict["created_at"]["$lte"] = filters["date_to"]
        
        collection = await self.get_collection()
        cursor = collection.find(filter_dict).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def update_assignment_status(self, assignment_id: str, status: AssignmentStatus) -> bool:
        """Update assignment status"""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        return await self.update(assignment_id, update_data)
    
    async def get_assignments_by_google_classroom_id(self, google_classroom_id: str) -> Optional[Dict[str, Any]]:
        """Get assignment by Google Classroom ID"""
        collection = await self.get_collection()
        return await collection.find_one({"google_classroom_id": google_classroom_id})
    
    async def find_by_google_classroom_id(self, google_classroom_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Find assignment by Google Classroom ID for a specific user"""
        collection = await self.get_collection()
        return await collection.find_one({
            "google_classroom_id": google_classroom_id,
            "user_id": user_id
        })
    
    async def get_pending_assignments(self) -> List[Dict[str, Any]]:
        """Get all pending assignments for processing"""
        return await self.find({"status": AssignmentStatus.PENDING})
    
    async def add_attachment(self, assignment_id: str, attachment_data: Dict[str, Any]) -> bool:
        """Add attachment to assignment"""
        collection = await self.get_collection()
        result = await collection.update_one(
            {"_id": ObjectId(assignment_id)},
            {
                "$push": {"attachments": attachment_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0