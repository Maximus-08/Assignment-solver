from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_token
from app.core.config import settings
from app.repositories.user import UserRepository
from app.repositories.assignment import AssignmentRepository
from app.models.user import UserModel

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserModel:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    
    # Verify token
    payload = verify_token(token)
    
    # Extract user info from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # Get user from database
    user_repo = UserRepository()
    user_data = await user_repo.get_by_id(user_id)
    
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return UserModel(**user_data)

async def get_current_user_or_agent(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> UserModel:
    """Get current user from JWT token OR validate agent API key and get user from assignment"""
    
    # Try API key first (for agent)
    if x_api_key:
        # Validate agent API key
        expected_key = "GZKtvr03TKU1QnPdCA8Js5e4eP0x/DYxoU5Zhy7TDWQ="
        if x_api_key == expected_key:
            # For agent requests, we don't have a user context here
            # Return a system user or handle differently
            # For now, return None to indicate agent access
            return None
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
    
    # Try JWT token
    if credentials:
        return await get_current_user(credentials)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No authentication provided"
    )

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[UserModel]:
    """Get current user if token is provided, otherwise return None"""
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

def get_assignment_repository() -> AssignmentRepository:
    """Get assignment repository instance"""
    return AssignmentRepository()