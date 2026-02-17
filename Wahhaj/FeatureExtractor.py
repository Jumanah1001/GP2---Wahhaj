from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

# Reuse shared domain types from the adapter module
from external_data_source_adapter import (
    AOI,
    BoundingBox,
    ExternalDataSourceAdapter,
    Raster,
    TimeRange,
)

logger = logging.getLogger(__name__)

NODATA: float = -9999.0


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------

@dataclass
class UAVImage:
    """
    Lightweight representation of a single UAV acquisition frame.

    Attributes
    ----------
    imageId : UUID string
    filePath : path to the raw image file on disk (or object-store key)
    resolution : ground sampling distance in metres per pixel
    timestamp : acquisition time (UTC)
    """
    imageId: str = field(default_factory=lambda: str(uuid.uuid4()))
    filePath: str = ""
    resolution: float = 0.05          # 5 cm GSD – typical UAV
    timestamp: datetime = field(default_factory=datetime.utcnow)
    _data: Optional[np.ndarray] = field(default=None, repr=False)  # lazily loaded

    def load(self) -> np.ndarray:
        """
        Load the raw pixel array from ``filePath``.

        Returns a synthetic (H, W, 3) uint8 RGB array when the file is not
        present so the rest of the pipeline can run without real data.
        Replace the body with ``rasterio.open(self.filePath).read()`` in
        production.
        """
        if self._data is not None:
            return self._data
        logger.debug("UAVImage.load() – synthetic data for %s", self.filePath or "<no path>")
        rng = np.random.default_rng(seed=int(uuid.UUID(self.imageId).int % (2**32)))
        # Simulate an RGB ortho-photo at a modest 200×200 resolution
        self._data = rng.integers(0, 256, size=(200, 200, 3), dtype=np.uint8)
        return self._data


@dataclass
class Dataset:
    """
    Collection of UAV images covering a survey area, plus spatial extent.

    Attributes
    ----------
    datasetId : UUID string
    name      : human-readable label
    aoi       : spatial extent + resolution + CRS
    time      : temporal window of the survey
    images    : ordered list of UAV frames in the dataset
    """
    datasetId: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "unnamed_dataset"
    aoi: AOI = field(default_factory=lambda: AOI(
        bbox=BoundingBox(-8.5, 30.0, -5.0, 33.5), resolution_m=100.0
    ))
    time: TimeRange = field(default_factory=lambda: TimeRange(
        start=datetime(2023, 1, 1), end=datetime(2023, 12, 31)
    ))
    images: List[UAVImage] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.images:
            # Populate with a single synthetic image by default
            self.images = [UAVImage()]


# ---------------------------------------------------------------------------
# FeatureExtractor
# ---------------------------------------------------------------------------

