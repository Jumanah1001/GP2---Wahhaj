"""
WAHHAJ — User Module
=====================
Exact implementation of the User class from the UML diagram.

Attributes  : userId, name, role, sessionId, createdAt, expiresAt
Methods     : login(), uploadDataFiles(), addUser(), removeUser(), resetPassword()
Relationship: User 1 --owns-- 0..* Database

Run:
    pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose passlib pydantic-settings email-validator
    uvicorn user:app --reload --port 8000
"""

import uuid
import enum
from datetime import datetime, timedelta
from typing import Optional, Generator, List

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy import create_engine, Column, String, DateTime, Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session, relationship
from sqlalchemy.exc import IntegrityError

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from jose import JWTError, jwt
from passlib.context import CryptContext


# ============================================================
# CONFIG
# ============================================================
class Settings(BaseSettings):
    DATABASE_URL:                str  = "postgresql://wahhaj_user:wahhaj_pass@localhost:5432/wahhaj_db"
    JWT_SECRET:                  str  = "CHANGE_THIS_IN_PRODUCTION"
    JWT_ALGORITHM:               str  = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int  = 15  # SRS 3.1.3.4 — session expires after 15 min
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()


# ============================================================
# DATABASE
# ============================================================
class Base(DeclarativeBase):
    pass

engine       = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# MODEL  (UML → Database table)
# ============================================================
class UserRole(str, enum.Enum):
    ADMIN   = "Admin"    # UML: enum{Admin, Analyst}
    ANALYST = "Analyst"


class User(Base):
    __tablename__ = "users"

    # UML attributes
    userId    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name      = Column(String(100), nullable=False)
    email     = Column(String(255), unique=True, nullable=False, index=True)  # needed for login()
    password  = Column(String(255), nullable=False)                            # hashed, needed for login()
    role      = Column(SAEnum(UserRole), nullable=False, default=UserRole.ANALYST)
    sessionId = Column(UUID(as_uuid=True), nullable=True, default=None)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiresAt = Column(DateTime, nullable=True,  default=None)
    isActive  = Column(Boolean,  nullable=False, default=True)

    # UML: User 1 ---owns--- 0..* Database
    databases = relationship("Database", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.userId} name={self.name} role={self.role}>"


# ============================================================
# SCHEMAS  (what goes in/out of the API)
# ============================================================
class UserCreate(BaseModel):
    """Used by addUser()"""
    name:     str       = Field(..., min_length=2, max_length=100)
    email:    EmailStr
    password: str       = Field(..., min_length=8)
    role:     UserRole  = UserRole.ANALYST

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if not any(c.isupper() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password needs at least one uppercase letter and one digit")
        return v

class UserLogin(BaseModel):
    """Used by login()"""
    email:    EmailStr
    password: str

class UserUpdate(BaseModel):
    """Used by resetPassword() and general edits"""
    name:     Optional[str]      = None
    role:     Optional[UserRole] = None
    isActive: Optional[bool]     = None
    password: Optional[str]      = Field(None, min_length=8)  # resetPassword()

class UserResponse(BaseModel):
    """Returned to frontend — password never included"""
    userId:    uuid.UUID
    name:      str
    email:     EmailStr
    role:      UserRole
    isActive:  bool
    createdAt: datetime
    expiresAt: Optional[datetime] = None
    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    """Returned after login()"""
    access_token: str
    token_type:   str          = "bearer"
    expires_in:   int
    user:         UserResponse


# ============================================================
# SERVICES  (business logic for each UML method)
# ============================================================
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return _pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)

