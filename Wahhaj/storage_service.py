import os
import shutil
from dataclasses import dataclass


# FileRef في الـ UML
@dataclass(frozen=True)
class FileRef:
    path: str
    size: int


class StorageService:

    def __init__(self, base_dir: str = "storage"):
        """
        base_dir: المجلد اللي تنخزن فيه الملفات
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    # put(file): FileRef
    def put(self, file_path: str) -> FileRef:
        """
        يخزن ملف في مجلد التخزين ويرجع FileRef
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError("Source file does not exist")

        filename = os.path.basename(file_path)
        dest_path = os.path.join(self.base_dir, filename)

        if os.path.exists(dest_path):
            raise FileExistsError("File already exists in storage")

        try:
            shutil.copy(file_path, dest_path)
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
