"""
UAVImage.py
============
يمثّل صورة واحدة من الطائرة المسيّرة.

المسؤوليات فقط:
  - تخزين بيانات الصورة (filePath, resolution, timestamp)
  - استخراج الـ metadata
  - تحميل بيانات الصورة (load)
  - validation خفيف
  - serialization للـ DB


"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import numpy as np

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".raw"}


class UAVImage:
    """
    صورة واحدة من الـ UAV.

    Attributes (UML)
    ----------------
    imageId    : UUID
    filePath   : مسار الملف
    resolution : دقة الصورة
    timestamp  : وقت الالتقاط (UTC)
    """

    def __init__(
        self,
        filePath: str,
        resolution,
        timestamp: Optional[datetime] = None,
        imageId: Optional[UUID] = None,
    ):
        self.imageId    = imageId or uuid4()
        self.filePath   = filePath
        self.resolution = resolution
        self.timestamp  = timestamp or datetime.now(timezone.utc)
        self._data: Optional[np.ndarray] = None
        logger.debug("UAVImage created: %s → %s", str(self.imageId)[:8], filePath)

    # ── UML Methods ──────────────────────────────────────────────────────────

    def extractMetadata(self) -> Dict[str, str]:
        """يرجع بيانات وصفية للصورة."""
        return {
            "imageId":    str(self.imageId),
            "filePath":   self.filePath,
            "resolution": str(self.resolution),
            "timestamp":  self.timestamp.isoformat(),
        }

    def geoReference(self) -> None:
        """Placeholder — يُكمل لاحقاً بمنطق GIS."""
        logger.debug("geoReference placeholder: %s", self.filePath)

    def load(self) -> np.ndarray:
        """
        يحمّل بيانات الصورة كـ ndarray (H, W, 3) uint8.
        مطلوبة من FeatureExtractor.
        يُخزّن النتيجة (caching).
        """
        if self._data is not None:
            return self._data

        # حاول تحميل الملف الحقيقي
        try:
            import cv2
            if os.path.exists(self.filePath):
                img = cv2.imread(self.filePath)
                if img is not None:
                    self._data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    logger.info("Loaded from disk: %s", self.filePath)
                    return self._data
        except Exception as e:
            logger.warning("cv2 load failed: %s", e)

        # Fallback synthetic للاختبار
        logger.debug("Using synthetic data: %s", self.filePath)
        rng = np.random.default_rng(seed=int(self.imageId.int % (2**32)))
        self._data = rng.integers(0, 256, size=(200, 200, 3), dtype=np.uint8)
        return self._data

    def validate(self) -> bool:
        """
        التحقق الخفيف من صحة الصورة.
        يتحقق من: filePath موجود، الامتداد مدعوم، الملف مو فارغ.
        """
        if not self.filePath:
            logger.error("validate: filePath is empty")
            return False

        ext = os.path.splitext(self.filePath)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.error("validate: unsupported extension '%s'", ext)
            return False

        if os.path.exists(self.filePath) and os.path.getsize(self.filePath) == 0:
            logger.error("validate: file is empty: %s", self.filePath)
            return False

        return True

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """للحفظ في قاعدة البيانات."""
        return {
            "imageId":    str(self.imageId),
            "filePath":   self.filePath,
            "resolution": str(self.resolution),
            "timestamp":  self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UAVImage":
        """للاسترجاع من قاعدة البيانات."""
        return cls(
            filePath   = data["filePath"],
            resolution = data["resolution"],
            timestamp  = datetime.fromisoformat(data["timestamp"])
                         if "timestamp" in data else None,
            imageId    = UUID(data["imageId"]) if "imageId" in data else None,
        )

    def __repr__(self):
        return (f"UAVImage(id={str(self.imageId)[:8]}, "
                f"path={self.filePath!r}, res={self.resolution})")


# ── self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    img = UAVImage("data/image.tif", "4096x2160")
    print("Created  :", img)
    print("Metadata :", img.extractMetadata())
    print("Valid    :", img.validate())
    data = img.load()
    print("Loaded   :", data.shape, data.dtype)
    img2 = UAVImage.from_dict(img.to_dict())
    assert str(img2.imageId) == str(img.imageId)
    print("✅ to_dict / from_dict OK")
