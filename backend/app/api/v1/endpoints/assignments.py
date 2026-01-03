from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status as http_status, Depends, Query, UploadFile, File, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import os
import uuid
import aiofiles
from pathlib import Path
from bson import ObjectId
from app.core.deps import get_current_user
from app.models.user import UserModel
from app.models.assignment import AssignmentModel, AssignmentCreate, AssignmentUpdate, AssignmentSource, AssignmentStatus, AttachmentModel

from app.repositories.assignment import AssignmentRepository
from app.repositories.solution import SolutionRepository

from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

class AssignmentResponse(BaseModel):
    id: str
    title: str
    description: str
    subject: str
    course_name: str
    instructor: Optional[str]
    due_date: Optional[datetime]
    upload_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    source: AssignmentSource
    status: AssignmentStatus
    assignment_type: str
    attachments: List[Dict[str, Any]] = []

class AssignmentListResponse(BaseModel):
    assignments: List[AssignmentResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class SearchResponse(BaseModel):
    assignments: List[AssignmentResponse]
    query: str
    total: int

@router.get("/", response_model=Dict[str, Any])
async def get_assignments(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    status: Optional[AssignmentStatus] = Query(None, description="Filter by status"),
    source: Optional[AssignmentSource] = Query(None, description="Filter by source"),
    assignment_type: Optional[str] = Query(None, description="Filter by assignment type"),
    date_from: Optional[datetime] = Query(None, description="Filter assignments from date"),
    date_to: Optional[datetime] = Query(None, description="Filter assignments to date"),
    current_user: UserModel = Depends(get_current_user)
):
    """Get all assignments with pagination and filtering"""
    try:
        assignment_repo = AssignmentRepository()
        skip = (page - 1) * per_page
        
        # Build filters
        filters = {}
        if subject:
            filters["subject"] = subject
        if status:
            filters["status"] = status
        if source:
            filters["source"] = source
        if assignment_type:
            filters["assignment_type"] = assignment_type
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        
        # Get filtered assignments
        if filters:
            assignments_data = await assignment_repo.filter_assignments(
                user_id=str(current_user.id),
                filters=filters,
                skip=skip,
                limit=per_page
            )
        else:
            assignments_data = await assignment_repo.get_assignments_by_user(
                user_id=str(current_user.id),
                skip=skip,
                limit=per_page
            )
        
        # Convert to response format
        assignments = []
        for assignment_data in assignments_data:
            assignment_data["id"] = str(assignment_data["_id"])
            assignments.append(AssignmentResponse(**assignment_data))
        
        # Get total count for pagination
        user_id_str = str(current_user.id)
        total_count = await assignment_repo.count({"user_id": user_id_str})
        
        logger.info(f"Query: user_id={user_id_str}, Found {len(assignments)} assignments (total {total_count})")
        logger.info(f"User object ID type: {type(current_user.id)}, value: {current_user.id}")
        
        response_data = {
            "assignments": assignments,
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "has_next": (skip + per_page) < total_count,
            "has_prev": page > 1
        }
        
        logger.info(f"Returning response with {len(assignments)} assignments")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Failed to retrieve assignments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve assignments: {str(e)}"
        )

@router.post("/cleanup-duplicates")
async def cleanup_duplicates(
    current_user: UserModel = Depends(get_current_user)
):
    """Remove duplicate assignments, keeping only the oldest one for each unique assignment"""
    try:
        assignment_repo = AssignmentRepository()
        collection = await assignment_repo.get_collection()
        
        # Get ALL assignments for this user
        all_assignments = await collection.find({
            "user_id": str(current_user.id)
        }).sort("created_at", 1).to_list(length=None)
        
        logger.info(f"Found {len(all_assignments)} total assignments for user {current_user.id}")
        
        # Group by title
        seen_titles = {}
        ids_to_delete = []
        
        for assignment in all_assignments:
            title = assignment.get("title", "")
            if title in seen_titles:
                # This is a duplicate, mark for deletion
                ids_to_delete.append(assignment["_id"])
                logger.info(f"Marking duplicate for deletion: {assignment['_id']} (title: {title}, source: {assignment.get('source', 'unknown')})")
            else:
                # First time seeing this title, keep it
                seen_titles[title] = assignment["_id"]
        
        # Delete all duplicates
        total_deleted = 0
        if ids_to_delete:
            result = await collection.delete_many({"_id": {"$in": ids_to_delete}})
            total_deleted = result.deleted_count
            logger.info(f"Cleaned {total_deleted} duplicate assignments for user {current_user.id}")
        
        return {
            "message": f"Cleaned up {total_deleted} duplicate assignments",
            "deleted_count": total_deleted
        }
    except Exception as e:
        logger.error(f"Error cleaning duplicates: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup duplicates: {str(e)}"
        )

