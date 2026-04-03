from dataclasses import dataclass
from typing import List


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
