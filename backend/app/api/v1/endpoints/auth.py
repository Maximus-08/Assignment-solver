from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.core.oauth import google_oauth
from app.core.security import create_user_token
from app.repositories.user import UserRepository
from app.models.user import UserModel, UserCreate
from app.core.deps import get_current_user

router = APIRouter()

class GoogleTokenRequest(BaseModel):
    token: str
    access_token: str = None  # Google access token for Classroom API
    refresh_token: str = None  # Google refresh token
    expires_in: int = None  # Token expiration in seconds

class GoogleCodeRequest(BaseModel):
    code: str
    redirect_uri: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserModel

@router.post("/google/token", response_model=LoginResponse)
async def login_with_google_token(request: GoogleTokenRequest):
    """Authenticate user with Google OAuth token"""
    try:
        # Verify Google token and get user info
        google_user_info = await google_oauth.verify_google_token(request.token)
        
        # Add Google OAuth tokens to user info
        if request.access_token:
            google_user_info["google_access_token"] = request.access_token
        if request.refresh_token:
            google_user_info["google_refresh_token"] = request.refresh_token
        if request.expires_in:
            google_user_info["token_expires_at"] = datetime.utcnow() + timedelta(seconds=request.expires_in)
        
        # Check if user exists
        user_repo = UserRepository()
        existing_user = await user_repo.get_user_by_google_id(google_user_info["google_id"])
        
        if existing_user:
            # Update user with new tokens and last login
            update_data = {"last_login": datetime.utcnow()}
            if request.access_token:
                update_data["google_access_token"] = request.access_token
            if request.refresh_token:
                update_data["google_refresh_token"] = request.refresh_token
            if request.expires_in:
                update_data["token_expires_at"] = datetime.utcnow() + timedelta(seconds=request.expires_in)
            
            await user_repo.update_user(existing_user["_id"], update_data)
            user_data = await user_repo.get_by_id(existing_user["_id"])
            user = UserModel(**user_data)
        else:
            # Create new user
            user_create = UserCreate(**google_user_info)
            user_id = await user_repo.create_user(user_create.dict())
            user_data = await user_repo.get_by_id(user_id)
            user = UserModel(**user_data)
        
        # Create JWT token
        access_token = create_user_token(
            user_id=str(user.id),
            email=user.email,
            google_id=user.google_id
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/google/code", response_model=LoginResponse)
async def login_with_google_code(request: GoogleCodeRequest):
    """Authenticate user with Google OAuth authorization code"""
    try:
        # Exchange code for token
        token_response = await google_oauth.exchange_code_for_token(
            request.code, 
            request.redirect_uri
        )
        
        # Get user info using the access token
        google_user_info = await google_oauth.verify_google_token(
            token_response["access_token"]
        )
        
        # Check if user exists
        user_repo = UserRepository()
        existing_user = await user_repo.get_user_by_google_id(google_user_info["google_id"])
        
        if existing_user:
            # Update last login
            await user_repo.update_last_login(existing_user["_id"])
            user = UserModel(**existing_user)
        else:
            # Create new user
            user_create = UserCreate(**google_user_info)
            user_id = await user_repo.create_user(user_create.dict())
            user_data = await user_repo.get_by_id(user_id)
            user = UserModel(**user_data)
        
        # Create JWT token
        access_token = create_user_token(
            user_id=str(user.id),
            email=user.email,
            google_id=user.google_id
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/logout")
async def logout(current_user: UserModel = Depends(get_current_user)):
    """User logout (client-side token removal)"""
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserModel)
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    """Get current user information"""
    return current_user