"""
Authentication and authorization for public plotter server.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import yaml

# Load configuration with error handling
try:
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    # Use default values if config file not found
    config = {
        'auth': {
            'database_url': 'sqlite:///users.db',
            'secret_key': 'development-secret-key-change-in-production',
            'token_expire_minutes': 10080
        }
    }
except yaml.YAMLError as e:
    raise RuntimeError(f"Error parsing configuration file: {e}")

# Database setup
Base = declarative_base()
engine = create_engine(config.get('auth', {}).get('database_url', 'sqlite:///users.db'))
SessionLocal = sessionmaker(bind=engine)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = config.get('auth', {}).get('secret_key', secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = config.get('auth', {}).get('token_expire_minutes', 10080)  # 7 days

# Security
security = HTTPBearer()


class User(Base):
    """User model."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True)
    
    # Permissions
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Rate limiting
    jobs_per_hour = Column(Integer, default=10)
    jobs_per_day = Column(Integer, default=50)
    max_job_duration = Column(Integer, default=3600)  # seconds
    
    # Usage tracking
    total_jobs = Column(Integer, default=0)
    total_plot_time = Column(Float, default=0.0)  # seconds
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(password, self.hashed_password)
    
    def set_password(self, password: str):
        """Hash and set password."""
        self.hashed_password = pwd_context.hash(password)
    
    def generate_api_key(self) -> str:
        """Generate new API key."""
        self.api_key = secrets.token_urlsafe(32)
        return self.api_key


class RateLimit(Base):
    """Rate limiting tracker."""
    __tablename__ = 'rate_limits'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    endpoint = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


# Create tables
Base.metadata.create_all(engine)


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.JWTError:
        raise HTTPException(401, "Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token or API key.
    
    Supports two auth methods:
    1. JWT Bearer token: Authorization: Bearer <token>
    2. API key: Authorization: Bearer <api_key>
    """
    token = credentials.credentials
    
    # Try JWT first
    try:
        payload = verify_token(token)
        username = payload.get("sub")
        
        if username is None:
            raise HTTPException(401, "Invalid authentication credentials")
        
        user = db.query(User).filter(User.username == username).first()
        
    except HTTPException:
        # Try API key
        user = db.query(User).filter(User.api_key == token).first()
    
    if user is None:
        raise HTTPException(401, "Invalid authentication credentials")
    
    if not user.is_active:
        raise HTTPException(403, "User account is disabled")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin permissions."""
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
    return current_user


def check_rate_limit(user: User, endpoint: str, db: Session) -> bool:
    """
    Check if user has exceeded rate limit.
    
    Returns True if within limit, raises HTTPException if exceeded.
    """
    now = datetime.utcnow()
    
    # Check hourly limit
    hour_ago = now - timedelta(hours=1)
    hourly_requests = db.query(RateLimit).filter(
        RateLimit.user_id == user.id,
        RateLimit.endpoint == endpoint,
        RateLimit.timestamp >= hour_ago
    ).count()
    
    if hourly_requests >= user.jobs_per_hour:
        raise HTTPException(
            429,
            f"Rate limit exceeded: {user.jobs_per_hour} jobs per hour"
        )
    
    # Check daily limit
    day_ago = now - timedelta(days=1)
    daily_requests = db.query(RateLimit).filter(
        RateLimit.user_id == user.id,
        RateLimit.endpoint == endpoint,
        RateLimit.timestamp >= day_ago
    ).count()
    
    if daily_requests >= user.jobs_per_day:
        raise HTTPException(
            429,
            f"Rate limit exceeded: {user.jobs_per_day} jobs per day"
        )
    
    # Record request
    rate_limit = RateLimit(
        user_id=user.id,
        endpoint=endpoint,
        timestamp=now
    )
    db.add(rate_limit)
    db.commit()
    
    return True


def create_user(
    username: str,
    email: str,
    password: str,
    is_admin: bool = False,
    db: Session = None
) -> User:
    """Create new user."""
    if db is None:
        db = SessionLocal()
    
    # Check if user exists
    if db.query(User).filter(User.username == username).first():
        raise ValueError(f"Username '{username}' already exists")
    
    if db.query(User).filter(User.email == email).first():
        raise ValueError(f"Email '{email}' already registered")
    
    # Create user
    user = User(
        username=username,
        email=email,
        is_admin=is_admin
    )
    user.set_password(password)
    user.generate_api_key()
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def init_admin_user():
    """Initialize default admin user if none exists."""
    db = SessionLocal()
    
    # Check if any admin exists
    admin = db.query(User).filter(User.is_admin.is_(True)).first()
    
    if not admin:
        print("Creating default admin user...")
        admin = create_user(
            username="admin",
            email="admin@example.com",
            password=secrets.token_urlsafe(16),  # Random password
            is_admin=True,
            db=db
        )
        
        print(f"""
╔══════════════════════════════════════════════════════════╗
║  DEFAULT ADMIN ACCOUNT CREATED                           ║
╠══════════════════════════════════════════════════════════╣
║  Username: admin                                         ║
║  Email:    admin@example.com                             ║
║  API Key:  {admin.api_key[:40]}...  ║
╠══════════════════════════════════════════════════════════╣
║  ⚠️  IMPORTANT: Change password immediately!              ║
║  Use: POST /api/auth/change-password                     ║
╚══════════════════════════════════════════════════════════╝
""")
    
    db.close()


# Initialize on import
init_admin_user()
