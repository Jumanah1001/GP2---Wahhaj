# wahhaj/ExternalDataSourceAdapter.py
# ─────────────────────────────────────────────────────────────
# Person C — Layer: Data Extraction
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
# NOTE: This is currently a synthetic/mock implementation.
#       When real API keys are available, replace _make_synthetic_raster()
#       only — method signatures must stay the same.
# ─────────────────────────────────────────────────────────────

from models import Raster, AOI
from datetime import datetime
from typing import Optional
import numpy as np


class ExternalDataSourceAdapter:
    """
    Adapter between FeatureExtractor and external data sources
    (NASA POWER, SRTM elevation, LST APIs, etc.)

    Currently returns synthetic rasters for development/testing.
    Replace _make_synthetic_raster() with real API calls in Phase 2.
    """

    def __init__(self, api_key: Optional[str] = None):
        # NOTE: api_key is optional — adapter works without it in mock mode
        self.api_key = api_key

    # ── Public methods (the CONTRACT) ────────────────────────

    def fetchGHI(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch Global Horizontal Irradiance raster.
        GHI = solar energy received per unit area (W/m²).
        Higher GHI = better solar site candidate.
        """
        return self._make_synthetic_raster(aoi, layer="ghi")

    def fetchLST(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch Land Surface Temperature raster.
        High LST reduces solar panel efficiency → lower suitability score.
        AHPModel treats LST as inverted criterion (lower = better).
        """
        return self._make_synthetic_raster(aoi, layer="lst")

    def fetchSunshineHours(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch average sunshine hours per day raster.
        More sunshine hours = more generation potential.
        """
        return self._make_synthetic_raster(aoi, layer="sunshine")

    def FetchElevation(self, aoi: AOI, time: datetime) -> Raster:
        """
        Fetch elevation raster (meters above sea level).
        NOTE: Capital F — matches exactly what FeatureExtractor calls.
        Elevation affects slope calculation downstream.
        """
        return self._make_synthetic_raster(aoi, layer="elevation")

    # ── Private helpers ───────────────────────────────────────

    def _make_synthetic_raster(self, aoi, layer: str) -> Raster:
        """
        Returns a mock 50×50 float32 raster for development.

        IMPORTANT — Raster spec (from Contract 2 in integration plan):
          - dtype  : float32  (AHPModel expects float32, not float64)
          - nodata : -9999.0  (normalizeData() skips these cells)
          - shape  : (rows, cols) — 50×50 sufficient for testing

        When connecting real APIs, keep this spec exactly.
        """
        data = np.random.uniform(0.3, 1.0, (50, 50)).astype(np.float32)
        return Raster(
            data=data,
            nodata=-9999.0,
            metadata={"layer": layer}
        )
