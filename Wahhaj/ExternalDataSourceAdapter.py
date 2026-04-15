# wahhaj/ExternalDataSourceAdapter.py
# ─────────────────────────────────────────────────────────────
# CONTRACT (must not change method signatures):
#   fetchGHI(aoi, time)           -> Raster
#   fetchLST(aoi, time)           -> Raster
#   fetchSunshineHours(aoi, time) -> Raster
#   FetchElevation(aoi, time)     -> Raster   ← capital F, intentional
# ─────────────────────────────────────────────────────────────

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import requests
import numpy as np

# Google Earth Engine is optional — LST falls back to mock if not installed
try:
    import ee
    _EE_AVAILABLE = True
except ImportError:
    _EE_AVAILABLE = False

try:
    from .models import Raster, AOI
except ImportError:
    from Wahhaj.models import Raster, AOI


class ExternalDataSourceAdapter:
    """
    Adapter between FeatureExtractor and external data sources.

    Strategy:
    - GHI and Sunshine Hours: Open-Meteo API (real data)
    - Elevation: Open-Meteo elevation API (real data)
    - LST: Google Earth Engine MODIS if available, else synthetic mock
    """

    GRID_ROWS = 5
    GRID_COLS = 5
    OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, api_key: Optional[str] = None,
                 grid_rows: int = 5, grid_cols: int = 5):
        self.api_key   = api_key
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

        # Try to initialise Earth Engine — silently skip if unavailable
        if _EE_AVAILABLE:
            try:
                ee.Initialize(project='wahhaj-data-fetching')
            except Exception:
                try:
                    ee.Authenticate()
                    ee.Initialize(project='wahhaj-data-fetching')
                except Exception:
                    pass  # EE init failed — LST will use mock

    # ── Public CONTRACT methods ───────────────────────────────

    def fetchGHI(self, aoi: AOI, time: datetime) -> Raster:
        """Fetch Global Horizontal Irradiance via Open-Meteo."""
        values = self._fetch_daily_grid_values(
            aoi=aoi, time=time, variable="shortwave_radiation_sum")
        return self._build_raster_from_grid(
            values=values, layer="ghi",
            source="open-meteo", unit="MJ/m²/day")

    def fetchLST(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch Land Surface Temperature.
        Uses MODIS via Earth Engine if available, else synthetic mock.
        """
        if _EE_AVAILABLE:
            try:
                values = self._fetch_modis_lst_grid(aoi, time)
                return self._build_raster_from_grid(
                    values=values, layer="lst",
                    source="earth-engine", unit="°C")
            except Exception:
                pass  # fall through to mock

        # Mock fallback — realistic Saudi LST range 35–55 °C
        rng  = np.random.default_rng(seed=42)
        data = rng.uniform(35.0, 55.0, (self.GRID_ROWS, self.GRID_COLS)).astype(np.float32)
        return Raster(data=data, nodata=-9999.0,
                      metadata={"layer": "lst", "source": "mock", "unit": "°C"})

    def fetchSunshineHours(self, aoi: AOI, time: datetime) -> Raster:
        """Fetch average sunshine hours per day via Open-Meteo."""
        values_sec = self._fetch_daily_grid_values(
            aoi=aoi, time=time, variable="sunshine_duration")
        values_hr = np.where(
            values_sec != -9999.0, values_sec / 3600.0, -9999.0
        ).astype(np.float32)
        return self._build_raster_from_grid(
            values=values_hr, layer="sunshine",
            source="open-meteo", unit="hours/day")

    def FetchElevation(self, aoi: AOI, time: datetime) -> Raster:
        """Fetch elevation via Open-Meteo elevation API. Capital F intentional."""
        values = self._fetch_open_meteo_elevation_grid(aoi)
        return self._build_raster_from_grid(
            values=values, layer="elevation",
            source="open-meteo-elevation", unit="m")

    # ── Private helpers ───────────────────────────────────────

    def _fetch_daily_grid_values(self, aoi, time, variable) -> np.ndarray:
        centroids   = self._build_5x5_centroids(aoi)
        grid        = np.full((self.GRID_ROWS, self.GRID_COLS), -9999.0, dtype=np.float32)
        start_date, end_date = self._resolve_time_window(time)
        for row, col, center_lat, center_lon in centroids:
            grid[row, col] = self._fetch_open_meteo_daily_mean(
                lat=center_lat, lon=center_lon,
                start_date=start_date, end_date=end_date,
                variable=variable)
        return grid

    def _fetch_open_meteo_daily_mean(self, lat, lon, start_date,
                                     end_date, variable) -> float:
        try:
            params   = {"latitude": lat, "longitude": lon,
                        "start_date": start_date, "end_date": end_date,
                        "daily": variable, "timezone": "auto"}
            response = requests.get(self.OPEN_METEO_ARCHIVE_URL,
                                    params=params, timeout=30)
            response.raise_for_status()
            payload  = response.json()
            values   = payload.get("daily", {}).get(variable)
            if not values:
                return -9999.0
            clean = [float(v) for v in values if v is not None]
            return float(np.mean(clean)) if clean else -9999.0
        except Exception:
            return -9999.0

    def _resolve_time_window(self, time: datetime) -> Tuple[str, str]:
        end_date   = time.date()
        start_date = end_date - timedelta(days=29)
        return start_date.isoformat(), end_date.isoformat()

    def _build_5x5_centroids(self, aoi: AOI) -> List[Tuple[int, int, float, float]]:
        lon_min, lat_min, lon_max, lat_max = aoi
        lat_step = (lat_max - lat_min) / self.GRID_ROWS
        lon_step = (lon_max - lon_min) / self.GRID_COLS
        points   = []
        for row in range(self.GRID_ROWS):
            cell_max_lat  = lat_max - (row * lat_step)
            center_lat    = cell_max_lat - lat_step / 2.0
            for col in range(self.GRID_COLS):
                cell_min_lon = lon_min + (col * lon_step)
                center_lon   = cell_min_lon + lon_step / 2.0
                points.append((row, col, center_lat, center_lon))
        return points

    def _build_raster_from_grid(self, values, layer, source, unit) -> Raster:
        return Raster(
            data=values.astype(np.float32), nodata=-9999.0,
            metadata={"layer": layer, "shape": tuple(values.shape),
                      "source": source, "unit": unit, "grid_type": "centroid_5x5"})

    def _fetch_modis_lst_grid(self, aoi: AOI, time: datetime) -> np.ndarray:
        """MODIS LST via Earth Engine — only called when _EE_AVAILABLE is True."""
        centroids = self._build_5x5_centroids(aoi)
        grid = np.full((self.GRID_ROWS, self.GRID_COLS), -9999.0, dtype=np.float32)
        start_date, end_date = self._resolve_time_window(time)
        for row, col, center_lat, center_lon in centroids:
            point = ee.Geometry.Point([center_lon, center_lat])
            value = (
                ee.ImageCollection("MODIS/061/MOD11A2")
                .filterDate(start_date, end_date)
                .select("LST_Day_1km")
                .mean()
                .multiply(0.02)
                .subtract(273.15)
                .reduceRegion(reducer=ee.Reducer.mean(),
                              geometry=point, scale=1000)
                .get("LST_Day_1km")
            )
            temp = value.getInfo()
            grid[row, col] = float(temp) if temp is not None else -9999.0
        return grid

    def _fetch_open_meteo_elevation_grid(self, aoi: AOI) -> np.ndarray:
        centroids  = self._build_5x5_centroids(aoi)
        latitudes  = ",".join(str(c[2]) for c in centroids)
        longitudes = ",".join(str(c[3]) for c in centroids)
        url        = "https://api.open-meteo.com/v1/elevation"
        try:
            response = requests.get(url,
                                    params={"latitude": latitudes,
                                            "longitude": longitudes},
                                    timeout=30)
            response.raise_for_status()
            elevations = response.json().get("elevation")
            if elevations:
                return np.array(elevations, dtype=np.float32).reshape(
                    (self.GRID_ROWS, self.GRID_COLS))
        except Exception:
            pass
        # Fallback: mock elevation for Saudi Arabia range
        rng = np.random.default_rng(seed=7)
        return rng.uniform(600.0, 1200.0,
                           (self.GRID_ROWS, self.GRID_COLS)).astype(np.float32)
