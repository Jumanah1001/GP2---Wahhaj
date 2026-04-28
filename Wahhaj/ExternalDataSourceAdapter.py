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

    def initialize_earth_engine(self) -> bool:
        """
        Public method to initialize Google Earth Engine.
        Returns True if Earth Engine is ready, False otherwise.
        """
        return self._ensure_ee()


    def _ensure_ee(self) -> bool:
        """
        Try to initialize Google Earth Engine.
        First tries the configured project ID.
        If it fails, tries the user's default Earth Engine project.
        """
        if self._ee_ready:
            return True

        try:
            import os
            import ee

            project_id = (
                os.getenv("EE_PROJECT_ID")
                or getattr(self, "ee_project_id", None)
                or "wahhaj-data-fetching"
            )

            try:
                ee.Initialize(project=project_id)
                self._ee_ready = True
                self._last_ee_error = None
                return True

            except Exception as project_error:
                try:
                    ee.Initialize()
                    self._ee_ready = True
                    self._last_ee_error = None
                    return True

                except Exception as default_error:
                    self._ee_ready = False
                    self._last_ee_error = (
                        f"Project initialize failed with project '{project_id}': {project_error}. "
                        f"Default initialize failed: {default_error}"
                    )
                    return False

        except Exception as exc:
            self._ee_ready = False
            self._last_ee_error = str(exc)
            return False
        
   

    # ── Grid helpers ─────────────────────────────────────────────────────────

    def _build_grid_points(self, aoi: AOI) -> List[Tuple[float, float]]:
        """aoi = (lon_min, lat_min, lon_max, lat_max)"""
        lon_min, lat_min, lon_max, lat_max = aoi
        lats = np.linspace(lat_min, lat_max, self.grid_rows)
        lons = np.linspace(lon_min, lon_max, self.grid_cols)
        return [(float(lat), float(lon)) for lat in lats for lon in lons]

    def _reshape_to_grid(self, values):
        arr = np.array(values, dtype=np.float32).flatten()

        expected_size = self.grid_rows * self.grid_cols

        if arr.size == expected_size:
            return arr.reshape((self.grid_rows, self.grid_cols))

        if arr.size == 1:
            return np.full(
                (self.grid_rows, self.grid_cols),
                float(arr[0]),
                dtype=np.float32,
            )

        raise ValueError(
            f"Expected {expected_size} values for a "
            f"{self.grid_rows}x{self.grid_cols} grid, but got {arr.size}."
        )

    #--------------------------------------------------------

    def _is_valid_real_raster(self, raster: Raster) -> bool:
        """
        Validate that a fetched raster contains real usable values.
        """
        if raster is None:
            return False

        if raster.data is None:
            return False

        data = raster.data.astype(np.float32)

        if data.size == 0:
            return False

        nodata = getattr(raster, "nodata", -9999.0)

        valid_mask = (data != nodata) & ~np.isnan(data)

        if not valid_mask.any():
            return False

        valid_values = data[valid_mask]

        if valid_values.size == 0:
            return False

        # If all values are exactly zero, this is suspicious for environmental data.
        if np.all(valid_values == 0):
            return False

        return True


    # ── Open-Meteo helper ────────────────────────────────────────────────────

    def _fetch_daily_grid_values(
        self,
        aoi: AOI,
        time: datetime,
        variable: str,
    ) -> List[float]:
        """
        Fetch a daily meteorological variable from Open-Meteo for a 5×5 grid.

        Tries multiple real historical windows before failing.
        This avoids stopping when the most recent archive data is unavailable.
        """
        points = self._build_grid_points(aoi)

        candidate_windows = [
            7,
            14,
            30,
            60,
        ]

        # Open-Meteo archive may not have very recent data immediately.
        # So we shift the end date a few days back.
        base_end_date = time.date() - timedelta(days=5)

        last_error = None

        for days in candidate_windows:
            end_date = base_end_date.strftime("%Y-%m-%d")
            start_date = (base_end_date - timedelta(days=days)).strftime("%Y-%m-%d")

            values: List[float] = []

            for lat, lon in points:
                try:
                    resp = requests.get(
                        self.OPEN_METEO_ARCHIVE_URL,
                        params={
                            "latitude": lat,
                            "longitude": lon,
                            "start_date": start_date,
                            "end_date": end_date,
                            "daily": variable,
                            "timezone": "auto",
                        },
                        timeout=15,
                    )
                    resp.raise_for_status()

                    data = resp.json()
                    daily_vals = data.get("daily", {}).get(variable, [])
                    valid = [v for v in daily_vals if v is not None]

                    values.append(float(np.mean(valid)) if valid else np.nan)

                except Exception as exc:
                    last_error = str(exc)
                    values.append(np.nan)

            valid_count = sum(1 for v in values if not np.isnan(v))

            if valid_count > 0:
                return values

        # Try same period last year as a real-data backup.
        previous_year_date = base_end_date.replace(year=base_end_date.year - 1)

        end_date = previous_year_date.strftime("%Y-%m-%d")
        start_date = (previous_year_date - timedelta(days=30)).strftime("%Y-%m-%d")

        values = []

        for lat, lon in points:
            try:
                resp = requests.get(
                    self.OPEN_METEO_ARCHIVE_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "start_date": start_date,
                        "end_date": end_date,
                        "daily": variable,
                        "timezone": "auto",
                    },
                    timeout=15,
                )
                resp.raise_for_status()

                data = resp.json()
                daily_vals = data.get("daily", {}).get(variable, [])
                valid = [v for v in daily_vals if v is not None]

                values.append(float(np.mean(valid)) if valid else np.nan)

            except Exception as exc:
                last_error = str(exc)
                values.append(np.nan)

        valid_count = sum(1 for v in values if not np.isnan(v))

        if valid_count > 0:
            return values

        raise RuntimeError(
            f"No real values returned from Open-Meteo for variable: {variable}. "
            f"Last error: {last_error}"
        )

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
        Tries real Earth Engine data first.
        Uses fallback only if all real-data attempts fail.
        """
        last_error = None

        if self._ensure_ee():
            for attempt in range(3):
                try:
                    raster = self._fetchLST_gee(aoi, time)

                    if self._is_valid_real_raster(raster):
                        raster.metadata = {
                            **(raster.metadata or {}),
                            "layer": "lst",
                            "source": "gee-modis",
                            "data_quality": "real",
                            "fetch_attempts": attempt + 1,
                        }
                        return raster

                    last_error = "LST raster returned empty or invalid values."

                except Exception as exc:
                    last_error = str(exc)

        fallback = self._fetchLST_synthetic(aoi)
        fallback.metadata = {
            **(fallback.metadata or {}),
            "layer": "lst",
            "source": "synthetic",
            "data_quality": "fallback",
            "fallback_reason": last_error or getattr(self, "_last_ee_error", "Earth Engine unavailable"),
        }
        return fallback

    def _fetchLST_gee(self, aoi: AOI, time: datetime) -> Raster:
        import ee

        points = self._build_grid_points(aoi)
        values = []

        end_date = time.strftime("%Y-%m-%d")
        start_date = (time - timedelta(days=30)).strftime("%Y-%m-%d")

        collection = (
            ee.ImageCollection("MODIS/061/MOD11A2")
            .filterDate(start_date, end_date)
            .select("LST_Day_1km")
        )

        count = collection.size().getInfo()
        if count == 0:
            raise RuntimeError("No MODIS LST images found for the selected date range.")

        image = collection.mean().multiply(0.02).subtract(273.15)

        for lat, lon in points:
            point = ee.Geometry.Point([lon, lat])

            value = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=1000,
                bestEffort=True,
            ).get("LST_Day_1km")

            result = value.getInfo()
            values.append(float(result) if result is not None else np.nan)

        grid = self._reshape_to_grid(values)

        return Raster(
            data=grid,
            nodata=-9999.0,
            metadata={
                "layer": "lst",
                "source": "gee-modis",
                "data_quality": "real",
                "unit": "°C",
            },
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
        Fetch terrain elevation.
        Tries real SRTM data from Earth Engine first.
        Uses fallback only if all real-data attempts fail.
        """
        last_error = None

        if self._ensure_ee():
            for attempt in range(3):
                try:
                    raster = self._fetchElevation_gee(aoi)

                    if self._is_valid_real_raster(raster):
                        raster.metadata = {
                            **(raster.metadata or {}),
                            "layer": "elevation",
                            "source": "srtm",
                            "data_quality": "real",
                            "fetch_attempts": attempt + 1,
                        }
                        return raster

                    last_error = "Elevation raster returned empty or invalid values."

                except Exception as exc:
                    last_error = str(exc)

        fallback = self._fetchElevation_synthetic(aoi)
        fallback.metadata = {
            **(fallback.metadata or {}),
            "layer": "elevation",
            "source": "synthetic",
            "data_quality": "fallback",
            "fallback_reason": last_error or getattr(self, "_last_ee_error", "Earth Engine unavailable"),
        }
        return fallback

    def _fetchElevation_gee(self, aoi: AOI) -> Raster:
        import ee

        points = self._build_grid_points(aoi)
        values = []

        srtm = ee.Image("USGS/SRTMGL1_003")

        for lat, lon in points:
            point = ee.Geometry.Point([lon, lat])

            value = srtm.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=30,
                bestEffort=True,
            ).get("elevation")

            result = value.getInfo()
            values.append(float(result) if result is not None else np.nan)

        grid = self._reshape_to_grid(values)

        return Raster(
            data=grid,
            nodata=-9999.0,
            metadata={
                "layer": "elevation",
                "source": "srtm",
                "data_quality": "real",
                "unit": "m",
            },
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