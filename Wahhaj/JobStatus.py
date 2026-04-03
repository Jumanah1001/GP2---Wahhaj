"""
JobStatus.py
=============
Single Source of Truth لحالة أي عملية في النظام.


"""

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class JobState(Enum):
    QUEUED  = "queued"
    RUNNING = "running"
    DONE    = "done"
    ERROR   = "error"


class JobStatus:
    """
    يتتبع حالة أي عملية (رفع، تحليل، تصدير).

    Attributes
    ----------
    jobId      : UUID string
    progress   : 0–100
    message    : رسالة وصفية
    state      : JobState
    created_at : وقت الإنشاء (UTC)
    updated_at : آخر تعديل (UTC)
    """

    def __init__(self):
        self.jobId      = str(uuid.uuid4())
        self.progress   = 0
        self.message    = ""
        self.state      = JobState.QUEUED
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        logger.debug("JobStatus created: %s", self.jobId[:8])

    # ── Transitions ──────────────────────────────────────────────────────────

    def mark_running(self, message: str = "Running...") -> None:
        self.state      = JobState.RUNNING
        self.message    = message
        self.updated_at = datetime.now(timezone.utc)
        logger.info("Job %s → RUNNING: %s", self.jobId[:8], message)

    def mark_done(self, message: str = "Completed") -> None:
        self.state      = JobState.DONE
        self.progress   = 100
        self.message    = message
        self.updated_at = datetime.now(timezone.utc)
        logger.info("Job %s → DONE", self.jobId[:8])

    def mark_error(self, message: str = "An error occurred") -> None:
        self.state      = JobState.ERROR
        self.message    = message
        self.updated_at = datetime.now(timezone.utc)
        logger.error("Job %s → ERROR: %s", self.jobId[:8], message)

    def update_progress(self, progress: int, message: str = "") -> None:
        self.progress   = max(0, min(100, progress))
        self.updated_at = datetime.now(timezone.utc)
        if message:
            self.message = message

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jobId":      self.jobId,
            "progress":   self.progress,
            "message":    self.message,
            "state":      self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobStatus":
        job             = cls.__new__(cls)
        job.jobId       = data["jobId"]
        job.progress    = data.get("progress", 0)
        job.message     = data.get("message", "")
        job.state       = JobState(data["state"])
        job.created_at  = datetime.fromisoformat(data["created_at"]) \
                          if "created_at" in data else datetime.now(timezone.utc)
        job.updated_at  = datetime.fromisoformat(data["updated_at"]) \
                          if "updated_at" in data else datetime.now(timezone.utc)
        return job

    def __repr__(self):
        return (f"JobStatus(id={self.jobId[:8]}, "
                f"state={self.state.value}, progress={self.progress}%)")


# ── self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    job = JobStatus()
    print("Initial :", job)
    job.mark_running("Uploading...")
    job.update_progress(50)
    print("Running :", job)
    job.mark_done()
    print("Done    :", job)
    restored = JobStatus.from_dict(job.to_dict())
    assert restored.jobId == job.jobId
    assert restored.state == job.state
    print("✅ to_dict / from_dict OK")
