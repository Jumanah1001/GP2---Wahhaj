# wahhaj/models.py — Single Source of Truth للـ shared types
#
# ⚠️ قواعد ثابتة — لا تعدّل إلا بعد إخبار الفريق:
#   • AOI = Tuple[float,float,float,float]  — (lon_min, lat_min, lon_max, lat_max)
#     لا تحوّله إلى dataclass؛ FeatureExtractor و Adapter يفكّكانه كـ tuple.
#   • Raster هو المرجع الوحيد — لا تعرّف Raster في أي ملف آخر.
#   • FileRef هو المرجع الوحيد — SuitabilityHeatmap يستخدمه مباشرة.
#   • SiteInfo هو المرجع الوحيد — SuitabilityHeatmap و SiteCandidate يستوردانه منه.
#
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# AOI — type alias فقط، لا dataclass
# (lon_min, lat_min, lon_max, lat_max)  ← WGS-84 decimal degrees
# ---------------------------------------------------------------------------
AOI = Tuple[float, float, float, float]


# ---------------------------------------------------------------------------
# Raster
# ---------------------------------------------------------------------------
@dataclass
class Raster:
    """
    2-D geographic raster.

    data      : float32 ndarray
    nodata    : sentinel value (default -9999.0)
    crs       : coordinate reference system string
    transform : (x_origin, x_res, y_origin, y_res) — north-up → y_res < 0
    metadata  : free-form dict (layer name, source, unit, …)
    """
    data:      np.ndarray
    nodata:    float             = -9999.0
    crs:       str               = "EPSG:4326"
    transform: Tuple[float, ...] = (0.0, 1.0, 0.0, -1.0)
    metadata:  Dict[str, Any]    = field(default_factory=dict)

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.data.shape

    def statistics(self) -> Dict[str, Any]:
        """إحصاءات بسيطة — تُستخدم في AnalysisRun.summary()"""
        valid = self.data[self.data != self.nodata]
        if valid.size == 0:
            return {"count": 0, "min": None, "max": None, "mean": None}
        return {
            "count": int(valid.size),
            "min":   float(valid.min()),
            "max":   float(valid.max()),
            "mean":  float(valid.mean()),
        }


# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------
@dataclass
class BoundingBox:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.xmin, self.ymin, self.xmax, self.ymax)

    def to_aoi(self) -> AOI:
        """تحويل إلى AOI tuple: (lon_min, lat_min, lon_max, lat_max)"""
        return (self.xmin, self.ymin, self.xmax, self.ymax)


# ---------------------------------------------------------------------------
# Point
# ---------------------------------------------------------------------------
@dataclass
class Point:
    """Geographic point — WGS-84 decimal degrees."""
    lon: float
    lat: float

    def __str__(self) -> str:
        return f"({self.lat:.6f}°N, {self.lon:.6f}°E)"


# ---------------------------------------------------------------------------
# FileRef
# ---------------------------------------------------------------------------
@dataclass
class FileRef:
    """
    مرجع لملف محفوظ.
    • size_bytes : الحجم بالبايت
    • name       : اسم الملف القصير (مطلوب من SuitabilityHeatmap.export_pdf)
    """
    path:       str
    size_bytes: int = 0
    name:       str = ""


# ---------------------------------------------------------------------------
# SiteInfo
# ---------------------------------------------------------------------------
@dataclass
class SiteInfo:
    """
    معلومات موقع عند النقر — تُرجع من SuitabilityHeatmap.inspect().
    تُستورد من هنا في SuitabilityHeatmap و SiteCandidate.
    """
    site_id:     str
    description: str
    coordinates: Tuple[float, float]   # (lon, lat)
