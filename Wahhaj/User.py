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
    """يُرجع من login() — يحمل token وصلاحية الجلسة."""
    session_id: str   = field(default_factory=lambda: str(uuid.uuid4()))
    user_id:    str   = ""
    token:      str   = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15))

    @property
    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < self.expires_at


# ── ValidationReport (خفيف — للـ UploadService) ───────────────────────────────

@dataclass
class ValidationReport:
    is_valid: bool       = True
    errors:   List[str]  = field(default_factory=list)
    warnings: List[str]  = field(default_factory=list)


# ── User ──────────────────────────────────────────────────────────────────────

class User:
    """
    UML: User

    ملاحظة: addUser / removeUser / resetPassword تعمل على
    _user_registry (in-memory) في المرحلة الأولى.
    تُستبدل بـ DB calls لاحقاً دون تغيير الـ interface.
    """

    _user_registry: Dict[str, "User"] = {}   # shared in-memory store

    def __init__(
        self,
        name:       str,
        email:      str,
        role:       UserRole  = UserRole.ANALYST,
        user_id:    Optional[str] = None,
        session_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        hashed_password: str = "",
        is_active:  bool = True,
    ):
        # UML attributes
        self.userId:    str      = user_id    or str(uuid.uuid4())
        self.name:      str      = name
        self.role:      UserRole = role
        self.sessionId: str      = session_id or str(uuid.uuid4())
        self.createdAt: datetime = created_at or datetime.now(timezone.utc)
        self.expiresAt: datetime = expires_at or datetime.now(timezone.utc) + timedelta(minutes=15)

        # internal
        self._email:           str  = email
        self._hashed_password: str  = hashed_password
        self.is_active:        bool = is_active

    # ── UML methods ───────────────────────────────────────────

    def login(self, email: str, pw: str) -> Session:
        """
        يتحقق من البيانات ويُنشئ Session جديدة.
        في المرحلة الأولى: mock validation.
        """
        if email != self._email:
            raise ValueError("Invalid email")
        # TODO: bcrypt.checkpw(pw, self._hashed_password)
        session = Session(
            user_id    = self.userId,
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        self.sessionId  = session.session_id
        self.expiresAt  = session.expires_at
        return session

    def uploadDataFiles(self, files: list) -> "JobStatus":
        """
        يبدأ رفع قائمة ملفات.
        يرجع JobStatus — يُشغَّل الـ pipeline عبر UploadService.
        """
        from wahhaj.JobStatus import JobStatus, JobState
        job = JobStatus()
        if not self.is_active:
            job.mark_error("User is inactive")
            return job
        if self.role not in (UserRole.ADMIN, UserRole.ANALYST):
            job.mark_error("Insufficient permissions")
            return job
        # Delegate to UploadService (injected externally)
        job.mark_running(f"Queued {len(files)} file(s)")
        return job

    def addUser(self, u: "User") -> None:
        """Admin فقط — يضيف مستخدماً للـ registry."""
        if self.role != UserRole.ADMIN:
            raise PermissionError("Only Admin can add users")
        User._user_registry[u.userId] = u

    def removeUser(self, userId: str) -> None:
        """Admin فقط — يحذف مستخدماً من الـ registry."""
        if self.role != UserRole.ADMIN:
            raise PermissionError("Only Admin can remove users")
        User._user_registry.pop(userId, None)

    def resetPassword(self, userId: str) -> None:
        """
        Admin يعيد ضبط كلمة مرور مستخدم آخر.
        TODO: إرسال reset-link عبر البريد.
        """
        if self.role != UserRole.ADMIN:
            raise PermissionError("Only Admin can reset passwords")
        # placeholder: يُستبدل بـ email link لاحقاً
        if userId in User._user_registry:
            User._user_registry[userId]._hashed_password = ""

    # ── Factory ───────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:     str,
        email:    str,
        role:     UserRole = UserRole.ANALYST,
        password: str      = "",
    ) -> "User":
        return cls(name=name, email=email, role=role, hashed_password=password)

    # ── Serialization ─────────────────────────────────────────

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


# ── JobStatus forward ref (لتجنب circular import) ─────────────────────────────
class JobStatus:
    pass
