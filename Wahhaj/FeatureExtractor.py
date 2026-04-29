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
#
# Person 3 additions (Data Validation + Normalization):
#   validate_shapes()       — ensures all layers share TARGET_SHAPE
#   handle_missing_values() — fills nodata/-9999/NaN cells with layer mean
#   normalizeData()         — now calls both helpers before min-max scaling
# ─────────────────────────────────────────────────────────────

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .models import Raster, AOI, BoundingBox
from .ExternalDataSourceAdapter import ExternalDataSourceAdapter
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


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

    TARGET_SHAPE: Tuple[int, int] = (10, 10)
    DEFAULT_AOI: AOI = (46.0, 24.0, 47.0, 25.0)  # central Riyadh for development

    def __init__(self, adapter: ExternalDataSourceAdapter):
        self.layers: Dict[str, Raster] = {}
        self.adapter = adapter
        self.slope = None

    # ── Public methods (must keep these signatures) ──────────

    def calculateSlope(self, elevation_grid: np.ndarray, aoi: AOI) -> np.ndarray:
        lon_min, lat_min, lon_max, lat_max = aoi

        lat_spacing_deg = (lat_max - lat_min) / max(self.TARGET_SHAPE[0] - 1, 1)
        lon_spacing_deg = (lon_max - lon_min) / max(self.TARGET_SHAPE[1] - 1, 1)

        mean_lat = (lat_min + lat_max) / 2.0
        meters_per_deg_lat = 111320.0
        meters_per_deg_lon = 111320.0 * np.cos(np.radians(mean_lat))

        dy = lat_spacing_deg * meters_per_deg_lat
        dx = lon_spacing_deg * meters_per_deg_lon

        dz_dy, dz_dx = np.gradient(elevation_grid, dy, dx)
        slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
        slope_deg = np.degrees(slope_rad)

        return slope_deg.astype(np.float32)

    def _make_slope_raster(
        self,
        elevation_raster: Optional[Raster] = None,
        aoi: Optional[AOI] = None
    ) -> Raster:
        """
        Build slope raster from elevation using the same logic as calculateSlope().
        """
        if elevation_raster is None:
            raise ValueError("elevation_raster is required to compute slope")

        if aoi is None:
            raise ValueError("aoi is required to compute slope")

        elevation = elevation_raster.data.astype(np.float32)
        nodata = elevation_raster.nodata

        valid_mask = elevation != nodata
        if not valid_mask.any():
            raise ValueError("Cannot compute slope: elevation raster has no valid cells")

        filled = elevation.copy()
        valid_mean = float(elevation[valid_mask].mean())
        filled[~valid_mask] = valid_mean

        slope = self.calculateSlope(filled, aoi).astype(np.float32)
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

    def resizeArray(self, arr: np.ndarray, target_rows: int, target_cols: int) -> np.ndarray:
        src_rows, src_cols = arr.shape
        row_idx = np.linspace(0, src_rows - 1, target_rows).astype(int)
        col_idx = np.linspace(0, src_cols - 1, target_cols).astype(int)
        return arr[np.ix_(row_idx, col_idx)]

    def extractFeatures(self, dataset: Dataset) -> "FeatureExtractor":
        t = dataset.start_date or datetime.now()
        aoi = self._validate_or_default_aoi(dataset.aoi)

        raw_ghi       = self.adapter.fetchGHI(aoi, t)
        raw_lst       = self.adapter.fetchLST(aoi, t)
        raw_sunshine  = self.adapter.fetchSunshineHours(aoi, t)
        raw_elevation = self.adapter.FetchElevation(aoi, t)

        self.layers["ghi"]       = self._resample_to_target_grid(raw_ghi, "ghi")
        self.layers["lst"]       = self._resample_to_target_grid(raw_lst, "lst")
        self.layers["sunshine"]  = self._resample_to_target_grid(raw_sunshine, "sunshine")
        self.layers["elevation"] = self._resample_to_target_grid(raw_elevation, "elevation")
        self.layers["slope"]     = self._make_slope_raster(self.layers["elevation"], aoi)

        # NOTE: normalizeData() is NOT called here.
        # AnalysisRun.execute() calls it after extractFeatures() returns.
        # Calling it here AND there would double-normalize the data.

        self.layers['obstacle'] = self._get_obstacle_layer(dataset)
        return self

    def validate_shapes(self) -> None:
        """
        Ensure every layer in self.layers is 2D and matches TARGET_SHAPE.

        Raises
        ------
        ValueError
            If any layer has the wrong number of dimensions or a shape
            that does not match TARGET_SHAPE (5, 5).

        Called automatically by normalizeData() before scaling.
        """
        if not self.layers:
            return  # nothing loaded yet — not an error

        expected_shape = self.TARGET_SHAPE
        mismatches = []

        for name, raster in self.layers.items():
            if raster.data.ndim != 2:
                mismatches.append(
                    f"  '{name}': not 2D (ndim={raster.data.ndim})"
                )
            elif raster.data.shape != expected_shape:
                mismatches.append(
                    f"  '{name}': shape={raster.data.shape}, "
                    f"expected={expected_shape}"
                )

        if mismatches:
            raise ValueError(
                "validate_shapes() failed — layer shape mismatch:\n"
                + "\n".join(mismatches)
            )

        logger.debug(
            "validate_shapes: all %d layers have shape %s ✓",
            len(self.layers), expected_shape,
        )

    def handle_missing_values(self) -> None:
        """
        Fill missing / nodata cells in every layer with that layer's valid mean.

        A cell is considered missing if it equals raster.nodata (-9999.0)
        OR if it is a NaN (which can arrive from API responses).

        Strategy
        --------
        - Compute the mean of all valid (non-nodata, non-NaN) cells.
        - Replace every missing cell with that mean.
        - If a layer has NO valid cells at all, fill with 0.0 and log a
          warning so the team knows the layer is unusable.

        Called automatically by normalizeData() before min-max scaling.
        """
        for name, raster in self.layers.items():
            data = raster.data.astype(np.float32)

            nodata_mask  = (data == raster.nodata)
            nan_mask     = np.isnan(data)
            missing_mask = nodata_mask | nan_mask

            if not missing_mask.any():
                # Layer is already clean — nothing to do
                continue

            n_missing = int(missing_mask.sum())
            valid_mask = ~missing_mask

            if valid_mask.any():
                fill_value = float(data[valid_mask].mean())
                logger.debug(
                    "handle_missing_values: layer '%s' — filling %d missing "
                    "cell(s) with valid mean %.4f",
                    name, n_missing, fill_value,
                )
            else:
                # Entire layer is nodata — safe fallback is 0.0
                fill_value = 0.0
                logger.warning(
                    "handle_missing_values: layer '%s' has NO valid cells. "
                    "Filling all cells with 0.0. This layer will not "
                    "contribute meaningful scores to AHP.",
                    name,
                )

            data[missing_mask] = fill_value
            raster.data = data

    def normalizeData(self) -> "FeatureExtractor":
        """
        Validate shapes, fill missing values, then normalize all layers
        to the range [0.0, 1.0].

        Steps
        -----
        1. validate_shapes()       — all layers must be (5, 5).
        2. handle_missing_values() — replace nodata / NaN with layer mean.
        3. Min-max normalization   — scale valid cells to [0.0, 1.0].
           • If all valid values are identical, they are set to 0.0
             so AHP does not break on a constant layer.

        Returns
        -------
        FeatureExtractor — self, for method chaining.
        """
        # ── Step 1: shape validation ──────────────────────────
        self.validate_shapes()

        # ── Step 2: fill missing values ───────────────────────
        self.handle_missing_values()

        # ── Step 3: per-layer min-max normalization ───────────
        for name, raster in self.layers.items():
                        # IMPORTANT:
            # The obstacle layer already represents AI-detected exclusion density:
            # 0.0 = clean / bare / acceptable
            # 1.0 = fully blocked by building, vegetation, or water
            # Do NOT min-max normalize it, because that would destroy the real threshold logic.
            if name == "obstacle":
                valid_mask = raster.data != raster.nodata

                if valid_mask.any():
                    raster.data[valid_mask] = np.clip(
                        raster.data[valid_mask].astype(np.float32),
                        0.0,
                        1.0,
                    )

                raster.metadata = {
                    **(raster.metadata or {}),
                    "normalized": True,
                    "layer": name,
                    "norm_min": 0.0,
                    "norm_max": 1.0,
                    "ai_exclusion_gate": True,
                }

                logger.debug("normalizeData: obstacle layer kept as AI exclusion density [0, 1]")
                continue

            # After handle_missing_values, nodata cells have been filled,
            # so valid_mask now covers the whole array.
            # We keep the nodata check here as a safety net.
            valid_mask = raster.data != raster.nodata

            if not valid_mask.any():
                # Completely empty layer — skip (already warned above)
                continue

            mn = float(raster.data[valid_mask].min())
            mx = float(raster.data[valid_mask].max())

            if mx > mn:
                raster.data[valid_mask] = (
                    (raster.data[valid_mask] - mn) / (mx - mn)
                ).astype(np.float32)
            else:
                # All valid values are the same — set to 0.0
                # so AHP weighted sum stays defined.
                raster.data[valid_mask] = 0.0

            raster.metadata = {
                **(raster.metadata or {}),
                "normalized": True,
                "layer": name,
                "norm_min": mn,
                "norm_max": mx,
            }

            logger.debug(
                "normalizeData: layer '%s' normalized [%.4f, %.4f] → [0, 1]",
                name, mn, mx,
            )

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
    
    def _classify_satellite_with_tiles(
        self,
        ai_model,
        image_path: str,
        tile_grid: int = 3,
        overlap: float = 0.20,
    ) -> Raster:
        """
        Classify a satellite image using tiled inference.
        Why:
        Satellite screenshots can make buildings, trees, and water appear small.
        Running YOLO on smaller overlapping tiles acts like a visual zoom,
        increasing the chance of detecting small obstacles.
        Output:
        A full-size class raster with the same meaning as AIModel.classifyArea:
            -1 = background / no detection
            0 = building
            1 = vegetation
            2 = water
            3 = bare_land
        """
        import os
        import tempfile
        import numpy as np
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        # Full class map initialized as no detection.
        full_classes = np.full((height, width), -1, dtype=np.int32)
        tile_w = int(width / tile_grid)
        tile_h = int(height / tile_grid)
        step_x = max(1, int(tile_w * (1.0 - overlap)))
        step_y = max(1, int(tile_h * (1.0 - overlap)))
        y_positions = list(range(0, max(height - tile_h + 1, 1), step_y))
        x_positions = list(range(0, max(width - tile_w + 1, 1), step_x))
        # Ensure last row/column are covered.
        if y_positions[-1] != height - tile_h:
            y_positions.append(max(height - tile_h, 0))
        if x_positions[-1] != width - tile_w:
            x_positions.append(max(width - tile_w, 0))
        # Priority rule:
        # excluded classes are more important than bare land.
        # building/water/vegetation should not be overwritten by bare_land.
        excluded_classes = {0, 1, 2}
        with tempfile.TemporaryDirectory() as tmpdir:
            for y0 in y_positions:
                for x0 in x_positions:
                    x1 = min(x0 + tile_w, width)
                    y1 = min(y0 + tile_h, height)
                    tile = image.crop((x0, y0, x1, y1))
                    tile_path = os.path.join(tmpdir, f"tile_{y0}_{x0}.png")
                    tile.save(tile_path)
                    tile_raster = ai_model.classifyArea(tile_path)
                    tile_classes = tile_raster.data.astype(np.int32)
                    # Resize class raster back to tile size if needed.
                    if tile_classes.shape != (y1 - y0, x1 - x0):
                        tile_img = Image.fromarray(tile_classes.astype(np.int16))
                        tile_img = tile_img.resize((x1 - x0, y1 - y0), resample=Image.NEAREST)
                        tile_classes = np.array(tile_img).astype(np.int32)
                    current = full_classes[y0:y1, x0:x1]
                    # Where tile detects excluded classes, always keep them.
                    tile_excluded = np.isin(tile_classes, list(excluded_classes))
                    # Where current is empty and tile has any valid class, fill it.
                    current_empty = current == -1
                    tile_valid = tile_classes != -1
                    update_mask = tile_excluded | (current_empty & tile_valid)
                    current[update_mask] = tile_classes[update_mask]
                    full_classes[y0:y1, x0:x1] = current
        return Raster(
            data=full_classes.astype(np.float32),
            nodata=-1.0,
            metadata={
                "layer": "ai_classes",
                "source": "AIModel_tiled",
                "tile_grid": tile_grid,
                "overlap": overlap,
                "meaning": "Tiled satellite classification result before obstacle-density conversion.",
            },
        )
   
    def _estimate_tile_grid_from_aoi(self, aoi, target_tile_m: float = 307.0) -> int:
        """
        Estimate tile_grid dynamically based on AOI ground size.

        The model was trained approximately on 307m × 307m scenes,
        so each tile should approximate that ground coverage.
        """
        import math
        import numpy as np

        if aoi is None or len(aoi) != 4:
            return 3

        lon_min, lat_min, lon_max, lat_max = aoi

        mean_lat = (lat_min + lat_max) / 2.0

        meters_per_deg_lat = 111320.0
        meters_per_deg_lon = 111320.0 * np.cos(np.radians(mean_lat))

        width_m = abs(lon_max - lon_min) * meters_per_deg_lon
        height_m = abs(lat_max - lat_min) * meters_per_deg_lat

        max_side_m = max(width_m, height_m)

        tile_grid = math.ceil(max_side_m / target_tile_m)

        # Keep it practical for Streamlit and YOLO inference
        tile_grid = max(1, min(tile_grid, 4))

        print("AOI WIDTH M =", width_m)
        print("AOI HEIGHT M =", height_m)
        print("AUTO TILE GRID =", tile_grid)

        return tile_grid    


    def _get_obstacle_layer(self, dataset) -> Raster:
        """
        Runs the AI model first and creates an exclusion-density layer.
        Meaning of the returned obstacle raster:
            0.0 = no excluded class detected in this cell
            1.0 = fully covered by excluded classes
        Excluded classes:
            0 = building
            1 = vegetation
            2 = water
        Bare land / background is treated as acceptable unless the model
        explicitly detects one of the excluded classes.
        """
        import numpy as np
        import os
        rows, cols = self.TARGET_SHAPE
        print("TARGET_SHAPE USED =", self.TARGET_SHAPE)
        _candidate_paths = [
            "weights/best.pt",
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "weights",
                    "best.pt"
                )
            ),
        ]
        MODEL_PATH = next((p for p in _candidate_paths if os.path.exists(p)), None)
        print("MODEL_PATH =", MODEL_PATH)
        print("MODEL_EXISTS =", os.path.exists(MODEL_PATH) if MODEL_PATH else False)
        print("IMAGES =", [getattr(img, "filePath", None) for img in dataset.images])
        if not dataset.images or MODEL_PATH is None:
            reason = "no images" if not dataset.images else "model weights not found"
            logger.warning("_get_obstacle_layer: using synthetic layer (%s)", reason)
            # Important:
            # If AI is missing, do not pretend the site is AI-validated.
            # Use high obstacle values so the AHP result cannot become green.
            data = np.full((rows, cols), 1.0, dtype=np.float32)
            return Raster(
                data=data,
                nodata=-9999.0,
                metadata={
                    "layer": "obstacle",
                    "source": "synthetic",
                    "reason": reason,
                    "ai_exclusion_gate": False,
                    "excluded_classes": {
                        0: "building",
                        1: "vegetation",
                        2: "water",
                    },
                },
            )
        try:
            from Wahhaj.AIModel import AIModel
            ai_model = AIModel(modelPath=MODEL_PATH)
            # This grid stores excluded-class density per heatmap cell.
            # Higher value = worse suitability.
            grid = np.zeros((rows, cols), dtype=np.float32)
            building_grid = np.zeros((rows, cols), dtype=np.float32)
            vegetation_grid = np.zeros((rows, cols), dtype=np.float32)
            water_grid = np.zeros((rows, cols), dtype=np.float32)
            bare_land_grid = np.zeros((rows, cols), dtype=np.float32)
            print("OBSTACLE GRID SHAPE =", grid.shape)
            processed_images = 0
            sorted_images = sorted(dataset.images, key=lambda img: img.timestamp)
            for img in sorted_images:
                file_path = img.filePath
                if not os.path.exists(file_path):
                    alts = [
                        file_path,
                        os.path.join("storage", file_path),
                        os.path.join("storage", os.path.basename(file_path)),
                        os.path.join("uploads", os.path.basename(file_path)),
                    ]
                    file_path = next((p for p in alts if os.path.exists(p)), None)
                if file_path is None:
                    logger.warning("_get_obstacle_layer: skipping missing image file")
                    continue

                tile_grid = self._estimate_tile_grid_from_aoi(
                    dataset.aoi,
                    target_tile_m=307.0,
                )            

                class_raster = self._classify_satellite_with_tiles(
                    ai_model=ai_model,
                    image_path=file_path,
                    tile_grid=tile_grid,
                    overlap=0.20,
                )


                classes = class_raster.data.astype(np.int32)

                # Per-class full-resolution masks
                building_mask = (classes == 0).astype(np.float32)
                vegetation_mask = (classes == 1).astype(np.float32)
                water_mask = (classes == 2).astype(np.float32)
                bare_land_mask = (classes == 3).astype(np.float32)

                # Downsample each class separately to the unified analysis grid
                building_density = self._downsample_mean(building_mask, self.TARGET_SHAPE)
                vegetation_density = self._downsample_mean(vegetation_mask, self.TARGET_SHAPE)
                water_density = self._downsample_mean(water_mask, self.TARGET_SHAPE)
                bare_land_density = self._downsample_mean(bare_land_mask, self.TARGET_SHAPE)

                # A combined density just for general display/debugging
                excluded_density = np.maximum.reduce([
                    building_density,
                    vegetation_density,
                    water_density,
                ]).astype(np.float32)

                print("BUILDING DENSITY GRID =", building_density)
                print("VEGETATION DENSITY GRID =", vegetation_density)
                print("WATER DENSITY GRID =", water_density)
                print("BARE LAND DENSITY GRID =", bare_land_density)
                print("EXCLUDED DENSITY GRID =", excluded_density)


                print("AI MODEL CLASS NAMES =", getattr(getattr(ai_model, "model", None), "names", None))
                print("AI UNIQUE CLASSES =", np.unique(class_raster.data))

                # Keep the worst density per class across all images
                if processed_images == 0:
                    building_grid = building_density
                    vegetation_grid = vegetation_density
                    water_grid = water_density
                    grid = excluded_density
                else:
                    building_grid = np.maximum(building_grid, building_density)
                    vegetation_grid = np.maximum(vegetation_grid, vegetation_density)
                    water_grid = np.maximum(water_grid, water_density)
                    bare_land_grid = np.maximum(bare_land_grid, bare_land_density)
                    grid = np.maximum(grid, excluded_density)

                processed_images += 1

            if processed_images == 0:
                reason = "image files not found"
                logger.warning("_get_obstacle_layer: using synthetic layer (%s)", reason)

                data = np.full((rows, cols), 1.0, dtype=np.float32)

                return Raster(
                    data=data,
                    nodata=-9999.0,
                    metadata={
                        "layer": "obstacle",
                        "source": "synthetic",
                        "reason": reason,
                        "ai_exclusion_gate": False,
                    },
                )

            return Raster(
                data=grid.astype(np.float32),
                nodata=-9999.0,
                metadata={
                    "layer": "obstacle",
                    "source": "AIModel",
                    "spatial": True,
                    "n_images": processed_images,
                    "ai_exclusion_gate": True,
                    "excluded_classes": {
                        0: "building",
                        1: "vegetation",
                        2: "water",
                    },
                    "building_density": building_grid.tolist(),
                    "vegetation_density": vegetation_grid.tolist(),
                    "water_density": water_grid.tolist(),
                    "bare_land_density": bare_land_grid.tolist(),
                    "combined_density": grid.tolist(),
                    "building_threshold": 0.05,
                    "water_threshold": 0.20,
                    "vegetation_threshold": 0.25,
                    "meaning": "Values represent maximum AI-excluded class density per cell.",
                },
            )

        except Exception as exc:
            logger.warning("_get_obstacle_layer failed (%s) — using synthetic layer", exc)

            data = np.full((rows, cols), 1.0, dtype=np.float32)

            return Raster(
                data=data,
                nodata=-9999.0,
                metadata={
                    "layer": "obstacle",
                    "source": "synthetic",
                    "error": str(exc),
                    "ai_exclusion_gate": False,
                },
            )