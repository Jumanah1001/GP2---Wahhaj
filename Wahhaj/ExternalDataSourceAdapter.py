# wahhaj/ExternalDataSourceAdapter.py
# ─────────────────────────────────────────────────────────────
# Data Extraction
# Responsibility: fetch environmental raster data from external APIs
#
# CONTRACT (must not change method signatures):
#   fetchGHI(aoi, time)           -> Raster
#   fetchLST(aoi, time)           -> Raster
#   fetchSunshineHours(aoi, time) -> Raster
#   FetchElevation(aoi, time)     -> Raster   ← capital F, intentional
#
# NOTE: All method names use camelCase to match exactly what
#       FeatureExtractor calls. Do NOT rename back to snake_case.
#
# NOTE: Raster and AOI are imported from models.py (Single Source of Truth).
#       Never define Raster locally in this file.
#
# NOTE: This keeps mock behavior for LST and Elevation for now.
#       GHI and Sunshine Hours now use Open-Meteo.
# ─────────────────────────────────────────────────────────────

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np
import requests

from .models import Raster, AOI


class ExternalDataSourceAdapter:
    """
    Adapter between FeatureExtractor and external data sources
    (Open-Meteo, NASA POWER, SRTM elevation, LST APIs, etc.)

    Current strategy:
    - Real API for GHI and Sunshine Hours using Open-Meteo
    - Synthetic/mock rasters for LST and Elevation for now
    """

    GRID_ROWS = 5
    GRID_COLS = 5
    OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, api_key: Optional[str] = None):
        # NOTE: api_key is optional — adapter works without it in current mode
        self.api_key = api_key

    # ── Public methods (the CONTRACT) ────────────────────────

    def fetchGHI(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch Global Horizontal Irradiance-like raster.

        We use Open-Meteo daily shortwave_radiation_sum as the solar
        irradiance proxy, then average values over the selected time window
        for each centroid in a 5x5 grid.
        """
        values = self._fetch_daily_grid_values(
            aoi=aoi,
            time=time,
            variable="shortwave_radiation_sum",
        )
        return self._build_raster_from_grid(
            values=values,
            layer="ghi",
            source="open-meteo",
            unit="MJ/m²/day (mean over window)",
        )

    def fetchLST(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch Land Surface Temperature raster.

        Still mock for now.
        """
        return self._make_synthetic_raster(aoi, layer="lst")

    def fetchSunshineHours(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch average sunshine hours per day raster.

        Open-Meteo returns sunshine_duration in seconds per day.
        We convert it to hours after averaging over the selected time window.
        """
        values_seconds = self._fetch_daily_grid_values(
            aoi=aoi,
            time=time,
            variable="sunshine_duration",
        )
        values_hours = np.where(
            values_seconds != -9999.0,
            values_seconds / 3600.0,
            -9999.0
        ).astype(np.float32)

        return self._build_raster_from_grid(
            values=values_hours,
            layer="sunshine",
            source="open-meteo",
            unit="hours/day (mean over window)",
        )

    def FetchElevation(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch elevation raster (meters above sea level).

        Still mock for now.
        NOTE: Capital F — matches exactly what FeatureExtractor calls.
        """
        return self._make_synthetic_raster(aoi, layer="elevation")

    # ── Real API helpers ─────────────────────────────────────

    def _fetch_daily_grid_values(
        self,
        aoi: AOI,
        time: datetime,
        variable: str,
    ) -> np.ndarray:
        """
        Build a 5x5 centroid grid over the AOI, fetch one aggregated value
        per centroid, and return a (5, 5) float32 array.
        """
        centroids = self._build_5x5_centroids(aoi)
        grid = np.full((self.GRID_ROWS, self.GRID_COLS), -9999.0, dtype=np.float32)

        start_date, end_date = self._resolve_time_window(time)

        for row, col, center_lat, center_lon in centroids:
            value = self._fetch_open_meteo_daily_mean(
                lat=center_lat,
                lon=center_lon,
                start_date=start_date,
                end_date=end_date,
                variable=variable,
            )
            grid[row, col] = value

        return grid

    def _fetch_open_meteo_daily_mean(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        variable: str,
    ) -> float:
        """
        Fetch a daily time series from Open-Meteo and return its mean value.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": variable,
            "timezone": "auto",
        }

        response = requests.get(
            self.OPEN_METEO_ARCHIVE_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        daily = payload.get("daily", {})
        values = daily.get(variable)

        if not values:
            return -9999.0

        clean_values = [float(v) for v in values if v is not None]
        if not clean_values:
            return -9999.0

        return float(np.mean(clean_values))

    def _resolve_time_window(self, time: datetime) -> Tuple[str, str]:
        """
        Resolve a stable analysis window for site suitability.

        Current choice:
        - previous 30 days ending at the provided datetime
        """
        end_date = time.date()
        start_date = end_date - timedelta(days=29)
        return start_date.isoformat(), end_date.isoformat()

    def _build_5x5_centroids(self, aoi: AOI) -> List[Tuple[int, int, float, float]]:
        """
        Build centroids for a 5x5 grid over the AOI.

        AOI format:
            (lon_min, lat_min, lon_max, lat_max)

        Convention:
        - row 0 = north/top
        - col 0 = west/left
        """
        lon_min, lat_min, lon_max, lat_max = aoi

        lat_step = (lat_max - lat_min) / self.GRID_ROWS
        lon_step = (lon_max - lon_min) / self.GRID_COLS

        points: List[Tuple[int, int, float, float]] = []

        for row in range(self.GRID_ROWS):
            cell_max_lat = lat_max - (row * lat_step)
            cell_min_lat = cell_max_lat - lat_step
            center_lat = (cell_min_lat + cell_max_lat) / 2.0

            for col in range(self.GRID_COLS):
                cell_min_lon = lon_min + (col * lon_step)
                cell_max_lon = cell_min_lon + lon_step
                center_lon = (cell_min_lon + cell_max_lon) / 2.0

                points.append((row, col, center_lat, center_lon))

        return points

    def _build_raster_from_grid(
        self,
        values: np.ndarray,
        layer: str,
        source: str,
        unit: str,
    ) -> Raster:
        """
        Wrap a (5,5) grid into the shared Raster model.
        """
        return Raster(
            data=values.astype(np.float32),
            nodata=-9999.0,
            metadata={
                "layer": layer,
                "shape": tuple(values.shape),
                "source": source,
                "unit": unit,
                "grid_type": "centroid_5x5",
            },
        )

    # ── Mock helpers (kept for remaining layers) ─────────────

    def _make_synthetic_raster(self, aoi: AOI, layer: str) -> Raster:
        """
        Returns a mock 50×50 float32 raster for development.

        IMPORTANT:
          - dtype  : float32
          - nodata : -9999.0
          - shape  : 50×50 for testing
        """
        data = np.random.uniform(0.3, 1.0, (50, 50)).astype(np.float32)
        return Raster(
            data=data,
            nodata=-9999.0,
            metadata={"layer": layer, "source": "mock"},
        )
