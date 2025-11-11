"""
Authentication routes for public plotter server.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from .auth import (
    get_db, create_access_token, get_current_user, get_admin_user,
    User, create_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response Models

class UserRegister(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User information response."""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    api_key: str
    jobs_per_hour: int
    jobs_per_day: int
    total_jobs: int
    total_plot_time: float
    created_at: str
    last_login: str = None


class UserUpdate(BaseModel):
    """Update user settings."""
    email: EmailStr = None
    jobs_per_hour: int = None
    jobs_per_day: int = None


class PasswordChange(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class AdminUserUpdate(BaseModel):
    """Admin user update."""
    is_active: bool = None
    is_admin: bool = None
    jobs_per_hour: int = None
    jobs_per_day: int = None
    max_job_duration: int = None


# Routes

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register new user account.
    
    Creates a new user with API key for plotter access.
    Default rate limits: 10 jobs/hour, 50 jobs/day.
    """
    try:
        user = create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            is_admin=False,
            db=db
        )
        
        logger.info(f"New user registered: {user.username}")
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            api_key=user.api_key,
            jobs_per_hour=user.jobs_per_hour,
            jobs_per_day=user.jobs_per_day,
            total_jobs=user.total_jobs,
            total_plot_time=user.total_plot_time,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login and receive JWT access token.
    
    Use the token in Authorization header: Bearer <token>
    Token expires in 7 days by default.
    """
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not user.verify_password(credentials.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(f"User logged in: {user.username}")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        api_key=current_user.api_key,
        jobs_per_hour=current_user.jobs_per_hour,
        jobs_per_day=current_user.jobs_per_day,
        total_jobs=current_user.total_jobs,
        total_plot_time=current_user.total_plot_time,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Current password is incorrect"
        )
    
    current_user.set_password(password_data.new_password)
    db.commit()
    
    logger.info(f"Password changed for user: {current_user.username}")
    
    return {"message": "Password changed successfully"}


@router.post("/regenerate-api-key")
async def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate API key.
    
    ⚠️ Old API key will be invalidated immediately.
    """
    new_key = current_user.generate_api_key()
    db.commit()
    
    logger.info(f"API key regenerated for user: {current_user.username}")
    
    return {
        "message": "API key regenerated successfully",
        "api_key": new_key
    }


@router.patch("/me", response_model=UserResponse)
async def update_user_settings(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings."""
    if updates.email:
        # Check if email already exists
        existing = db.query(User).filter(
            User.email == updates.email,
            User.id != current_user.id
        ).first()
        
        if existing:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Email already in use"
            )
        
        current_user.email = updates.email
    
    if updates.jobs_per_hour is not None:
        current_user.jobs_per_hour = updates.jobs_per_hour
    
    if updates.jobs_per_day is not None:
        current_user.jobs_per_day = updates.jobs_per_day
    
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"User settings updated: {current_user.username}")
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        api_key=current_user.api_key,
        jobs_per_hour=current_user.jobs_per_hour,
        jobs_per_day=current_user.jobs_per_day,
        total_jobs=current_user.total_jobs,
        total_plot_time=current_user.total_plot_time,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )


# Admin Routes

@router.get("/users", dependencies=[Depends(get_admin_user)])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "total_jobs": user.total_jobs,
            "total_plot_time": user.total_plot_time,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        for user in users
    ]


@router.patch("/users/{user_id}", dependencies=[Depends(get_admin_user)])
async def update_user_admin(
    user_id: int,
    updates: AdminUserUpdate,
    db: Session = Depends(get_db)
):
    """Update user settings (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    
    if updates.is_active is not None:
        user.is_active = updates.is_active
    
    if updates.is_admin is not None:
        user.is_admin = updates.is_admin
    
    if updates.jobs_per_hour is not None:
        user.jobs_per_hour = updates.jobs_per_hour
    
    if updates.jobs_per_day is not None:
        user.jobs_per_day = updates.jobs_per_day
    
    if updates.max_job_duration is not None:
        user.max_job_duration = updates.max_job_duration
    
    db.commit()
    
    logger.info(f"Admin updated user: {user.username}")
    
    return {"message": f"User {user.username} updated successfully"}


@router.delete("/users/{user_id}", dependencies=[Depends(get_admin_user)])
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    
    if user.is_admin:
        # Check if this is the last admin
        admin_count = db.query(User).filter(User.is_admin.is_(True)).count()
        if admin_count <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Cannot delete the last admin user"
            )
    
    username = user.username
    db.delete(user)
    db.commit()
    
    logger.info(f"Admin deleted user: {username}")
    
    return {"message": f"User {username} deleted successfully"}
