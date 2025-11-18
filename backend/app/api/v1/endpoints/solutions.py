from fastapi import APIRouter
from typing import List, Optional
from app.core.deps import get_current_user
from app.models.user import UserModel
from app.models.solution import SolutionModel, SolutionCreate
from app.repositories.solution import SolutionRepository
from app.repositories.assignment import AssignmentRepository
from fastapi import Depends, HTTPException, status, Query, BackgroundTasks, Header
from bson import ObjectId
import asyncio
import subprocess
import sys
from pathlib import Path
from app.core.logging import get_logger
from datetime import datetime

router = APIRouter()
logger = get_logger(__name__)

@router.get("/", response_model=List[dict])
async def get_solutions(
    subject_area: Optional[str] = Query(None, description="Filter by subject area"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserModel = Depends(get_current_user)
):
    """Get solutions with optional filtering"""
    try:
        solution_repo = SolutionRepository()
        skip = (page - 1) * per_page
        
        if subject_area:
            solutions = await solution_repo.get_solutions_by_subject(
                subject_area=subject_area,
                skip=skip,
                limit=per_page
            )
        elif min_confidence is not None:
            solutions = await solution_repo.get_solutions_by_confidence(
                min_confidence=min_confidence,
                skip=skip,
                limit=per_page
            )
        else:
            solutions = await solution_repo.find({}, skip=skip, limit=per_page)
        
        # Convert ObjectId to string for response
        for solution in solutions:
            solution["id"] = str(solution["_id"])
            solution["assignment_id"] = str(solution["assignment_id"])
        
        return solutions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve solutions: {str(e)}"
        )

@router.get("/{assignment_id}/solution", response_model=dict)
async def get_assignment_solution(
    assignment_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get solution for a specific assignment with explanations, step-by-step breakdowns, and reasoning"""
    try:
        logger.info(f"Fetching solution for assignment {assignment_id} by user {current_user.id}")
        
        # Validate assignment exists and user has access
        assignment_repo = AssignmentRepository()
        assignment = await assignment_repo.get_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Check if user has access to this assignment
        if str(assignment.get("user_id")) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Get solution for the assignment
        solution_repo = SolutionRepository()
        solution = await solution_repo.get_solution_by_assignment_id(assignment_id)
        
        if not solution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solution not found for this assignment"
            )
        
        # Convert ObjectId to string for response
        solution["id"] = str(solution["_id"])
        solution["assignment_id"] = str(solution["assignment_id"])
        del solution["_id"]  # Remove the original ObjectId field
        
        return solution
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve solution: {str(e)}"
        )

@router.post("/{assignment_id}/solution", response_model=dict)
async def create_assignment_solution(
    assignment_id: str,
    solution_data: SolutionCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """Upload solution from automation agent with explanations, step-by-step breakdowns, and reasoning"""
    try:
        # Validate assignment exists
        assignment_repo = AssignmentRepository()
        assignment = await assignment_repo.get_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Check if solution already exists
        solution_repo = SolutionRepository()
        existing_solution = await solution_repo.get_solution_by_assignment_id(assignment_id)
        
        if existing_solution:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solution already exists for this assignment"
            )
        
        # Validate required fields for comprehensive solutions
        if not solution_data.content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solution content is required"
            )
        
        if not solution_data.explanation.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solution explanation is required"
            )
        
        if not solution_data.reasoning.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solution reasoning is required"
            )
        
        # Create solution data
        solution_dict = solution_data.dict()
        solution_dict["assignment_id"] = ObjectId(assignment_id)
        
        # Create the solution
        solution_id = await solution_repo.create_solution(solution_dict)
        
        # Return created solution
        created_solution = await solution_repo.get_by_id(solution_id)
        created_solution["id"] = str(created_solution["_id"])
        created_solution["assignment_id"] = str(created_solution["assignment_id"])
        
        return created_solution
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create solution: {str(e)}"
        )

@router.post("/_internal/{assignment_id}/solution", response_model=dict, include_in_schema=False)
async def create_assignment_solution_internal(
    assignment_id: str,
    solution_data: SolutionCreate,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Internal endpoint for agent to upload solution (requires API key)"""
    try:
        # Validate API key
        expected_key = "GZKtvr03TKU1QnPdCA8Js5e4eP0x/DYxoU5Zhy7TDWQ="
        if x_api_key != expected_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Validate assignment exists
        assignment_repo = AssignmentRepository()
        assignment = await assignment_repo.get_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Check if solution already exists - if so, delete it first
        solution_repo = SolutionRepository()
        existing_solution = await solution_repo.get_solution_by_assignment_id(assignment_id)
        
        if existing_solution:
            await solution_repo.delete(str(existing_solution["_id"]))
        
        # Validate required fields
        if not solution_data.content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solution content is required"
            )
        
        # Create solution data
        solution_dict = solution_data.dict()
        solution_dict["assignment_id"] = ObjectId(assignment_id)
        solution_dict["created_at"] = datetime.utcnow()
        
        # Create the solution
        solution_id = await solution_repo.create_solution(solution_dict)
        
        # Return created solution
        created_solution = await solution_repo.get_by_id(solution_id)
        created_solution["id"] = str(created_solution["_id"])
        created_solution["assignment_id"] = str(created_solution["assignment_id"])
        
        return created_solution
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create solution: {str(e)}"
        )

