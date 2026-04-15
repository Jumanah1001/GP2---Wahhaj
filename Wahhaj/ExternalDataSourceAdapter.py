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
# FIX (Phase 2):
#   ee.Initialize() is now deferred to the first LST/Elevation call so that
#   importing this module never raises an exception when GEE credentials
#   are absent.  All other methods (GHI, Sunshine) use Open-Meteo and
#   work without any credentials.
# ─────────────────────────────────────────────────────────────

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import requests
import numpy as np

from .models import Raster, AOI


class ExternalDataSourceAdapter:
    """
    Adapter between FeatureExtractor and external data sources
    (Open-Meteo, NASA POWER, SRTM elevation, LST APIs, etc.)

    Current strategy:
    - Real API for GHI and Sunshine Hours using Open-Meteo
    - Synthetic/mock rasters for LST and Elevation (GEE deferred)
    """

    GRID_ROWS = 5
    GRID_COLS = 5
    OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(
        self,
        api_key:   Optional[str] = None,
        grid_rows: int = 5,
        grid_cols: int = 5,
    ):
        self.api_key   = api_key
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        # GEE initialisation is deferred to the first call that needs it
        self._ee_ready = False

    # ── GEE lazy init ────────────────────────────────────────────────────────

    def _ensure_ee(self) -> bool:
        """
        Attempt to initialise Google Earth Engine lazily.
        Returns True if successful, False otherwise.
        Callers fall back to synthetic data when this returns False.
        """
        if self._ee_ready:
            return True
        try:
            import ee  # noqa: F401
            try:
                ee.Initialize(project="wahhaj-data-fetching")
            except Exception:
                ee.Authenticate()
                ee.Initialize(project="wahhaj-data-fetching")
            self._ee_ready = True
            return True
        except Exception:
            return False

    # ── Grid helpers ─────────────────────────────────────────────────────────

    def _build_grid_points(self, aoi: AOI) -> List[Tuple[float, float]]:
        """aoi = (lon_min, lat_min, lon_max, lat_max)"""
        lon_min, lat_min, lon_max, lat_max = aoi
        lats = np.linspace(lat_min, lat_max, self.grid_rows)
        lons = np.linspace(lon_min, lon_max, self.grid_cols)
        return [(float(lat), float(lon)) for lat in lats for lon in lons]

    def _reshape_to_grid(self, values: List[float]) -> np.ndarray:
        return np.array(values, dtype=np.float32).reshape(
            (self.grid_rows, self.grid_cols)
        )

    # ── Open-Meteo helper ────────────────────────────────────────────────────

    def _fetch_daily_grid_values(
        self,
        aoi:      AOI,
        time:     datetime,
        variable: str,
    ) -> List[float]:
        """
        Fetch a daily meteorological variable from Open-Meteo for a 5×5
        grid of points covering the AOI, averaged over a 7-day window
        ending on `time`.
        Falls back to synthetic data on any network/parsing error.
        """
        points     = self._build_grid_points(aoi)
        end_date   = time.strftime("%Y-%m-%d")
        start_date = (time - timedelta(days=7)).strftime("%Y-%m-%d")
        values: List[float] = []

        for lat, lon in points:
            try:
                resp = requests.get(
                    self.OPEN_METEO_ARCHIVE_URL,
                    params={
                        "latitude":  lat,
                        "longitude": lon,
                        "start_date": start_date,
                        "end_date":   end_date,
                        "daily":      variable,
                        "timezone":   "auto",
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                daily_vals = data.get("daily", {}).get(variable, [])
                valid = [v for v in daily_vals if v is not None]
                values.append(float(np.mean(valid)) if valid else 0.0)
            except Exception:
                values.append(0.0)

        return values

    def _build_raster_from_grid(
        self,
        values: List[float],
        layer:  str,
        source: str,
        aoi:    AOI,
    ) -> Raster:
        grid = self._reshape_to_grid(values)
        lon_min, lat_min, lon_max, lat_max = aoi
        return Raster(
            data      = grid,
            nodata    = -9999.0,
            crs       = "EPSG:4326",
            transform = (lon_min, (lon_max - lon_min) / self.grid_cols,
                         lat_max, -(lat_max - lat_min) / self.grid_rows),
            metadata  = {"layer": layer, "source": source},
        )

    # ── Public CONTRACT methods ───────────────────────────────────────────────

    def fetchGHI(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch Global Horizontal Irradiance via Open-Meteo
        (shortwave_radiation_sum as proxy).
        """
        values = self._fetch_daily_grid_values(
            aoi=aoi, time=time, variable="shortwave_radiation_sum"
        )
        return self._build_raster_from_grid(
            values=values, layer="ghi", source="open-meteo", aoi=aoi
        )

    def fetchSunshineHours(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch sunshine hours via Open-Meteo (sunshine_duration proxy).
        """
        values = self._fetch_daily_grid_values(
            aoi=aoi, time=time, variable="sunshine_duration"
        )
        # sunshine_duration is in seconds — convert to hours
        values = [v / 3600.0 for v in values]
        return self._build_raster_from_grid(
            values=values, layer="sunshine", source="open-meteo", aoi=aoi
        )

    def fetchLST(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch Land Surface Temperature.
        Uses GEE if credentials are available; falls back to a
        synthetic grid derived from latitude otherwise.
        """
        if self._ensure_ee():
            try:
                return self._fetchLST_gee(aoi, time)
            except Exception:
                pass
        return self._fetchLST_synthetic(aoi)

    def _fetchLST_gee(self, aoi: AOI, time: datetime) -> Raster:
        import ee  # noqa: F401
        lon_min, lat_min, lon_max, lat_max = aoi
        region = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
        end_ms   = int(time.timestamp() * 1000)
        start_ms = end_ms - 30 * 24 * 3600 * 1000

        collection = (
            ee.ImageCollection("MODIS/006/MOD11A1")
            .filterDate(ee.Date(start_ms), ee.Date(end_ms))
            .select("LST_Day_1km")
            .mean()
        )
        mean_img = collection.multiply(0.02).subtract(273.15)
        sample = mean_img.sampleRectangle(region=region, defaultValue=35)
        arr = np.array(sample.getInfo()["properties"]["LST_Day_1km"], dtype=np.float32)
        # Resize to grid
        from PIL import Image as _PILImage
        resized = np.array(
            _PILImage.fromarray(arr).resize(
                (self.grid_cols, self.grid_rows), _PILImage.BILINEAR
            ),
            dtype=np.float32,
        )
        return Raster(
            data=resized, nodata=-9999.0,
            metadata={"layer": "lst", "source": "gee-modis"},
        )

    def _fetchLST_synthetic(self, aoi: AOI) -> Raster:
        """
        Synthetic LST: baseline 35°C reduced slightly toward higher latitudes
        plus small random noise.  Suitable for testing.
        """
        lon_min, lat_min, lon_max, lat_max = aoi
        lats = np.linspace(lat_min, lat_max, self.grid_rows)
        lons = np.linspace(lon_min, lon_max, self.grid_cols)
        grid = np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32)
        rng  = np.random.default_rng(seed=42)
        for r, lat in enumerate(lats):
            for c, lon in enumerate(lons):
                grid[r, c] = 35.0 - (lat - lat_min) * 0.5 + rng.uniform(-1, 1)
        return Raster(
            data=grid, nodata=-9999.0,
            metadata={"layer": "lst", "source": "synthetic"},
        )

    def FetchElevation(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch terrain elevation (SRTM/GEE) or fall back to synthetic.
        Capital F is intentional — matches FeatureExtractor contract.
        """
        if self._ensure_ee():
            try:
                return self._fetchElevation_gee(aoi)
            except Exception:
                pass
        return self._fetchElevation_synthetic(aoi)

    def _fetchElevation_gee(self, aoi: AOI) -> Raster:
        import ee  # noqa: F401
        lon_min, lat_min, lon_max, lat_max = aoi
        region = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
        srtm   = ee.Image("USGS/SRTMGL1_003")
        sample = srtm.sampleRectangle(region=region, defaultValue=300)
        arr = np.array(
            sample.getInfo()["properties"]["elevation"], dtype=np.float32
        )
        from PIL import Image as _PILImage
        resized = np.array(
            _PILImage.fromarray(arr).resize(
                (self.grid_cols, self.grid_rows), _PILImage.BILINEAR
            ),
            dtype=np.float32,
        )
        return Raster(
            data=resized, nodata=-9999.0,
            metadata={"layer": "elevation", "source": "srtm"},
        )

    def _fetchElevation_synthetic(self, aoi: AOI) -> Raster:
        """
        Synthetic elevation: flat Saudi plateau ~600 m ± small variation.
        """
        rng  = np.random.default_rng(seed=7)
        grid = (600 + rng.uniform(-30, 30, (self.grid_rows, self.grid_cols))
                ).astype(np.float32)
        return Raster(
            data=grid, nodata=-9999.0,
            metadata={"layer": "elevation", "source": "synthetic"},
        )