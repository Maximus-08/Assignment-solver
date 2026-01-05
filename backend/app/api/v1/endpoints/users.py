from fastapi import APIRouter, HTTPException, Header, status as http_status
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.repositories.user import UserRepository
from app.core.config import settings

router = APIRouter()

class GoogleCredentialsResponse(BaseModel):
    user_id: str
    email: str
    google_access_token: Optional[str]
    google_refresh_token: Optional[str]
    token_expires_at: Optional[datetime]

class UserListResponse(BaseModel):
    id: str
    email: str
    name: str

@router.get("/", response_model=dict)
async def list_users():
    """Get list of all users (minimal info for agent processing)"""
    try:
        user_repo = UserRepository()
        collection = await user_repo.get_collection()
        users_cursor = collection.find({}, {"_id": 1, "email": 1, "name": 1})
        users = []
        async for user in users_cursor:
            users.append({
                "id": str(user["_id"]),
                "email": user.get("email"),
                "name": user.get("name")
            })
        return {"users": users}
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )

@router.get("/profile")
async def get_user_profile():
    """Get current user profile"""
    return {"message": "User profile endpoint - to be implemented"}

@router.put("/profile")
async def update_user_profile():
    """Update user profile"""
    return {"message": "Update user profile - to be implemented"}

@router.get("/{user_id}/google-credentials", response_model=GoogleCredentialsResponse)
async def get_user_google_credentials(
    user_id: str,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """
    Get user's Google OAuth credentials for agent use.
    Requires valid API key in X-API-Key header.
    """
    # Verify API key (from agent's BACKEND_API_KEY)
    if not settings.BACKEND_API_KEY or x_api_key != settings.BACKEND_API_KEY:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Get user data
    user_repo = UserRepository()
    user_data = await user_repo.get_by_id(user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return Google credentials
    return GoogleCredentialsResponse(
        user_id=str(user_data["_id"]),
        email=user_data["email"],
        google_access_token=user_data.get("google_access_token"),
        google_refresh_token=user_data.get("google_refresh_token"),
        token_expires_at=user_data.get("token_expires_at")
    )