@router.put("/{assignment_id}/solution/rating", response_model=dict)
async def update_solution_rating(
    assignment_id: str,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1 to 5"),
    current_user: UserModel = Depends(get_current_user)
):
    """Update feedback rating for a solution"""
    try:
        # Validate assignment exists and user has access
        assignment_repo = AssignmentRepository()
        assignment = await assignment_repo.get_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if str(assignment.get("user_id")) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Get solution
        solution_repo = SolutionRepository()
        solution = await solution_repo.get_solution_by_assignment_id(assignment_id)
        
        if not solution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solution not found for this assignment"
            )
        
        # Update rating
        solution_id = str(solution["_id"])
        success = await solution_repo.update_solution_rating(solution_id, rating)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update solution rating"
            )
        
        return {"message": "Solution rating updated successfully", "rating": rating}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update solution rating: {str(e)}"
        )

@router.post("/{assignment_id}/solve")
async def trigger_assignment_solution(
    assignment_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user)
):
    """Trigger the agent to solve a specific assignment"""
    try:
        # Validate assignment exists and user has access
        assignment_repo = AssignmentRepository()
        assignment = await assignment_repo.get_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if str(assignment.get("user_id")) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Check if solution already exists
        solution_repo = SolutionRepository()
        existing_solution = await solution_repo.get_solution_by_assignment_id(assignment_id)
        
        if existing_solution:
            return {
                "message": "Solution already exists for this assignment",
                "status": "completed"
            }
        
        # Update assignment status to processing
        await assignment_repo.update_assignment_status(assignment_id, "processing")
        
        # Trigger agent in background
        background_tasks.add_task(run_agent_for_assignment, assignment_id, str(current_user.id))
        
        return {
            "message": "Assignment processing started",
            "status": "processing",
            "assignment_id": assignment_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger assignment solution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger solution: {str(e)}"
        )

@router.post("/{assignment_id}/regenerate")
async def regenerate_solution(
    assignment_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete existing solution and regenerate a new one"""
    try:
        # Validate assignment exists and user has access
        assignment_repo = AssignmentRepository()
        assignment = await assignment_repo.get_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        if str(assignment.get("user_id")) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this assignment"
            )
        
        # Delete existing solution if any
        solution_repo = SolutionRepository()
        existing_solution = await solution_repo.get_solution_by_assignment_id(assignment_id)
        if existing_solution:
            await solution_repo.delete(str(existing_solution["_id"]))
            logger.info(f"Deleted existing solution for assignment {assignment_id}")
        
        # Update status to processing
        await assignment_repo.update_assignment_status(assignment_id, "processing")
        
        # Trigger agent in background
        background_tasks.add_task(run_agent_for_assignment, assignment_id, str(current_user.id))
        
        logger.info(f"Regeneration triggered for assignment {assignment_id}")
        
        return {
            "message": "Solution regeneration started",
            "status": "processing",
            "assignment_id": assignment_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate solution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate solution: {str(e)}"
        )

async def run_agent_for_assignment(assignment_id: str, user_id: str):
    """Background task to run the agent for a specific assignment"""
    try:
        logger.info(f"Starting agent for assignment {assignment_id}, user {user_id}")
        
        # Get path to agent directory (backend/agent)
        backend_dir = Path(__file__).parent.parent.parent.parent
        agent_dir = backend_dir / "agent"
        
        # Use system Python executable
        agent_python = str(sys.executable)
        logger.info(f"Using Python: {agent_python}")
        
        # Get path to main.py
        main_script = str(agent_dir / "main.py")
        logger.info(f"Agent directory: {agent_dir}, main script: {main_script}")
        
        # Run agent with specific assignment ID using subprocess in executor
        def run_agent():
            import subprocess
            logger.info(f"Executing: {agent_python} {main_script} --assignment-id {assignment_id} --user-id {user_id}")
            process = subprocess.Popen(
                [agent_python, main_script, 
                 "--assignment-id", assignment_id,
                 "--user-id", user_id],
                cwd=str(agent_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            return process.returncode, stdout, stderr
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        returncode, stdout, stderr = await loop.run_in_executor(None, run_agent)
        
        # Log output regardless of success/failure
        if stdout:
            logger.info(f"Agent stdout: {stdout}")
        if stderr:
            logger.info(f"Agent stderr: {stderr}")
        
        if returncode == 0:
            logger.info(f"Agent completed successfully for assignment {assignment_id}")
        else:
            logger.error(f"Agent failed for assignment {assignment_id} with return code {returncode}")
            logger.error(f"Agent stderr: {stderr}")
            # Update assignment status to failed
            assignment_repo = AssignmentRepository()
            await assignment_repo.update_assignment_status(assignment_id, "failed")
            
    except Exception as e:
        logger.error(f"Error running agent for assignment {assignment_id}: {e}", exc_info=True)
        # Update assignment status to failed
        try:
            assignment_repo = AssignmentRepository()
            await assignment_repo.update_assignment_status(assignment_id, "failed")
        except:
            pass