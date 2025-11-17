from fastapi import APIRouter
from app.api.v1.endpoints import assignments, solutions, auth, users, health, classroom

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(solutions.router, prefix="/assignments", tags=["solutions"])
api_router.include_router(classroom.router, prefix="/classroom", tags=["classroom"])