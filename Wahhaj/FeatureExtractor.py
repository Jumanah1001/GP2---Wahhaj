# wahhaj/FeatureExtractor.py
# ─────────────────────────────────────────────────────────────
# Data Extraction
# Responsibility: extract and normalize all feature layers
#                 needed by AHPModel for suitability scoring
#
# CONTRACT (must not change):
#   FeatureExtractor.layers          : Dict[str, Raster]
#   FeatureExtractor.extractFeatures : (dataset: Dataset) -> FeatureExtractor
#   FeatureExtractor.normalizeData   : () -> FeatureExtractor
#
# NOTE: Layer names must match exactly what AHPModel expects:
#       "ghi", "lst", "sunshine", "elevation", "slope"
#       If you rename any key here, AHPModel weights will break.
#
# NOTE: Dataset is defined here and exported from this file.
#       AnalysisRun (Person D) imports Dataset from FeatureExtractor.
#       Person A must add to __init__.py:
#           from .FeatureExtractor import FeatureExtractor, Dataset
#
# NOTE: normalizeData() must be called before passing layers to AHPModel.
#       AHPModel assumes all values are in range [0.0, 1.0].
#
# NOTE [FROM PROJECT DOCUMENT]: The system uses QGIS and GeoPandas to
#       calculate slope and elevation (Chapter 4, Software Requirements).
#       Current _make_slope_raster() is a MOCK for Phase 1 only.
#       In production, replace with GeoPandas/richdem computation from DSM/DTM.
#
# NOTE [FROM PROJECT DOCUMENT]: UAV images go through OpenCV preprocessing
#       (resizing, filtering, edge detection) before feature extraction.
#       This preprocessing should happen on dataset.images before
#       extractFeatures() is called — either in UploadService or here.
#       Coordinate with Person B (UploadService) on where OpenCV runs.
#
# NOTE [FROM PROJECT DOCUMENT]: The system targets Saudi Arabia climate
#       conditions. The fallback AOI (46.0, 24.0, 47.0, 25.0) covers
#       central Riyadh — appropriate default for development.
# ─────────────────────────────────────────────────────────────

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from Wahhaj.models import Raster, AOI
from Wahhaj.ExternalDataSourceAdapter import ExternalDataSourceAdapter
from datetime import datetime
import numpy as np


@dataclass
class Dataset:
    """
    The main data object that flows through the pipeline.

    Created by UploadService, read by FeatureExtractor and AnalysisRun.
    Do NOT add processing logic here — Dataset is data only.

    Attributes:
        name       : human-readable label for this analysis run
        aoi        : Area of Interest bounding box (lon_min, lat_min, lon_max, lat_max)
                     If None, defaults to Riyadh area for development
        images     : list of UAVImage objects uploaded by the user
        start_date : start of the time range for environmental data fetching
        end_date   : end of the time range for environmental data fetching
                     NOTE: project document specifies TimeRange as part of
                     Dataset — Person A should confirm the TimeRange type
                     in models.py and update these fields accordingly.
    """
    name: str
    aoi: Optional[AOI] = None
    images: List = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class FeatureExtractor:
    """
    Fetches all environmental layers needed for solar site suitability scoring.

    Layers produced: ghi, lst, sunshine, elevation, slope
    These match the 5 criteria used in AHPModel with weights:
        ghi=0.35, sunshine=0.25, slope=0.20, elevation=0.12, lst=0.08

    Usage (method chaining supported):
        extractor = FeatureExtractor()
        extractor.extractFeatures(dataset).normalizeData()
        layers = extractor.layers  # ready for AHPModel
    """

    def __init__(self):
        # NOTE: layers keys must match AHPModel.WEIGHTS keys exactly
        # AHPModel expects: "ghi", "sunshine", "slope", "elevation", "lst"
        self.layers: Dict[str, Raster] = {}
        self._adapter = ExternalDataSourceAdapter()
        # NOTE: _adapter is private — AnalysisRun must not call it directly

    # ── Public methods (the CONTRACT) ────────────────────────

    def extractFeatures(self, dataset: Dataset) -> "FeatureExtractor":
        """
        Fetch all feature layers for the given dataset.

        Calls ExternalDataSourceAdapter for remote data (GHI, LST, etc.)
        and computes slope locally from elevation.

        NOTE: UAV images in dataset.images should already be preprocessed
        with OpenCV before this method is called (see project document,
        Software Requirements: OpenCV for resizing, filtering, edge detection).

        Returns self to allow method chaining with normalizeData().
        """
        # Use dataset time range if provided, otherwise use current time
        # NOTE: project document specifies TimeRange — update when Person A
        # finalizes the TimeRange type in models.py
        t = dataset.start_date or datetime.now()

        # NOTE: fallback AOI covers central Riyadh — for development only
        # In production, dataset.aoi will always be set by UploadService
        aoi = dataset.aoi or (46.0, 24.0, 47.0, 25.0)

        # ── Fetch from external adapter ───────────────────────
        # NOTE: method names must match adapter CONTRACT exactly
        self.layers["ghi"]       = self._adapter.fetchGHI(aoi, t)
        self.layers["lst"]       = self._adapter.fetchLST(aoi, t)
        self.layers["sunshine"]  = self._adapter.fetchSunshineHours(aoi, t)
        self.layers["elevation"] = self._adapter.FetchElevation(aoi, t)

        # ── Compute locally ───────────────────────────────────
        # NOTE: slope is derived from DSM/DTM captured by the UAV drone.
        # Project document says QGIS and GeoPandas calculate slope/elevation.
        # MOCK for Phase 1 — replace with GeoPandas gradient computation
        # using dataset.images DSM data in production.
        self.layers["slope"] = self._make_slope_raster()

        return self  # enables: extractor.extractFeatures(d).normalizeData()

    def normalizeData(self) -> "FeatureExtractor":
        """
        Normalize all layer values to range [0.0, 1.0].

        IMPORTANT: Must be called before passing layers to AHPModel.
        AHPModel multiplies each layer by its weight and sums — if layers
        are in different scales the result will be wrong.

        Skips nodata cells (-9999.0) during min/max calculation.
        Returns self to allow method chaining.
        """
        for name, raster in self.layers.items():
            # Skip nodata cells — do not include -9999.0 in min/max
            valid_mask = raster.data != -9999.0

            if valid_mask.any():
                mn = raster.data[valid_mask].min()
                mx = raster.data[valid_mask].max()

                # Guard against division by zero (all values identical)
                if mx > mn:
                    raster.data[valid_mask] = (
                        (raster.data[valid_mask] - mn) / (mx - mn)
                    )

        return self

    # ── Private helpers ───────────────────────────────────────

    def _make_slope_raster(self) -> Raster:
        """
        MOCK slope raster for Phase 1 development.

        Production replacement (Phase 2):
            import geopandas as gpd
            # Load DSM from UAV imagery, compute slope using:
            # slope = np.degrees(np.arctan(np.gradient(elevation_array)))
            # Or use richdem: rd.TerrainAttribute(dem, attrib='slope_degrees')

        NOTE: Low slope values = flat terrain = better solar site suitability.
        AHPModel inverts slope in scoring: score = 1.0 - normalized_slope
        This means after normalizeData(), slope=0.0 → best, slope=1.0 → worst.
        """
        data = np.random.uniform(0.0, 0.3, (50, 50)).astype(np.float32)
        return Raster(
            data=data,
            nodata=-9999.0,
            metadata={"layer": "slope"}
        )
