from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from app.core.database import get_database

class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the MongoDB collection"""
        db = await get_database()
        return db[self.collection_name]
    
    async def create(self, document: Dict[str, Any]) -> str:
        """Create a new document"""
        collection = await self.get_collection()
        result = await collection.insert_one(document)
        return str(result.inserted_id)
    
    async def get_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        collection = await self.get_collection()
        document = await collection.find_one({"_id": ObjectId(document_id)})
        return document
    
    async def update(self, document_id: str, update_data: Dict[str, Any]) -> bool:
        """Update document by ID"""
        collection = await self.get_collection()
        result = await collection.update_one(
            {"_id": ObjectId(document_id)}, 
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def delete(self, document_id: str) -> bool:
        """Delete document by ID"""
        collection = await self.get_collection()
        result = await collection.delete_one({"_id": ObjectId(document_id)})
        return result.deleted_count > 0
    
    async def find(self, filter_dict: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Find documents with filter"""
        collection = await self.get_collection()
        cursor = collection.find(filter_dict).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def count(self, filter_dict: Dict[str, Any] = None) -> int:
        """Count documents"""
        collection = await self.get_collection()
        if filter_dict is None:
            filter_dict = {}
        return await collection.count_documents(filter_dict)