@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get specific assignment by ID"""
    try:
        assignment_repo = AssignmentRepository()
        assignment_data = await assignment_repo.get_by_id(assignment_id)
        
        if not assignment_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Check if user owns this assignment
        if assignment_data["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Auto-fix status: If solution exists but status is failed/processing, update to completed
        current_status = assignment_data.get("status")
        if current_status in ["failed", "processing"]:
            solution_repo = SolutionRepository()
            solution = await solution_repo.get_solution_by_assignment_id(assignment_id)
            if solution:
                logger.info(f"Auto-fixing status for assignment {assignment_id}: {current_status} -> completed")
                await assignment_repo.update(assignment_id, {"status": "completed"})
                assignment_data["status"] = "completed"
        
        assignment_data["id"] = str(assignment_data["_id"])
        return AssignmentResponse(**assignment_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve assignment: {str(e)}"
        )

@router.get("/_internal/{assignment_id}", response_model=AssignmentResponse, include_in_schema=False)
async def get_assignment_internal(
    assignment_id: str,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Internal endpoint for agent to fetch assignment by ID (requires API key)"""
    try:
        # Validate API key
        if not settings.BACKEND_API_KEY or x_api_key != settings.BACKEND_API_KEY:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        assignment_repo = AssignmentRepository()
        assignment_data = await assignment_repo.get_by_id(assignment_id)
        
        if not assignment_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        assignment_data["id"] = str(assignment_data["_id"])
        return AssignmentResponse(**assignment_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve assignment: {str(e)}"
        )

