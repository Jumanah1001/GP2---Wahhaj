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
#
# NOTE: normalizeData() must be called before passing layers to AHPModel.
#       AHPModel assumes all values are in range [0.0, 1.0].
# ─────────────────────────────────────────────────────────────

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np

from wahhaj.models import Raster, SiteInfo, FileRef
from wahhaj.SiteCandidate import SiteCandidate
from wahhaj.SuitabilityHeatmap import SuitabilityHeatmap


@dataclass
class Dataset:
    """
    Main pipeline data object.

    Attributes:
        name       : label for this analysis run
        aoi        : Area of Interest bounding box (lon_min, lat_min, lon_max, lat_max)
        images     : uploaded UAVImage objects
        start_date : start time for environmental data fetching
        end_date   : end time for environmental data fetching
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

    Output convention for Phase 1 / integration:
    - All layers are resampled to the same 5x5 grid.
    - This satisfies the project requirement that all layers must share
      the same shape/resolution before validation, normalization, and AHP.
    """

    TARGET_SHAPE: Tuple[int, int] = (5, 5)
    DEFAULT_AOI: AOI = (46.0, 24.0, 47.0, 25.0)  # central Riyadh for development

    def __init__(self):
        self.layers: Dict[str, Raster] = {}
        self._adapter = ExternalDataSourceAdapter()

    # ── Public methods (must keep these signatures) ──────────

    def extractFeatures(self, dataset: Dataset) -> "FeatureExtractor":
        """
        Fetch all feature layers for the given dataset and align them to a common 5x5 grid.

        Required output keys:
            "ghi", "lst", "sunshine", "elevation", "slope"

        Returns:
            self
        """
        t = dataset.start_date or datetime.now()
        aoi = self._validate_or_default_aoi(dataset.aoi)

        # Fetch raw rasters from adapter
        raw_ghi = self._adapter.fetchGHI(aoi, t)
        raw_lst = self._adapter.fetchLST(aoi, t)
        raw_sunshine = self._adapter.fetchSunshineHours(aoi, t)
        raw_elevation = self._adapter.FetchElevation(aoi, t)

        # Align everything to the shared project grid (5x5)
        self.layers["ghi"] = self._resample_to_target_grid(raw_ghi, "ghi")
        self.layers["lst"] = self._resample_to_target_grid(raw_lst, "lst")
        self.layers["sunshine"] = self._resample_to_target_grid(raw_sunshine, "sunshine")
        self.layers["elevation"] = self._resample_to_target_grid(raw_elevation, "elevation")

        # Compute slope from elevation if possible, otherwise fallback mock
        self.layers["slope"] = self._make_slope_raster(self.layers["elevation"])

        return self

    def normalizeData(self) -> "FeatureExtractor":
        """
        Normalize all layer values to [0.0, 1.0], ignoring nodata cells.
        """
        for name, raster in self.layers.items():
            valid_mask = raster.data != raster.nodata

            if not valid_mask.any():
                continue

            mn = raster.data[valid_mask].min()
            mx = raster.data[valid_mask].max()

            if mx > mn:
                raster.data[valid_mask] = (
                    (raster.data[valid_mask] - mn) / (mx - mn)
                ).astype(np.float32)
            else:
                # If all valid values are the same, set them to 0.0
                # so downstream AHP doesn't break on a constant layer.
                raster.data[valid_mask] = 0.0

            raster.metadata = {
                **(raster.metadata or {}),
                "normalized": True,
                "layer": name,
            }

        return self

    # ── Private helpers ───────────────────────────────────────

    def _validate_or_default_aoi(self, aoi: Optional[AOI]) -> AOI:
        """
        Validate AOI format: (lon_min, lat_min, lon_max, lat_max).
        If AOI is missing, use the development default.
        """
        if aoi is None:
            return self.DEFAULT_AOI

        if len(aoi) != 4:
            raise ValueError("AOI must be a 4-tuple: (lon_min, lat_min, lon_max, lat_max)")

        lon_min, lat_min, lon_max, lat_max = aoi

        if lon_min >= lon_max:
            raise ValueError("AOI invalid: lon_min must be smaller than lon_max")

        if lat_min >= lat_max:
            raise ValueError("AOI invalid: lat_min must be smaller than lat_max")

        return aoi

    def _resample_to_target_grid(self, raster: Raster, layer_name: str) -> Raster:
        """
        Convert any incoming raster to the project-standard 5x5 grid.

        This keeps all layers aligned before normalization/AHP.
        """
        target_rows, target_cols = self.TARGET_SHAPE
        src = raster.data.astype(np.float32)

        if src.ndim != 2:
            raise ValueError(f"Raster for layer '{layer_name}' must be 2D")

        if src.shape == self.TARGET_SHAPE:
            out = src.copy()
        else:
            out = self._downsample_mean(src, self.TARGET_SHAPE, nodata=raster.nodata)

        metadata = {
            **(raster.metadata or {}),
            "layer": layer_name,
            "shape": self.TARGET_SHAPE,
            "source_shape": tuple(src.shape),
            "aoi_aligned": True,
        }

        return Raster(
            data=out,
            nodata=raster.nodata,
            metadata=metadata,
        )

    def _downsample_mean(
        self,
        data: np.ndarray,
        target_shape: Tuple[int, int],
        nodata: float = -9999.0,
    ) -> np.ndarray:
        """
        Downsample raster to target shape using block mean.

        For Phase 1 integration, this gives a stable shared grid for AHP.
        It is simple and deterministic, which is good for testing and debugging.
        """
        target_rows, target_cols = target_shape
        src_rows, src_cols = data.shape

        row_edges = np.linspace(0, src_rows, target_rows + 1, dtype=int)
        col_edges = np.linspace(0, src_cols, target_cols + 1, dtype=int)

        result = np.full((target_rows, target_cols), nodata, dtype=np.float32)

        for r in range(target_rows):
            r0, r1 = row_edges[r], row_edges[r + 1]
            for c in range(target_cols):
                c0, c1 = col_edges[c], col_edges[c + 1]

                block = data[r0:r1, c0:c1]
                if block.size == 0:
                    continue

                valid = block[block != nodata]
                if valid.size == 0:
                    continue

                result[r, c] = float(valid.mean())

        return result

    def _make_slope_raster(self, elevation_raster: Optional[Raster] = None) -> Raster:
        """
        Build slope raster from elevation when available.

        Phase 1:
        - If elevation exists, estimate slope from gradient.
        - Otherwise fallback to a mock raster for development.

        Note:
        - Lower slope is better for solar suitability.
        - AHPModel may invert slope later during scoring.
        """
        if elevation_raster is None:
            data = np.random.uniform(0.0, 0.3, self.TARGET_SHAPE).astype(np.float32)
            return Raster(
                data=data,
                nodata=-9999.0,
                metadata={"layer": "slope", "mock": True}
            )

        elevation = elevation_raster.data.astype(np.float32)
        nodata = elevation_raster.nodata

        valid_mask = elevation != nodata
        if not valid_mask.any():
            data = np.random.uniform(0.0, 0.3, self.TARGET_SHAPE).astype(np.float32)
            return Raster(
                data=data,
                nodata=nodata,
                metadata={"layer": "slope", "mock": True, "reason": "empty_elevation"}
            )

        # Fill nodata temporarily using mean of valid cells to avoid gradient issues
        filled = elevation.copy()
        valid_mean = float(elevation[valid_mask].mean())
        filled[~valid_mask] = valid_mean

        grad_y, grad_x = np.gradient(filled)
        slope = np.sqrt((grad_x ** 2) + (grad_y ** 2)).astype(np.float32)

        # Restore nodata mask
        slope[~valid_mask] = nodata

        return Raster(
            data=slope,
            nodata=nodata,
            metadata={
                "layer": "slope",
                "derived_from": "elevation",
                "shape": tuple(slope.shape),
            }
        )
