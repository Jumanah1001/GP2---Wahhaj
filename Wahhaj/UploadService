from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum
import mimetypes
import os
import json
import uuid


class JobState(Enum):
    """Enum for job states (matches diagram state)"""
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class JobStatus:
    """Matches the diagram: jobId + progress + message + state"""
    job_id: str
    progress: int = 0
    message: str = ""
    state: JobState = JobState.QUEUED


class UploadService:
    """
    Service for handling file uploads with validation.
    Uses StorageService and returns JobStatus (as in class diagram).
    """

    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.raw'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/tiff',
        'image/x-raw'
    }
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

    def init(self, storage_service):
        self.storage_service = storage_service
        self._job: Optional[JobStatus] = None

    def validate_file_type(self, file_path: str, file_data: bytes) -> Optional[str]:
        """
        Returns:
            None if valid, otherwise returns an error message string.
        """
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()

        if extension not in self.ALLOWED_EXTENSIONS:
            return f"Invalid file extension: {extension}"

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type not in self.ALLOWED_MIME_TYPES:
            return f"Invalid MIME type: {mime_type}"

        if len(file_data) > self.MAX_FILE_SIZE:
            return "File size exceeds maximum allowed size"

        if len(file_data) == 0:
            return "File is empty"

        return None

    def upload_file(
        self,
        file_data: bytes,
        file_path: str,
        metadata: Optional[Dict] = None
    ) -> JobStatus:
        """
        Upload file with validation and simple progress tracking.
        Returns a JobStatus object (diagram-aligned).
        """
        job = JobStatus(job_id=str(uuid.uuid4()), state=JobState.RUNNING, progress=5, message="Starting upload")
        self._job = job

        try:
            # 1) Validate
            job.progress = 15
            job.message = "Validating file"
            err = self.validate_file_type(file_path, file_data)
            if err:
                job.state = JobState.ERROR
                job.message = err
                return job

            # 2) Save file
            job.progress = 60
            job.message = "Saving file"
            success = self.storage_service.save_file(file_data, file_path)
            if not success:
                job.state = JobState.ERROR
                job.message = "File upload failed (storage error)"
                return job

            # 3) Save metadata (optional)
            if metadata:
                job.progress = 80
                job.message = "Saving metadata"
                metadata_path = f"{file_path}.metadata.json"
                metadata_json = json.dumps(metadata, ensure_ascii=False).encode('utf-8')
                # إذا فشل حفظ الميتاداتا ما نطيح الرفع كله (اختياري)
                self.storage_service.save_file(metadata_json, metadata_path)

            # 4) Done
            job.progress = 100
            job.state = JobState.DONE
            job.message = "Upload completed"
            return job

        except Exception as e:
            job.state = JobState.ERROR
            job.message = f"Error during upload: {e}"
            return job

    def get_job_status(self) -> Optional[JobStatus]:
        """Get the latest job status (simple version)."""
        return self._job

    def reset_job_status(self) -> None:
        """Reset stored job info."""
        self._job = None 