class FeatureExtractor:
    """
    Derives and normalises analysis-ready feature layers from a UAV dataset.

    UML attributes
    --------------
    slope : Raster
        Terrain slope derived from the elevation DEM [degrees 0-90].
        Populated by :meth:`extractFeatures`.

    UML methods
    -----------
    extractFeatures(dataset: Dataset)
        Fetches external layers (GHI, LST, SunshineHours, Elevation),
        derives slope + aspect from the DEM, and computes spectral indices
        from the UAV imagery.  All outputs land in :attr:`layers`.

    normalizeData()
        Applies per-layer min-max normalisation [0, 1] over valid pixels,
        preserving the nodata mask.  Modifies :attr:`layers` in-place.

    Parameters
    ----------
    adapter : ExternalDataSourceAdapter, optional
        Allows dependency injection for testing.  A default adapter is
        constructed if none is supplied.
    """

    #: Canonical sentinel for missing / masked pixels
    NODATA: float = NODATA

    def __init__(self, adapter: Optional[ExternalDataSourceAdapter] = None) -> None:
        self._adapter: ExternalDataSourceAdapter = adapter or ExternalDataSourceAdapter()

        # UML attribute ──────────────────────────────────────────────────────
        self.slope: Optional[Raster] = None

        # All derived layers keyed by name
        self.layers: Dict[str, Raster] = {}

        # Track which dataset was last processed
        self._dataset: Optional[Dataset] = None

        logger.info("FeatureExtractor ready | adapter=%s", type(self._adapter).__name__)

    # -----------------------------------------------------------------------
    # Public interface  (UML methods)
    # -----------------------------------------------------------------------

    def extractFeatures(self, dataset: Dataset) -> "FeatureExtractor":
        """
        Extract all feature layers from *dataset*.

        Steps
        -----
        1. Fetch GHI, LST, SunshineHours, Elevation from external providers.
        2. Derive slope and aspect rasters from the elevation layer.
        3. Compute per-image spectral indices (NDVI proxy, brightness) and
           mosaic them onto the AOI grid.
        4. Populate :attr:`layers` and :attr:`slope`.

        Parameters
        ----------
        dataset : Dataset
            A :class:`Dataset` containing spatial extent, temporal window,
            and UAV image references.

        Returns
        -------
        FeatureExtractor
            *self* – enables fluent chaining with :meth:`normalizeData`.

        Raises
        ------
        ValueError
            If ``dataset`` contains no images or has an invalid AOI.
        RuntimeError
            If any external data fetch fails after retries.
        """
        if not dataset.images:
            raise ValueError(f"Dataset '{dataset.name}' contains no UAV images.")

        self._dataset = dataset
        aoi, time = dataset.aoi, dataset.time

        logger.info(
            "extractFeatures | dataset=%s | images=%d | aoi=%s",
            dataset.name, len(dataset.images), aoi.bbox.to_tuple(),
        )

        # ── Step 1: Fetch external raster layers ────────────────────────────
        logger.info("  Fetching GHI …")
        ghi = self._adapter.fetchGHI(aoi, time)

        logger.info("  Fetching LST …")
        lst = self._adapter.fetchLST(aoi, time)

        logger.info("  Fetching SunshineHours …")
    
        sunshine = self._adapter.fetchSunshineHours(aoi, time)

        logger.info("  Fetching Elevation …")
        elevation = self._adapter.FetchElevation(aoi, time)

        # ── Step 2: Derive slope and aspect from DEM ─────────────────────────
        logger.info("  Deriving slope and aspect from DEM …")
        slope_raster, aspect_raster = self._derive_slope_aspect(elevation)

        # Expose slope as the UML-named attribute
        self.slope = slope_raster

        # ── Step 3: Spectral features from UAV imagery ───────────────────────
        logger.info("  Extracting spectral features from %d UAV image(s) …", len(dataset.images))
        ndvi_raster, brightness_raster = self._extract_spectral_features(dataset, elevation)

        # ── Step 4: Populate layers dict ─────────────────────────────────────
        self.layers = {
            "ghi":          ghi,
            "lst":          lst,
            "sunshine":     sunshine,
            "elevation":    elevation,
            "slope":        slope_raster,
            "aspect":       aspect_raster,
            "ndvi":         ndvi_raster,
            "brightness":   brightness_raster,
        }

        logger.info("extractFeatures complete | layers=%s", list(self.layers.keys()))
        return self

    def normalizeData(self) -> "FeatureExtractor":
        """
        Apply min-max normalisation [0, 1] to every layer in :attr:`layers`.

        The nodata mask is preserved: nodata pixels remain ``NODATA`` after
        normalisation and are excluded from the min/max computation.

        Returns
        -------
        FeatureExtractor
            *self* – enables fluent chaining.

        Raises
        ------
        RuntimeError
            If called before :meth:`extractFeatures` has populated any layers.
        """
        if not self.layers:
            raise RuntimeError(
                "normalizeData() called before extractFeatures().  "
                "Call extractFeatures(dataset) first."
            )

        logger.info("normalizeData | normalising %d layers …", len(self.layers))

        for name, raster in self.layers.items():
            normalised = self._minmax_normalise(raster)
            self.layers[name] = normalised
            # Keep the slope attribute in sync
            if name == "slope":
                self.slope = normalised
            logger.debug(
                "  %-12s  min=%.4f  max=%.4f  → normalised",
                name,
                float(np.nanmin(normalised.data[normalised.data != self.NODATA])) if np.any(normalised.data != self.NODATA) else float("nan"),
                float(np.nanmax(normalised.data[normalised.data != self.NODATA])) if np.any(normalised.data != self.NODATA) else float("nan"),
            )

        logger.info("normalizeData complete.")
        return self

    # -----------------------------------------------------------------------
    # Layer access helpers
    # -----------------------------------------------------------------------

    def get_layer(self, name: str) -> Raster:
        """Return a named layer, raising KeyError with a helpful message."""
        if name not in self.layers:
            available = list(self.layers.keys())
            raise KeyError(
                f"Layer '{name}' not found.  Available layers: {available}"
            )
        return self.layers[name]

    def layer_names(self) -> List[str]:
        """Return the names of all currently extracted layers."""
        return list(self.layers.keys())

    def summary(self) -> Dict[str, dict]:
        """
        Return a dictionary of per-layer statistics.

        Useful for quick inspection without loading data elsewhere.
        """
        return {name: raster.statistics() for name, raster in self.layers.items()}

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _derive_slope_aspect(
        self, elevation: Raster
    ) -> Tuple[Raster, Raster]:
        """
        Compute slope [degrees] and aspect [degrees, 0=N, CW] from a DEM.

        Uses finite-difference gradients.  Pixel spacing is approximated from
        the raster transform (x_res, y_res in degrees → metres).

        Parameters
        ----------
        elevation : Raster
            Elevation grid [m].

        Returns
        -------
        Tuple[Raster, Raster]
            (slope_raster, aspect_raster)
        """
        data = elevation.data.copy().astype(np.float64)
        nodata_mask = data == self.NODATA

        # Replace nodata with NaN for gradient computation
        data[nodata_mask] = np.nan

        # Pixel size in metres (approximate, from transform degrees → m)
        _, x_res_deg, _, y_res_deg = elevation.transform
        lat_centre = 0.0  # fallback; ideally extract from transform
        metres_per_deg_lon = 111_320 * np.cos(np.radians(lat_centre))
        metres_per_deg_lat = 111_320
        dx = abs(x_res_deg) * metres_per_deg_lon
        dy = abs(y_res_deg) * metres_per_deg_lat

        # Finite-difference gradient (central differences via np.gradient)
        gy, gx = np.gradient(data, dy, dx)

        # Slope: arctan of the gradient magnitude → degrees
        slope_rad = np.arctan(np.sqrt(gx**2 + gy**2))
        slope_deg = np.degrees(slope_rad).astype(np.float32)

        # Aspect: 0° = North, clockwise → convert from math convention
        aspect_rad = np.arctan2(-gy, gx)
        aspect_deg = (90.0 - np.degrees(aspect_rad)) % 360.0
        aspect_deg = aspect_deg.astype(np.float32)

        # Restore nodata sentinel
        slope_deg[nodata_mask]  = self.NODATA
        aspect_deg[nodata_mask] = self.NODATA

        slope_raster = Raster(
            data=slope_deg,
            nodata=self.NODATA,
            crs=elevation.crs,
            transform=elevation.transform,
            metadata={"source": "Derived from DEM", "units": "degrees", "layer": "slope"},
        )
        aspect_raster = Raster(
            data=aspect_deg,
            nodata=self.NODATA,
            crs=elevation.crs,
            transform=elevation.transform,
            metadata={"source": "Derived from DEM", "units": "degrees_CW_from_N", "layer": "aspect"},
        )
        return slope_raster, aspect_raster

    def _extract_spectral_features(
        self, dataset: Dataset, reference_raster: Raster
    ) -> Tuple[Raster, Raster]:
        """
        Compute per-image spectral indices and mosaic onto the AOI grid.

        In production this would ortho-rectify each UAV frame, reproject to
        the AOI CRS/resolution, and composite overlapping pixels.  Here we
        use a synthetic RGB proxy so the pipeline runs without real imagery.

        Returns
        -------
        Tuple[Raster, Raster]
            (ndvi_raster, brightness_raster)
        """
        rows, cols = reference_raster.shape[:2]
        ndvi_accum   = np.zeros((rows, cols), dtype=np.float64)
        bright_accum = np.zeros((rows, cols), dtype=np.float64)
        count        = np.zeros((rows, cols), dtype=np.int32)

        for img in dataset.images:
            raw = img.load()        # (H, W, 3) uint8 RGB
            # Resample to the AOI grid via nearest-neighbour
            resampled = self._resample(raw, rows, cols)

            r = resampled[:, :, 0].astype(np.float64) / 255.0
            g = resampled[:, :, 1].astype(np.float64) / 255.0
            b = resampled[:, :, 2].astype(np.float64) / 255.0

            # NDVI proxy: (NIR – Red) / (NIR + Red).
            # UAV RGB cameras don't have a NIR band; we approximate NIR with
            # the green channel (modified green NDVI) for demonstration.
            # Replace with real NIR when a multi-spectral camera is used.
            nir_proxy = g
            denom = nir_proxy + r
            ndvi = np.where(denom > 0, (nir_proxy - r) / denom, 0.0)

            brightness = (r + g + b) / 3.0

            ndvi_accum   += ndvi
            bright_accum += brightness
            count        += 1

        safe_count = np.where(count > 0, count, 1)
        ndvi_mean   = (ndvi_accum   / safe_count).astype(np.float32)
        bright_mean = (bright_accum / safe_count).astype(np.float32)

        # Pixels with no image coverage become nodata
        no_cov = count == 0
        ndvi_mean[no_cov]   = self.NODATA
        bright_mean[no_cov] = self.NODATA

        ndvi_raster = Raster(
            data=ndvi_mean,
            nodata=self.NODATA,
            crs=reference_raster.crs,
            transform=reference_raster.transform,
            metadata={"source": "UAV imagery", "units": "index [-1,1]", "layer": "ndvi"},
        )
        brightness_raster = Raster(
            data=bright_mean,
            nodata=self.NODATA,
            crs=reference_raster.crs,
            transform=reference_raster.transform,
            metadata={"source": "UAV imagery", "units": "index [0,1]", "layer": "brightness"},
        )
        return ndvi_raster, brightness_raster

    @staticmethod
    def _resample(array: np.ndarray, out_rows: int, out_cols: int) -> np.ndarray:
        """
        Nearest-neighbour resampling to (out_rows, out_cols) spatial size.

        Works for both 2-D (H, W) and 3-D (H, W, C) arrays.
        """
        in_rows, in_cols = array.shape[:2]
        row_idx = (np.arange(out_rows) * in_rows / out_rows).astype(int)
        col_idx = (np.arange(out_cols) * in_cols / out_cols).astype(int)
        row_idx = np.clip(row_idx, 0, in_rows - 1)
        col_idx = np.clip(col_idx, 0, in_cols - 1)
        return array[np.ix_(row_idx, col_idx)] if array.ndim == 2 else array[row_idx][:, col_idx]

    @staticmethod
    def _minmax_normalise(raster: Raster) -> Raster:
        """
        Return a new Raster whose valid pixels are scaled to [0, 1].

        The nodata sentinel is preserved unchanged.
        """
        data  = raster.data.copy()
        valid = data != raster.nodata

        if not np.any(valid):
            # All pixels are nodata – return unchanged
            return raster

        vmin = float(data[valid].min())
        vmax = float(data[valid].max())
        span = vmax - vmin

        if span == 0:
            # Constant layer – set all valid pixels to 0.5
            data[valid] = 0.5
        else:
            data[valid] = (data[valid] - vmin) / span

        return Raster(
            data=data.astype(np.float32),
            nodata=raster.nodata,
            crs=raster.crs,
            transform=raster.transform,
            metadata={**raster.metadata, "normalised": True, "original_min": vmin, "original_max": vmax},
        )
