"""
UploadService.py
=================
Upload pipeline فقط — لا شيء آخر.

المسؤوليات بالترتيب:
  1. التحقق من نوع وحجم الملف
  2. التحقق من التكرار
  3. حفظ الملف عبر StorageService
  4. إنشاء UAVImage
  5. إرفاقه بـ Database
  6. تحديث وإرجاع JobStatus

لا يعتمد على:
  - FeatureExtractor  (شخص C)
  - AnalysisRun       (شخص D)
  - AHPModel          (شخص D)

يعتمد فقط على:
  - JobStatus.py  ← ملفك
  - UAVImage.py   ← ملفك
  - Database.py   ← ملفك
  - StorageService (شخص A)
"""

import json
import logging
import mimetypes
import os
from typing import Dict, Optional

from JobStatus import JobState, JobStatus
from UAVImage import UAVImage
from Database import Database

logger = logging.getLogger(__name__)


class UploadService:
    """
    Upload pipeline service.

    Contract (القسم 9 — خطة التكامل):
        Input  : file_data (bytes) + file_path (str) + metadata (dict, optional)
        Output : JobStatus — DONE أو ERROR
        بعد DONE: self.last_database يحتوي Database جاهز للـ pipeline
    """

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".raw"}
    ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/tiff", "image/x-raw"}
    MAX_FILE_SIZE      = 500 * 1024 * 1024   # 500 MB — SRS FR-2

    def __init__(self, storage_service=None):
        self.storage_service          = storage_service
        self._job: Optional[JobStatus] = None
        self.last_database: Optional[Database] = None
        logger.debug("UploadService initialized")

    def init(self, storage_service) -> None:
        """للتوافق مع الكود القديم."""
        self.storage_service = storage_service

    # ── Main Method ───────────────────────────────────────────────────────────

    def upload_file(
        self,
        file_data: bytes,
        file_path: str,
        metadata: Optional[Dict] = None,
    ) -> JobStatus:
        """
        يرفع ملف ويُنشئ Database جاهزاً للـ pipeline.

        Returns
        -------
        JobStatus
            DONE  → نجح، self.last_database جاهز
            ERROR → فشل، job.message يحتوي السبب
        """
        job = JobStatus()
        job.mark_running("Starting upload")
        self._job = job
        logger.info("Upload started: %s (%.1f KB)", file_path, len(file_data) / 1024)

        try:
            # 1) Guard: storage_service موجود؟ ──────────────────────────────
            job.update_progress(5, "Checking storage service")
            if self.storage_service is None:
                job.mark_error("StorageService not configured — call init() first")
                return job

            # 2) Validate ────────────────────────────────────────────────────
            job.update_progress(15, "Validating file")
            error = self.validate_file_type(file_path, file_data)
            if error:
                job.mark_error(error)
                return job

            # 3) Duplicate check ─────────────────────────────────────────────
            job.update_progress(25, "Checking for duplicates")
            if self._file_exists(file_path):
                job.mark_error(f"File already exists: {os.path.basename(file_path)}")
                logger.warning("Duplicate: %s", file_path)
                return job

            # 4) Save file ───────────────────────────────────────────────────
            job.update_progress(50, "Saving file")
            if not self.storage_service.save_file(file_data, file_path):
                job.mark_error("Storage error — file not saved")
                return job
            logger.info("File saved: %s", file_path)

            # 5) Save metadata ───────────────────────────────────────────────
            if metadata:
                job.update_progress(65, "Saving metadata")
                meta_bytes = json.dumps(metadata, ensure_ascii=False).encode()
                self.storage_service.save_file(meta_bytes, f"{file_path}.metadata.json")

            # 6) Create UAVImage ─────────────────────────────────────────────
            job.update_progress(80, "Creating image record")
            resolution = (metadata or {}).get("resolution", "unknown")
            image      = UAVImage(filePath=file_path, resolution=resolution)

            # 7) Attach to Database ──────────────────────────────────────────
            job.update_progress(90, "Building dataset")
            db = Database(name=os.path.basename(file_path))
            db.add_image(image)
            self.last_database = db
            logger.info("Database ready: '%s' — %d image(s)", db.name, db.image_count())

            # 8) Done ────────────────────────────────────────────────────────
            job.mark_done("Upload completed successfully")
            return job

        except Exception as exc:
            logger.exception("Upload error: %s", exc)
            job.mark_error(f"Unexpected error: {exc}")
            return job

    # ── Validation ───────────────────────────────────────────────────────────

    def validate_file_type(self, file_path: str, file_data: bytes) -> Optional[str]:
        """
        يتحقق من نوع وحجم الملف.
        Returns None إذا صحيح، وإلا رسالة الخطأ.
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if not ext:
            return "File has no extension"

        if ext not in self.ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(self.ALLOWED_EXTENSIONS))
            return f"Extension '{ext}' not allowed. Allowed: {allowed}"

        mime, _ = mimetypes.guess_type(file_path)
        if mime and mime not in self.ALLOWED_MIME_TYPES:
            return f"MIME type '{mime}' not allowed"

        if len(file_data) == 0:
            return "File is empty"

        if len(file_data) > self.MAX_FILE_SIZE:
            mb = len(file_data) / (1024 * 1024)
            return f"File {mb:.1f} MB exceeds 500 MB limit"

        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _file_exists(self, file_path: str) -> bool:
        """يتحقق إذا الملف موجود مسبقاً في التخزين."""
        try:
            self.storage_service.get(os.path.basename(file_path))
            return True
        except Exception:
            return False

    # ── Status ────────────────────────────────────────────────────────────────

    def get_job_status(self) -> Optional[JobStatus]:
        return self._job

    def reset(self) -> None:
        """يصفّر الحالة للاستخدام التالي."""
        self._job           = None
        self.last_database  = None
        logger.debug("UploadService reset")


# ── self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    class _MockStorage:
        _store: Dict = {}
        def save_file(self, data, path):
            self._store[path] = data
            return True
        def get(self, path):
            if path not in self._store:
                raise FileNotFoundError
            return self._store[path]

    svc = UploadService(storage_service=_MockStorage())

    # رفع ناجح
    job = svc.upload_file(b"\x89PNG\r\n" + b"\x00" * 100, "riyadh.png",
                          {"resolution": "4K"})
    print("Upload    :", job)
    print("Database  :", svc.last_database)
    print("Images    :", svc.last_database.image_count())

    # مكرر
    job2 = svc.upload_file(b"\x89PNG\r\n" + b"\x00" * 100, "riyadh.png")
    print("Duplicate :", job2)

    # امتداد خاطئ
    job3 = svc.upload_file(b"data", "file.exe")
    print("Bad ext   :", job3)

    # بدون storage
    job4 = UploadService().upload_file(b"\x89PNG\r\n", "img.png")
    print("No storage:", job4)
