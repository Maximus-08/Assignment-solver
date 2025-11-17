from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.repositories.base import BaseRepository

class SolutionRepository(BaseRepository):
    def __init__(self):
        super().__init__("solutions")
    
    async def create_solution(self, solution_data: Dict[str, Any]) -> str:
        """Create a new solution"""
        solution_data["created_at"] = datetime.utcnow()
        return await self.create(solution_data)
    
    async def get_solution_by_assignment_id(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """Get solution for a specific assignment"""
        collection = await self.get_collection()
        return await collection.find_one({"assignment_id": ObjectId(assignment_id)})
    
    async def update_solution_rating(self, solution_id: str, rating: int) -> bool:
        """Update solution feedback rating"""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        return await self.update(solution_id, {"feedback_rating": rating})
    
    async def get_solutions_by_subject(self, subject_area: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get solutions by subject area"""
        return await self.find({"subject_area": subject_area}, skip=skip, limit=limit)
    
    async def get_solutions_by_confidence(self, min_confidence: float, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get solutions with confidence score above threshold"""
        filter_dict = {"confidence_score": {"$gte": min_confidence}}
        return await self.find(filter_dict, skip=skip, limit=limit)
    
    async def mark_quality_validated(self, solution_id: str, validated: bool = True) -> bool:
        """Mark solution as quality validated"""
        return await self.update(solution_id, {"quality_validated": validated})