@router.put("/_internal/{assignment_id}/status", response_model=dict, include_in_schema=False)
async def update_assignment_status_internal(
    assignment_id: str,
    status_data: dict,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Internal endpoint for agent to update assignment status (requires API key)"""
    try:
        # Validate API key
        if not settings.BACKEND_API_KEY or x_api_key != settings.BACKEND_API_KEY:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        assignment_repo = AssignmentRepository()
        
        # Check if assignment exists
        existing_assignment = await assignment_repo.get_by_id(assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Update status
        update_data = {
            "status": status_data.get("status"),
            "updated_at": datetime.utcnow()
        }
        await assignment_repo.update(assignment_id, update_data)
        
        return {"message": "Status updated successfully", "assignment_id": assignment_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update assignment status: {str(e)}"
        )

@router.post("/{assignment_id}/reset-status")
async def reset_assignment_status(
    assignment_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Reset assignment status to pending (useful for stuck assignments)"""
    try:
        assignment_repo = AssignmentRepository()
        
        # Check if assignment exists and user owns it
        existing_assignment = await assignment_repo.get_by_id(assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if existing_assignment["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Reset status to pending
        await assignment_repo.update(assignment_id, {
            "status": "pending",
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"Reset assignment {assignment_id} status to pending")
        
        return {
            "message": "Assignment status reset to pending",
            "assignment_id": assignment_id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset assignment status: {str(e)}"
        )

@router.post("/", response_model=AssignmentResponse)
async def create_assignment(
    assignment_create: AssignmentCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """Create new assignment (manual upload)"""
    try:
        assignment_repo = AssignmentRepository()
        
        # Always run cleanup on manual uploads to remove any existing duplicates
        logger.info(f"Running duplicate cleanup for user {current_user.id}")
        collection = await assignment_repo.get_collection()
        
        # Get ALL assignments for this user (not just MANUAL_UPLOAD)
        all_assignments = await collection.find({
            "user_id": str(current_user.id)
        }).sort("created_at", 1).to_list(length=None)
        
        logger.info(f"Found {len(all_assignments)} total assignments")
        
        # Group by title
        seen_titles = {}
        ids_to_delete = []
        
        for assignment in all_assignments:
            title = assignment.get("title", "")
            if title in seen_titles:
                # This is a duplicate, mark for deletion
                ids_to_delete.append(assignment["_id"])
                logger.info(f"Marking duplicate for deletion: {assignment['_id']} (title: {title}, source: {assignment.get('source', 'unknown')})")
            else:
                # First time seeing this title, keep it
                seen_titles[title] = assignment["_id"]
        
        # Delete all duplicates
        if ids_to_delete:
            result = await collection.delete_many({"_id": {"$in": ids_to_delete}})
            logger.info(f"Auto-cleaned {result.deleted_count} duplicate assignments for user {current_user.id}")
        else:
            logger.info(f"No duplicates found to clean for user {current_user.id}")
        
        # Check for duplicate assignment (within last 5 minutes)
        existing = await assignment_repo.find_duplicate(
            user_id=str(current_user.id),
            title=assignment_create.title,
            description=assignment_create.description or "",
            subject=assignment_create.subject,
            minutes=5
        )
        
        if existing:
            logger.info(f"Duplicate assignment detected for user {current_user.id}, returning existing assignment {existing['_id']}")
            existing["id"] = str(existing["_id"])
            return AssignmentResponse(**existing)
        
        # Prepare assignment data - use model_dump() instead of dict() for Pydantic v2
        assignment_data = assignment_create.model_dump()
        now = datetime.utcnow()
        assignment_data.update({
            "user_id": str(current_user.id),
            "source": AssignmentSource.MANUAL_UPLOAD,
            "status": AssignmentStatus.PENDING,
            "attachments": [],
            "upload_date": now,
            "created_at": now,
            "updated_at": now
        })
        
        # Create assignment
        assignment_id = await assignment_repo.create_assignment(assignment_data)
        
        # Retrieve created assignment
        created_assignment = await assignment_repo.get_by_id(assignment_id)
        created_assignment["id"] = str(created_assignment["_id"])
        
        return AssignmentResponse(**created_assignment)
        
    except Exception as e:
        logger.error(f"Failed to create assignment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create assignment: {str(e)}"
        )

@router.put("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: str,
    assignment_update: AssignmentUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """Update assignment"""
    try:
        assignment_repo = AssignmentRepository()
        
        # Check if assignment exists and user owns it
        existing_assignment = await assignment_repo.get_by_id(assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if existing_assignment["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Update assignment
        update_data = {k: v for k, v in assignment_update.dict().items() if v is not None}
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            await assignment_repo.update(assignment_id, update_data)
        
        # Return updated assignment
        updated_assignment = await assignment_repo.get_by_id(assignment_id)
        updated_assignment["id"] = str(updated_assignment["_id"])
        
        return AssignmentResponse(**updated_assignment)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update assignment: {str(e)}"
        )

@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete assignment"""
    try:
        assignment_repo = AssignmentRepository()
        
        # Check if assignment exists and user owns it
        existing_assignment = await assignment_repo.get_by_id(assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if existing_assignment["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Delete assignment
        await assignment_repo.delete(assignment_id)
        
        return {"message": "Assignment deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete assignment: {str(e)}"
        )

@router.get("/search", response_model=SearchResponse)
async def search_assignments(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserModel = Depends(get_current_user)
):
    """Search assignments by query"""
    try:
        assignment_repo = AssignmentRepository()
        skip = (page - 1) * per_page
        
        # Search assignments
        assignments_data = await assignment_repo.search_assignments(
            user_id=str(current_user.id),
            query=q,
            skip=skip,
            limit=per_page
        )
        
        # Convert to response format
        assignments = []
        for assignment_data in assignments_data:
            assignment_data["id"] = str(assignment_data["_id"])
            assignments.append(AssignmentResponse(**assignment_data))
        
        return SearchResponse(
            assignments=assignments,
            query=q,
            total=len(assignments)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search assignments: {str(e)}"
        )



class AttachmentResponse(BaseModel):
    filename: str
    file_type: str
    size_bytes: int
    upload_date: datetime

class AttachmentUploadResponse(BaseModel):
    message: str
    attachment: AttachmentResponse



@router.post("/{assignment_id}/attachments", response_model=AttachmentUploadResponse)
async def upload_attachment(
    assignment_id: str,
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user)
):
    """Upload file attachment to assignment"""
    try:
        assignment_repo = AssignmentRepository()
        
        # Check if assignment exists and user owns it
        existing_assignment = await assignment_repo.get_by_id(assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if existing_assignment["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Validate file size
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Validate file type (documents and images)
        allowed_types = {
            'application/pdf', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain', 'text/csv',
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
        }
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not supported. Allowed types: documents and images"
            )
        
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.UPLOAD_DIR) / "assignments" / assignment_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create attachment data
        attachment_data = {
            "filename": file.filename,
            "file_type": file.content_type,
            "storage_url": str(file_path),
            "size_bytes": len(content),
            "content_extracted": False
        }
        
        # Add attachment to assignment
        await assignment_repo.add_attachment(assignment_id, attachment_data)
        
        return AttachmentUploadResponse(
            message="File uploaded successfully",
            attachment=AttachmentResponse(
                filename=file.filename,
                file_type=file.content_type,
                size_bytes=len(content),
                upload_date=datetime.utcnow()
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload attachment: {str(e)}"
        )

@router.get("/{assignment_id}/attachments")
async def list_attachments(
    assignment_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """List all attachments for an assignment"""
    try:
        assignment_repo = AssignmentRepository()
        
        # Check if assignment exists and user owns it
        existing_assignment = await assignment_repo.get_by_id(assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if existing_assignment["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        attachments = existing_assignment.get("attachments", [])
        
        return {
            "attachments": attachments,
            "total": len(attachments)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list attachments: {str(e)}"
        )

@router.get("/{assignment_id}/attachments/{filename}")
async def download_attachment(
    assignment_id: str,
    filename: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Download attachment file"""
    try:
        assignment_repo = AssignmentRepository()
        
        # Check if assignment exists and user owns it
        existing_assignment = await assignment_repo.get_by_id(assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if existing_assignment["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Find attachment by filename
        attachments = existing_assignment.get("attachments", [])
        attachment = None
        for att in attachments:
            if att["filename"] == filename:
                attachment = att
                break
        
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found"
            )
        
        # Check if file exists
        file_path = Path(attachment["storage_url"])
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )
        
        return FileResponse(
            path=str(file_path),
            filename=attachment["filename"],
            media_type=attachment["file_type"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download attachment: {str(e)}"
        )

@router.delete("/{assignment_id}/attachments/{filename}")
async def delete_attachment(
    assignment_id: str,
    filename: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete attachment file"""
    try:
        assignment_repo = AssignmentRepository()
        
        # Check if assignment exists and user owns it
        existing_assignment = await assignment_repo.get_by_id(assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if existing_assignment["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Find attachment by filename
        attachments = existing_assignment.get("attachments", [])
        attachment_to_remove = None
        for att in attachments:
            if att["filename"] == filename:
                attachment_to_remove = att
                break
        
        if not attachment_to_remove:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found"
            )
        
        # Remove file from disk
        file_path = Path(attachment_to_remove["storage_url"])
        if file_path.exists():
            file_path.unlink()
        
        # Remove attachment from database
        collection = await assignment_repo.get_collection()
        await collection.update_one(
            {"_id": ObjectId(assignment_id)},
            {
                "$pull": {"attachments": {"filename": filename}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return {"message": "Attachment deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete attachment: {str(e)}"
        )

@router.get("/debug/count")
async def debug_assignment_count(
    current_user: UserModel = Depends(get_current_user)
):
    """Debug endpoint to check assignment count in database"""
    try:
        assignment_repo = AssignmentRepository()
        collection = await assignment_repo.get_collection()
        
        user_id_str = str(current_user.id)
        
        # Get total count with string
        total = await collection.count_documents({"user_id": user_id_str})
        
        # Get total count with ObjectId
        total_obj = await collection.count_documents({"user_id": current_user.id})
        
        # Get all documents to see actual user_id format
        all_assignments = await collection.find({}).limit(10).to_list(length=10)
        
        # Get all distinct user_ids to see format
        all_user_ids = await collection.distinct("user_id")
        
        # Get sample assignments with this user_id
        sample = await collection.find({"user_id": user_id_str}).limit(5).to_list(length=5)
        
        # Convert ObjectId to string for JSON serialization
        for doc in sample:
            doc["_id"] = str(doc["_id"])
            if isinstance(doc.get("user_id"), ObjectId):
                doc["user_id_type"] = "ObjectId"
                doc["user_id"] = str(doc["user_id"])
            else:
                doc["user_id_type"] = type(doc.get("user_id")).__name__
        
        # Check what format user_ids are stored in
        user_id_types = {}
        for assignment in all_assignments:
            uid = assignment.get("user_id")
            uid_type = type(uid).__name__
            if uid_type not in user_id_types:
                user_id_types[uid_type] = []
            user_id_types[uid_type].append(str(uid))
        
        return {
            "current_user_id": user_id_str,
            "current_user_id_type": type(current_user.id).__name__,
            "total_count_string_query": total,
            "total_count_objectid_query": total_obj,
            "all_user_ids_in_db": [str(uid) for uid in all_user_ids],
            "user_id_storage_types": user_id_types,
            "sample_assignments": sample,
            "total_assignments_in_db": await collection.count_documents({})
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug failed: {str(e)}"
        )