"""
wahhaj/User.py
==============
UML attributes:
    +userId     : UUID
    +name       : string
    +role       : enum(Admin, Analyst)
    +sessionId  : UUID
    +createdAt  : datetime
    +expiresAt  : datetime

UML methods:
    +login(email, pw)              : Session
    +uploadDataFiles(files)        : JobStatus
    +addUser(u: User)              : void
    +removeUser(userId: UUID)      : void
    +resetPassword(userId: UUID)   : void
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN   = "Admin"
    ANALYST = "Analyst"


# ── Session ───────────────────────────────────────────────────────────────────

@dataclass
class Session:
    """Returned from login() — carries token and session validity."""
    session_id: str      = field(default_factory=lambda: str(uuid.uuid4()))
    user_id:    str      = ""
    token:      str      = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15)
    )

    @property
    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < self.expires_at


# ── ValidationReport ──────────────────────────────────────────────────────────

@dataclass
class ValidationReport:
    is_valid: bool      = True
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ── User ──────────────────────────────────────────────────────────────────────

class User:
    """
    UML: User

    addUser / removeUser / resetPassword operate on _user_registry
    (in-memory store) in Phase 1.  Replace with DB calls later without
    changing the interface.
    """

    _user_registry: Dict[str, "User"] = {}   # shared in-memory store

    def __init__(
        self,
        name:            str,
        email:           str,
        role:            UserRole         = UserRole.ANALYST,
        user_id:         Optional[str]    = None,
        session_id:      Optional[str]    = None,
        created_at:      Optional[datetime] = None,
        expires_at:      Optional[datetime] = None,
        hashed_password: str              = "",
        is_active:       bool             = True,
    ):
        # UML attributes
        self.userId:    str      = user_id    or str(uuid.uuid4())
        self.name:      str      = name
        self.role:      UserRole = role
        self.sessionId: str      = session_id or str(uuid.uuid4())
        self.createdAt: datetime = created_at or datetime.now(timezone.utc)
        self.expiresAt: datetime = (
            expires_at or datetime.now(timezone.utc) + timedelta(minutes=15)
        )

        # internal
        self._email:           str  = email.strip().lower()
        self._hashed_password: str  = hashed_password
        self.is_active:        bool = is_active

    # ── UML methods ───────────────────────────────────────────────────────────

    def login(self, email: str, pw: str) -> Session:
        if email.strip().lower() != self._email:
            raise ValueError("Invalid email")

        if pw != self._hashed_password:
            raise ValueError("Invalid password")

        if not self.is_active:
            raise ValueError("Account is inactive")

        session = Session(
            user_id=self.userId,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        self.sessionId = session.session_id
        self.expiresAt = session.expires_at
        return session

    def uploadDataFiles(self, files: list) -> "JobStatus":
        """Queue a list of files for upload via UploadService."""
        from Wahhaj.JobStatus import JobStatus, JobState
        job = JobStatus()
        if not self.is_active:
            job.mark_error("User is inactive")
            return job
        if self.role not in (UserRole.ADMIN, UserRole.ANALYST):
            job.mark_error("Insufficient permissions")
            return job
        job.mark_running(f"Queued {len(files)} file(s)")
        return job

    def addUser(self, u: "User") -> None:
        """Admin only — add a user to the registry."""
        if self.role != UserRole.ADMIN:
            raise PermissionError("Only Admin can add users")
        User._user_registry[u.userId] = u

    def removeUser(self, userId: str) -> None:
        """Admin only — remove a user from the registry."""
        if self.role != UserRole.ADMIN:
            raise PermissionError("Only Admin can remove users")
        User._user_registry.pop(userId, None)

    def resetPassword(self, userId: str) -> None:
        """Admin only — reset another user's password to empty."""
        if self.role != UserRole.ADMIN:
            raise PermissionError("Only Admin can reset passwords")
        if userId in User._user_registry:
            User._user_registry[userId]._hashed_password = ""

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:     str,
        email:    str,
        role:     UserRole = UserRole.ANALYST,
        password: str      = "",
    ) -> "User":
        return cls(name=name, email=email, role=role, hashed_password=password)

    # ── Registry lookup ───────────────────────────────────────────────────────

    @classmethod
    def find_by_email(cls, email: str) -> Optional["User"]:
        """
        Search _user_registry for a user with the given email.
        Returns None if not found.

        Called by ui_helpers.login_user() before invoking .login().
        """
        normalized = email.strip().lower()
        for user in cls._user_registry.values():
            if user._email == normalized:
                return user
        return None

    # ── Dev seed ──────────────────────────────────────────────────────────────

    @classmethod
    def seed_default_users(cls) -> None:
        """
        Populate _user_registry with dev accounts if it is empty.
        Called automatically by ui_helpers.login_user().

        Dev credentials
        ---------------
        admin@wahhaj.sa    / admin123     (Admin role)
        analyst@wahhaj.sa  / analyst123   (Analyst role)

        Replace this method body with a DB read when moving to production.
        """
        if cls._user_registry:
            return  # already seeded, skip

        admin = cls(
            name            = "Admin",
            email           = "admin@wahhaj.sa",
            role            = UserRole.ADMIN,
            hashed_password = "admin123",
        )
        analyst = cls(
            name            = "Analyst",
            email           = "analyst@wahhaj.sa",
            role            = UserRole.ANALYST,
            hashed_password = "analyst123",
        )
        cls._user_registry[admin.userId]   = admin
        cls._user_registry[analyst.userId] = analyst

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "userId":    self.userId,
            "name":      self.name,
            "email":     self._email,
            "role":      self.role.value,
            "sessionId": self.sessionId,
            "createdAt": self.createdAt.isoformat(),
            "expiresAt": self.expiresAt.isoformat(),
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"User(id={self.userId[:8]}, name={self.name!r}, role={self.role.value})"


# ── JobStatus forward ref (prevents circular import) ──────────────────────────
class JobStatus:
    pass