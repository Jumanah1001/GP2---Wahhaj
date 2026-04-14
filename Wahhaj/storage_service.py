"""
wahhaj/storage_service.py
=========================
UML methods:
    +get(path) : FileRef
    +put(file)  : FileRef

save_file() محتفظ به لأن UploadService يستخدمه داخلياً.
get() يرفع FileNotFoundError — UploadService._file_exists يعتمد على ذلك.
"""

import os
import shutil
from .models import FileRef


class StorageService:

    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    # ── UML methods ───────────────────────────────────────────

    def get(self, path: str) -> FileRef:
        """
        يسترجع FileRef للملف المطلوب.
        يرفع FileNotFoundError إذا الملف غير موجود.
        ⚠️ UploadService._file_exists يعتمد على هذا الـ raise.
        """
        full = os.path.join(self.base_dir, path)
        if not os.path.exists(full):
            raise FileNotFoundError(f"File not found in storage: {path}")
        size = os.path.getsize(full)
        return FileRef(path=full, size_bytes=size, name=os.path.basename(full))

    def put(self, file_path: str) -> FileRef:
        """ينقل ملفاً موجوداً إلى التخزين ويرجع FileRef."""
        dest = os.path.join(self.base_dir, os.path.basename(file_path))
        shutil.copy2(file_path, dest)
        size = os.path.getsize(dest)
        return FileRef(path=dest, size_bytes=size, name=os.path.basename(dest))

    # ── Extra (مطلوب داخلياً من UploadService) ───────────────

    def save_file(self, file_data: bytes, file_path: str) -> bool:
        """يحفظ bytes مباشرة — مطلوب من UploadService (ليس في UML لكن ضروري)."""
        try:
            full_path = os.path.join(self.base_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as fp:
                fp.write(file_data)
            return True
        except Exception:
            return False

    def delete_file(self, path: str) -> bool:
        try:
            os.remove(os.path.join(self.base_dir, path))
            return True
        except Exception:
            return False
