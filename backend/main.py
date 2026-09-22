"""FastAPI application for Ayni data collection system."""
import os
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

from database import get_pool, close_pool
from auth import decode_token, create_access_token, authenticate_user, create_user, get_user
from schema import (
    UserCreate, FormSubmissionCreate, FormSubmissionUpdate, 
    EtnographicScene, ObservationDay, SceneRecord, AnalyticMemo
)
from forms_service import (
    create_form_submission, get_form_submission, get_user_submissions,
    get_team_submissions, delete_form_submission, sync_form, get_statistics,
    update_form_submission
)

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup on startup/shutdown."""
    # Startup
    await get_pool()
    print("✓ Database pool initialized")
    yield
    # Shutdown
    await close_pool()
    print("✓ Database pool closed")


app = FastAPI(
    title="Ayni Collection System API",
    description="Backend API for qualitative data collection forms",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware. Keep origins explicit when credentials are enabled.
allowed_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract and validate the current user from JWT token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = await get_user(payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return payload


# ============================================================================
# Authentication Routes
# ============================================================================

@app.post("/api/auth/register")
async def register(user: UserCreate):
    """Register a new user."""
    try:
        new_user = await create_user(
            email=user.email,
            name=user.name,
            password=user.password,
            role="collector"
        )
        
        token = create_access_token(new_user["id"], new_user["role"])
        
        return {
            "user": {
                "id": new_user["id"],
                "email": new_user["email"],
                "name": new_user["name"],
                "role": new_user["role"]
            },
            "token": token
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/api/auth/login")
async def login(email: str, password: str):
    """Login user and return access token."""
    user = await authenticate_user(email, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    token = create_access_token(user["id"], user["role"])
    
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        },
        "token": token
    }


# ============================================================================
# Form Submission Routes
# ============================================================================

@app.post("/api/forms")
async def create_submission(
    submission: FormSubmissionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new form submission."""
    result = await create_form_submission(
        user_id=current_user["user_id"],
        form_type=submission.form_type,
        data=submission.data,
        status=submission.status,
        client_id=submission.client_id,
    )
    return result


@app.get("/api/forms/{submission_id}")
async def read_submission(
    submission_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a form submission."""
    submission = await get_form_submission(submission_id)
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form submission not found"
        )
    
    # Drafts and submitted records are private unless the team endpoint grants access.
    if submission["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this form"
        )

    return submission


@app.put("/api/forms/{submission_id}")
async def update_submission(
    submission_id: str,
    update: FormSubmissionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a form submission."""
    result = await update_form_submission(
        submission_id=submission_id,
        user_id=current_user["user_id"],
        data=update.data,
        status=update.status
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form submission not found or access denied"
        )
    
    return result


@app.delete("/api/forms/{submission_id}")
async def delete_submission(
    submission_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a form submission."""
    success = await delete_form_submission(submission_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form submission not found or cannot be deleted"
        )
    
    return {"message": "Form submission deleted successfully"}


@app.post("/api/forms/{submission_id}/submit")
async def submit_form(
    submission_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Submit a form (change status from draft to submitted)."""
    result = await update_form_submission(
        submission_id=submission_id,
        user_id=current_user["user_id"],
        status="submitted"
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form submission not found"
        )
    
    return result


@app.post("/api/forms/{submission_id}/sync")
async def sync_form_submission(
    submission_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Sync a form (mark as synced)."""
    result = await sync_form(submission_id, current_user["user_id"])
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form submission not found"
        )
    
    return result


@app.get("/api/forms")
async def list_user_submissions(
    form_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all submissions for the current user."""
    submissions = await get_user_submissions(
        user_id=current_user["user_id"],
        form_type=form_type
    )
    return {
        "submissions": submissions,
        "total": len(submissions)
    }


@app.get("/api/team/forms")
async def list_team_submissions(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get all submitted forms from team (read-only access)."""
    result = await get_team_submissions(
        requester_id=current_user["user_id"],
        limit=limit,
        offset=offset
    )
    return result


# ============================================================================
# Statistics Routes
# ============================================================================

@app.get("/api/statistics")
async def statistics(current_user: dict = Depends(get_current_user)):
    """Get form submission statistics."""
    stats = await get_statistics(current_user["user_id"])
    return stats


# ============================================================================
# Health Check
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============================================================================
# Root
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Ayni Collection System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
