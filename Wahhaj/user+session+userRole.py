"""
User Management System
Complete implementation of the User class with authentication and administration

Classes included:
- UserRole (enum)
- Session
- User


"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4
import hashlib
import secrets


# ============================================================================
# ENUMERATIONS
# ============================================================================

class UserRole(Enum):
    """User roles with different permission levels"""
    ADMIN = "Admin"
    ANALYST = "Analyst"


# ============================================================================
# SESSION CLASS
# ============================================================================

class Session:
    """User session information"""
    
    def __init__(self, session_id: UUID, user_id: UUID, created_at: datetime, expires_at: datetime):
        self.session_id: UUID = session_id
        self.user_id: UUID = user_id
        self.created_at: datetime = created_at
        self.expires_at: datetime = expires_at
        self.ip_address: Optional[str] = None
        self.user_agent: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if session is still valid"""
        return datetime.now() < self.expires_at
    
    def __str__(self):
        return f"Session({self.session_id}, expires: {self.expires_at})"


# ============================================================================
# USER CLASS
# ============================================================================

class User:
    """
    User account management class
    Handles authentication, authorization, and user administration
    """
    
    # Class-level storage (in production, use a database)
    _users_db: dict = {}  # user_id -> User
    _sessions_db: dict = {}  # session_id -> Session
    _credentials_db: dict = {}  # email -> hashed_password
    
    def __init__(self, name: str, email: str, role: UserRole, password: Optional[str] = None):
        """
        Initialize a new user
        
        Args:
            name: User's full name
            email: User's email address
            role: User role (Admin or Analyst)
            password: User's password (will be hashed)
        """
        self.user_id: UUID = uuid4()
        self.name: str = name
        self.email: str = email.lower()  # Normalize email
        self.role: UserRole = role
        self.session_id: Optional[UUID] = None
        self.created_at: datetime = datetime.now()
        self.expires_at: Optional[datetime] = None
        
        # Store user in class-level database
        User._users_db[self.user_id] = self
        
        # Set password if provided
        if password:
            self._set_password(password)
    
    # ========================================================================
    # PASSWORD MANAGEMENT (Private Methods)
    # ========================================================================
    
    @staticmethod
    def _hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
        """
        Hash password using SHA-256 with salt
        
        Args:
            password: Plain text password
            salt: Optional salt bytes (generated if not provided)
            
        Returns:
            Tuple of (hashed_password_hex, salt_bytes)
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # Hash password with salt
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # Number of iterations
        )
        
        return pwd_hash.hex(), salt
    
    def _set_password(self, password: str):
        """
        Set user password (hashes and stores)
        
        Args:
            password: Plain text password
        """
        pwd_hash, salt = self._hash_password(password)
        # Store as "hash$salt" for easy retrieval
        User._credentials_db[self.email] = f"{pwd_hash}${salt.hex()}"
    
    @staticmethod
    def _verify_password(email: str, password: str) -> bool:
        """
        Verify password for given email
        
        Args:
            email: User email
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        if email not in User._credentials_db:
            return False
        
        stored = User._credentials_db[email]
        stored_hash, salt_hex = stored.split('$')
        salt = bytes.fromhex(salt_hex)
        
        # Hash provided password with same salt
        pwd_hash, _ = User._hash_password(password, salt)
        
        # Compare hashes
        return pwd_hash == stored_hash
    
    # ========================================================================
    # AUTHENTICATION METHODS
    # ========================================================================
    
    def login(self, email: str, password: str) -> Session:
        """
        Authenticate user and create session
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Session object if authentication successful
            
        Raises:
            ValueError: If authentication fails
        """
        # Normalize email
        email = email.lower()
        
        # Verify credentials
        if not self._verify_password(email, password):
            raise ValueError("Invalid email or password")
        
        # Check if email matches this user
        if email != self.email:
            raise ValueError("Email does not match user account")
        
        # Create new session (24 hour duration)
        session = Session(
            session_id=uuid4(),
            user_id=self.user_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24)
        )
        
        # Store session
        self.session_id = session.session_id
        self.expires_at = session.expires_at
        User._sessions_db[session.session_id] = session
        
        return session
    
    def logout(self):
        """Logout user and invalidate session"""
        if self.session_id and self.session_id in User._sessions_db:
            del User._sessions_db[self.session_id]
        
        self.session_id = None
        self.expires_at = None
    
    def is_authenticated(self) -> bool:
        """Check if user has valid active session"""
        if not self.session_id:
            return False
        
        if self.session_id not in User._sessions_db:
            return False
        
        session = User._sessions_db[self.session_id]
        return session.is_valid()
    
    def refresh_session(self) -> Session:
        """
        Refresh current session (extend expiration)
        
        Returns:
            Updated session object
            
        Raises:
            ValueError: If no active session exists
        """
        if not self.session_id or self.session_id not in User._sessions_db:
            raise ValueError("No active session to refresh")
        
        session = User._sessions_db[self.session_id]
        session.expires_at = datetime.now() + timedelta(hours=24)
        self.expires_at = session.expires_at
        
        return session
    
    # ========================================================================
    # DATA UPLOAD METHODS
    # ========================================================================
    
    def upload_data(self, files: List[str]):
        """
        Upload UAV data files (creates async job)
        
        Args:
            files: List of file paths to upload
            
        Returns:
            JobStatus object for tracking upload progress
            
        Note:
            Requires JobStatus class to be imported from teammate's module:
            from jobstatus_module import JobStatus
        """
        if not self.is_authenticated():
            raise PermissionError("User must be authenticated to upload data")
        
        # Import JobStatus from teammate's module
        # from jobstatus_module import JobStatus
        
        # Create upload job using teammate's JobStatus class
        # job = JobStatus()
        # job.message = f"Queued {len(files)} files for upload"
        # job.state = "Queued"
        # return job
        
        # Placeholder return (remove when JobStatus is available)
        print(f"Upload initiated for {len(files)} files")
        return None
    
    # ========================================================================
    # USER MANAGEMENT METHODS (Admin Only)
    # ========================================================================
    
    def _require_admin(self):
        """Helper to check admin permissions"""
        if self.role != UserRole.ADMIN:
            raise PermissionError(f"Operation requires Admin role. Current role: {self.role.value}")
        
        if not self.is_authenticated():
            raise PermissionError("Admin must be authenticated to perform this operation")
    
    def add_user(self, user: 'User'):
        """
        Add a new user to the system (Admin only)
        
        Args:
            user: User object to add
            
        Raises:
            PermissionError: If current user is not an admin
            ValueError: If user with same email already exists
        """
        self._require_admin()
        
        # Check if email already exists (excluding the user being added)
        for uid, existing_user in User._users_db.items():
            if uid != user.user_id and existing_user.email == user.email:
                raise ValueError(f"User with email {user.email} already exists")
        
        # User is already added to _users_db in __init__
        # Just verify it's there
        if user.user_id not in User._users_db:
            User._users_db[user.user_id] = user
        
        print(f"✓ Admin {self.name} added user: {user.name} ({user.email})")
    
    def remove_user(self, user_id: UUID):
        """
        Remove a user from the system (Admin only)
        
        Args:
            user_id: UUID of user to remove
            
        Raises:
            PermissionError: If current user is not an admin
            ValueError: If user not found
        """
        self._require_admin()
        
        # Cannot remove self
        if user_id == self.user_id:
            raise ValueError("Cannot remove your own account")
        
        # Check if user exists
        if user_id not in User._users_db:
            raise ValueError(f"User with ID {user_id} not found")
        
        user = User._users_db[user_id]
        
        # Remove user's sessions
        sessions_to_remove = [
            sid for sid, session in User._sessions_db.items()
            if session.user_id == user_id
        ]
        for session_id in sessions_to_remove:
            del User._sessions_db[session_id]
        
        # Remove credentials
        if user.email in User._credentials_db:
            del User._credentials_db[user.email]
        
        # Remove user
        del User._users_db[user_id]
        
        print(f"✓ Admin {self.name} removed user: {user.name} ({user.email})")
    
    def reset_password(self, user_id: UUID, new_password: Optional[str] = None) -> str:
        """
        Reset user password (Admin only)
        
        Args:
            user_id: UUID of user whose password to reset
            new_password: New password (auto-generated if not provided)
            
        Returns:
            The new password (for admin to communicate to user)
            
        Raises:
            PermissionError: If current user is not an admin
            ValueError: If user not found
        """
        self._require_admin()
        
        # Check if user exists
        if user_id not in User._users_db:
            raise ValueError(f"User with ID {user_id} not found")
        
        user = User._users_db[user_id]
        
        # Generate random password if not provided
        if new_password is None:
            # Generate secure random password
            new_password = secrets.token_urlsafe(12)
        
        # Set new password
        user._set_password(new_password)
        
        # Invalidate all user's sessions (force re-login)
        sessions_to_remove = [
            sid for sid, session in User._sessions_db.items()
            if session.user_id == user_id
        ]
        for session_id in sessions_to_remove:
            del User._sessions_db[session_id]
        
        if user_id == user.user_id:
            user.session_id = None
            user.expires_at = None
        
        print(f"✓ Admin {self.name} reset password for user: {user.name} ({user.email})")
        
        return new_password
    
    # ========================================================================
    # USER QUERIES (Admin Only)
    # ========================================================================
    
    def list_all_users(self) -> List['User']:
        """
        List all users in system (Admin only)
        
        Returns:
            List of all User objects
            
        Raises:
            PermissionError: If current user is not an admin
        """
        self._require_admin()
        return list(User._users_db.values())
    
    def get_user_by_id(self, user_id: UUID) -> Optional['User']:
        """
        Get user by ID (Admin only)
        
        Args:
            user_id: User ID to lookup
            
        Returns:
            User object if found, None otherwise
        """
        self._require_admin()
        return User._users_db.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional['User']:
        """
        Get user by email (Admin only)
        
        Args:
            email: Email address to lookup
            
        Returns:
            User object if found, None otherwise
        """
        self._require_admin()
        email = email.lower()
        for user in User._users_db.values():
            if user.email == email:
                return user
        return None
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def change_password(self, old_password: str, new_password: str):
        """
        Allow user to change their own password
        
        Args:
            old_password: Current password
            new_password: New password
            
        Raises:
            ValueError: If old password is incorrect
        """
        if not self._verify_password(self.email, old_password):
            raise ValueError("Current password is incorrect")
        
        self._set_password(new_password)
        print(f"✓ Password changed for user: {self.name}")
    
    def __str__(self):
        """String representation of user"""
        auth_status = "✓ Authenticated" if self.is_authenticated() else "✗ Not authenticated"
        return (f"User(id={self.user_id}, name='{self.name}', "
                f"email='{self.email}', role={self.role.value}, {auth_status})")
    
    def __repr__(self):
        """Developer representation"""
        return (f"User(user_id={self.user_id}, name={self.name!r}, "
                f"email={self.email!r}, role={self.role})")