def create_jwt(user_id: uuid.UUID, role: str) -> str:
    expire  = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_jwt(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

# --- UML: login(email, pw): Session ---
def login(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password) or not user.isActive:
        return None
    return user

# --- UML: addUser(u: User) ---
def add_user(db: Session, data: UserCreate) -> User:
    if db.query(User).filter(User.email == data.email).first():
        raise ValueError(f"Email '{data.email}' already exists.")
    user = User(name=data.name, email=data.email,
                password=hash_password(data.password), role=data.role)
    try:
        db.add(user); db.commit(); db.refresh(user)
    except IntegrityError:
        db.rollback(); raise ValueError("Database conflict.")
    return user

# --- UML: removeUser(userId: UUID) ---
def remove_user(db: Session, user_id: uuid.UUID) -> bool:
    user = db.query(User).filter(User.userId == user_id).first()
    if not user:
        return False
    db.delete(user); db.commit()
    return True

# --- UML: resetPassword(userId: UUID) ---
def reset_password(db: Session, user_id: uuid.UUID, new_password: str) -> bool:
    user = db.query(User).filter(User.userId == user_id).first()
    if not user:
        return False
    user.password = hash_password(new_password)
    db.commit()
    return True

# --- UML: uploadDataFiles(): JobStatus — returns 202 Accepted, actual upload handled by UploadService ---
def upload_data_files(user: User) -> dict:
    return {"jobId": str(uuid.uuid4()), "userId": str(user.userId), "state": "Queued"}

# Helper: partial update (name, role, isActive)
def update_user(db: Session, user_id: uuid.UUID, data: UserUpdate) -> Optional[User]:
    user = db.query(User).filter(User.userId == user_id).first()
    if not user:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, hash_password(value) if field == "password" else value)
    db.commit(); db.refresh(user)
    return user


# ============================================================
# ROUTERS
# ============================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Dependency: validates JWT and returns the logged-in User."""
    err = HTTPException(status_code=401, detail="Invalid or expired token.",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_jwt(token)
        user_id = payload.get("sub")
        if not user_id: raise err
    except JWTError:
        raise err
    user = db.query(User).filter(User.userId == uuid.UUID(user_id)).first()
    if not user or not user.isActive: raise err
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: ensures the caller is an Admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


# /auth — login()
auth_router = APIRouter(prefix="/auth", tags=["Auth"])

@auth_router.post("/login", response_model=TokenResponse)
def route_login(credentials: UserLogin, db: Session = Depends(get_db)):
    """UML: login(email, pw): Session"""
    user = login(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return TokenResponse(
        access_token=create_jwt(user.userId, user.role.value),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


# /users — addUser(), removeUser(), resetPassword(), uploadDataFiles()
users_router = APIRouter(prefix="/users", tags=["Users"])

@users_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@users_router.get("/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100,
               db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).offset(skip).limit(limit).all()

@users_router.post("/", response_model=UserResponse, status_code=201)
def route_add_user(data: UserCreate, db: Session = Depends(get_db),
                   _: User = Depends(require_admin)):
    """UML: addUser(u: User)"""
    try:
        return add_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@users_router.delete("/{user_id}", status_code=204)
def route_remove_user(user_id: uuid.UUID, db: Session = Depends(get_db),
                      _: User = Depends(require_admin)):
    """UML: removeUser(userId: UUID)"""
    if not remove_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found.")

@users_router.patch("/{user_id}/reset-password", status_code=200)
def route_reset_password(user_id: uuid.UUID, new_password: str,
                         db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """UML: resetPassword(userId: UUID)"""
    if not reset_password(db, user_id, new_password):
        raise HTTPException(status_code=404, detail="User not found.")
    return {"detail": "Password reset successfully."}

@users_router.patch("/{user_id}", response_model=UserResponse)
def route_update_user(user_id: uuid.UUID, data: UserUpdate,
                      db: Session = Depends(get_db), _: User = Depends(require_admin)):
    updated = update_user(db, user_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    return updated

@users_router.post("/upload", status_code=202)
def route_upload_data_files(current_user: User = Depends(get_current_user)):
    """UML: uploadDataFiles(): JobStatus"""
    return upload_data_files(current_user)


# ============================================================
# APP
# ============================================================
app = FastAPI(title="WAHHAJ API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_router)
app.include_router(users_router)

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
