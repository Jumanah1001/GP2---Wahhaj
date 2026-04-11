"""
Database.py
============
مدير بيانات الـ Dataset — data holder فقط.

المسؤوليات:
  - metadata الـ dataset (id, name, dates)
  - قائمة الصور (UAVImage)
  - AOI الاختياري
  - نطاق زمني اختياري
  - إضافة / حذف / استرجاع الصور
  - validation خفيف
  - serialization للـ DB

ليس مسؤولاً عن:
  - تحليل البيانات       → AnalysisRun (شخص D)
  - استخراج الـ features  → FeatureExtractor (شخص C)
  - نموذج AHP             → AHPModel (شخص D)
  - الـ heatmap           → SuitabilityHeatmap (شخص D)
  - أي AI/ML logic


"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from Wahhaj.UAVImage import UAVImage

logger = logging.getLogger(__name__)


class ValidationReport:
    """تقرير التحقق الخفيف من صحة الـ Dataset."""

    def __init__(self):
        self.is_valid    = True
        self.errors:   List[str] = []
        self.warnings: List[str] = []
        self.checked_at  = datetime.now(timezone.utc)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False
        logger.warning("Validation error: %s", msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.debug("Validation warning: %s", msg)

    def __repr__(self):
        return (f"ValidationReport(valid={self.is_valid}, "
                f"errors={len(self.errors)}, warnings={len(self.warnings)})")


class Database:
    """
    Dataset holder — يحمل بيانات الـ UAV المرفوعة.

    هذا الكائن هو الـ Dataset الذي يتدفق للـ pipeline:
        UploadService → Database → FeatureExtractor → AHPModel

    Attributes
    ----------
    dataset_id    : UUID فريد
    name          : اسم الـ dataset
    date_uploaded : وقت الإنشاء (UTC)
    updated_at    : آخر تعديل (UTC)
    images        : List[UAVImage]
    aoi           : Area of Interest اختياري — يُحدَّد لاحقاً أو من الـ metadata
    start_date    : بداية النطاق الزمني (اختياري)
    end_date      : نهاية النطاق الزمني (اختياري)

    ملاحظة للـ integration:
        FeatureExtractor (شخص C) يقرأ:
            database.images, database.aoi,
            database.start_date, database.end_date
        لا تُغيّر أسماء هذه الـ attributes.
    """

    def __init__(
        self,
        name: str,
        aoi=None,
        start_date: Optional[datetime] = None,
        end_date:   Optional[datetime] = None,
    ):
        self.dataset_id    = uuid4()
        self.name          = name
        self.date_uploaded = datetime.now(timezone.utc)
        self.updated_at    = datetime.now(timezone.utc)
        self.images: List[UAVImage] = []
        self.aoi           = aoi          # tuple أو AOI object — يُحدَّد لاحقاً
        self.start_date    = start_date
        self.end_date      = end_date
        logger.debug("Database created: '%s' (%s)", name, str(self.dataset_id)[:8])

    # ── Image Management ─────────────────────────────────────────────────────

    def add_image(self, image: UAVImage) -> None:
        """يضيف UAVImage للـ dataset."""
        self.images.append(image)
        self.updated_at = datetime.now(timezone.utc)
        logger.debug("Image added: %s → '%s'", image.filePath, self.name)

    def remove_image(self, image_id: str) -> bool:
        """يحذف UAVImage بالـ ID. يرجع True إذا حُذف."""
        before = len(self.images)
        self.images = [
            img for img in self.images
            if str(img.imageId) != image_id
        ]
        removed = len(self.images) < before
        if removed:
            self.updated_at = datetime.now(timezone.utc)
            logger.debug("Image removed: %s from '%s'", image_id[:8], self.name)
        return removed

    def get_image(self, image_id: str) -> Optional[UAVImage]:
        """يسترجع UAVImage بالـ ID."""
        for img in self.images:
            if str(img.imageId) == image_id:
                return img
        return None

    def image_count(self) -> int:
        """عدد الصور في الـ dataset."""
        return len(self.images)

    # ── Lightweight Validation ────────────────────────────────────────────────

    def validate(self) -> ValidationReport:
        """
        التحقق الخفيف من صحة الـ dataset.
        يتحقق من: الاسم، وجود صور، صحة كل صورة.
        لا يُشغّل أي منطق تحليل.
        """
        report = ValidationReport()

        if not self.name or not self.name.strip():
            report.add_error("Dataset name is empty")

        if not self.images:
            report.add_warning("Dataset has no images yet")

        for i, img in enumerate(self.images):
            if not img.filePath:
                report.add_error(f"Image {i}: filePath is empty")
            elif not img.validate():
                report.add_error(f"Image {i}: validation failed — {img.filePath}")

        logger.info("Validation '%s': %s", self.name, report)
        return report

    # ── Serialization (DB) ────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """
        تحويل إلى dict للحفظ في قاعدة البيانات.

        مثال مع PostgreSQL لاحقاً:
            session.execute(insert(DatasetTable), self.to_dict())
        """
        return {
            "dataset_id":    str(self.dataset_id),
            "name":          self.name,
            "date_uploaded": self.date_uploaded.isoformat(),
            "updated_at":    self.updated_at.isoformat(),
            "aoi":           self.aoi,
            "start_date":    self.start_date.isoformat() if self.start_date else None,
            "end_date":      self.end_date.isoformat()   if self.end_date   else None,
            "images":        [img.to_dict() for img in self.images],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Database":
        """
        استرجاع من dict (من قاعدة البيانات).

        مثال:
            row = session.execute(select(DatasetTable).where(...)).first()
            db  = Database.from_dict(dict(row))
        """
        obj = cls.__new__(cls)
        obj.dataset_id    = UUID(data["dataset_id"])
        obj.name          = data["name"]
        obj.date_uploaded = datetime.fromisoformat(data["date_uploaded"]) \
                            if "date_uploaded" in data else datetime.now(timezone.utc)
        obj.updated_at    = datetime.fromisoformat(data["updated_at"]) \
                            if "updated_at"    in data else datetime.now(timezone.utc)
        obj.aoi           = data.get("aoi")
        obj.start_date    = datetime.fromisoformat(data["start_date"]) \
                            if data.get("start_date") else None
        obj.end_date      = datetime.fromisoformat(data["end_date"]) \
                            if data.get("end_date")   else None
        obj.images        = [UAVImage.from_dict(img) for img in data.get("images", [])]
        logger.debug("Database restored: '%s' (%s)", obj.name, str(obj.dataset_id)[:8])
        return obj

    # ── DB CRUD Stubs ─────────────────────────────────────────────────────────

    def save(self, db_connection=None) -> bool:
        """
        يحفظ في قاعدة البيانات.
        TODO: ربط بـ SQLAlchemy / PostgreSQL لاحقاً.
        """
        if db_connection is None:
            logger.debug("save(): no DB connection — in-memory only")
            return True
        # session.merge(DatasetModel(**self.to_dict()))
        # session.commit()
        logger.info("Dataset saved: %s", str(self.dataset_id)[:8])
        return True

    @classmethod
    def find_by_id(
        cls, dataset_id: str, db_connection=None
    ) -> Optional["Database"]:
        """
        يسترجع Dataset بالـ ID.
        TODO: ربط بـ DB لاحقاً.
        """
        if db_connection is None:
            logger.debug("find_by_id(): no DB connection")
            return None
        # row = session.get(DatasetModel, dataset_id)
        # return cls.from_dict(row.to_dict()) if row else None
        return None

    @classmethod
    def find_by_name(
        cls, name: str, db_connection=None
    ) -> List["Database"]:
        """
        يسترجع Datasets بالاسم.
        TODO: ربط بـ DB لاحقاً.
        """
        if db_connection is None:
            logger.debug("find_by_name(): no DB connection")
            return []
        return []

    def delete(self, db_connection=None) -> bool:
        """
        يحذف من قاعدة البيانات.
        TODO: ربط بـ DB لاحقاً.
        """
        if db_connection is None:
            logger.debug("delete(): no DB connection")
            return True
        # session.delete(session.get(DatasetModel, self.dataset_id))
        # session.commit()
        logger.info("Dataset deleted: %s", str(self.dataset_id)[:8])
        return True

    # ── Dunder ───────────────────────────────────────────────────────────────

    def __repr__(self):
        return (f"Database(id={self.dataset_id}, "
                f"name={self.name!r}, images={len(self.images)})")


# ── self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    db = Database("Riyadh Survey 2025")
    img = UAVImage("data/drone.png", "4K")
    db.add_image(img)

    # validate
    report = db.validate()
    print("Validation:", report)

    # get image
    found = db.get_image(str(img.imageId))
    assert found is not None
    print("get_image  : OK")

    # to_dict / from_dict
    d   = db.to_dict()
    db2 = Database.from_dict(d)
    assert str(db2.dataset_id) == str(db.dataset_id)
    assert len(db2.images)     == 1
    print("Serialization: OK")

    # remove
    removed = db.remove_image(str(img.imageId))
    assert removed and len(db.images) == 0
    print("remove_image: OK")

    print("✅ Database all tests passed")
