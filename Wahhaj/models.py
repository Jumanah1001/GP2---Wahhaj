from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, List, Optional
import numpy as np

# --------------------------------------------------
# Types
# --------------------------------------------------

AOI = Tuple[float, float, float, float]

# --------------------------------------------------
# Core Data Structures
# --------------------------------------------------

@dataclass
class Raster:
    data: np.ndarray
    nodata: float = -9999.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def shape(self):
        return self.data.shape


# --------------------------------------------------

@dataclass
class Point:
    lon: float
    lat: float


# --------------------------------------------------

@dataclass
class SiteInfo:
    lon: float
    lat: float
    suitability_score: float
    rank: Optional[int] = None
    attrs: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------

@dataclass
class FileRef:
    path: str
    size_bytes: int = 0
    content_type: str = "application/octet-stream"


# --------------------------------------------------

@dataclass
class TileSet:
    tiles: List = field(default_factory=list)


# --------------------------------------------------
# Extra (احتفظنا فيها لأنها مفيدة لك)
# --------------------------------------------------

@dataclass(frozen=True)
class BoundingBox:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


@dataclass(frozen=True)
class GridCell:
    row: int
    col: int
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    center_lat: float
    center_lon: float


@dataclass(frozen=True)
class SolarFeatureGrids:
    solar_irradiance_grid: List[List[float]]
    sunshine_hours_grid: List[List[float]]