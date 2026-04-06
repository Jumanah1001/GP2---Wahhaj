"""
wahhaj/storage_service.py
Contract: UploadService ↔ StorageService

⚠️ تغييرات مهمة:
  • get() يرفع FileNotFoundError إذا الملف غير موجود
    (UploadService._file_exists يعتمد على هذا السلوك)
  • FileRef يشمل الآن حقل name (من models.py v2)
"""
import os
import shutil
from wahhaj.models import FileRef


class StorageService:
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_file(self, file_data: bytes, file_path: str) -> bool:
        """يحفظ bytes مباشرة — مطلوب من UploadService."""
        try:
            full_path = os.path.join(self.base_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as fp:
                fp.write(file_data)
            return True
        except Exception:
            return False

    def put(self, file_path: str) -> FileRef:
        """ينقل ملفاً موجوداً إلى التخزين ويرجع FileRef."""
        dest = os.path.join(self.base_dir, os.path.basename(file_path))
        shutil.copy2(file_path, dest)
        size = os.path.getsize(dest)
        return FileRef(path=dest, size_bytes=size, name=os.path.basename(dest))

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

    def delete_file(self, path: str) -> bool:
        try:
            full = os.path.join(self.base_dir, path)
            os.remove(full)
            return True
        except Exception:
            return False            shutil.copy(file_path, dest_path)
        except PermissionError:
            raise PermissionError("No permission to write to storage directory")
        except OSError as e:
            raise RuntimeError(f"Storage error: {e}")

        return FileRef(
            path=dest_path,
            size=os.path.getsize(dest_path)
        )

    # get(path): FileRef
    def get(self, path: str) -> FileRef:
        """
        يرجع FileRef لملف مخزن
        """
        full_path = os.path.join(self.base_dir, path)

        if not os.path.exists(full_path):
            raise FileNotFoundError("File not found")

        return FileRef(
            path=full_path,
            size=os.path.getsize(full_path)
        )

    # deleteFile(file): bool
    def deleteFile(self, path: str) -> bool:
        """
        يحذف ملف من التخزين
        """
        full_path = os.path.join(self.base_dir, path)

        if not os.path.exists(full_path):
            raise FileNotFoundError("File not found")

        os.remove(full_path)
        return True

##test
if __name__ == "__main__":
    storage = StorageService()

    ref = storage.put("test.txt")
    print("PUT:", ref)

    ref2 = storage.get("test.txt")
    print("GET:", ref2)

    
    # result = storage.deleteFile("test.txt")
    # print("DELETE:", result)
