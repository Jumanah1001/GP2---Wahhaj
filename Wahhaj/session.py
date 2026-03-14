"""


Class: Session



"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4
import hashlib
import secrets


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


