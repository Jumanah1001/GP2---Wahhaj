# ─────────────────────────────────────────────────────────────
# Unit Tests for Layer: Data Extraction
#
# Run your tests only:
#   pytest tests/test_feature_extraction.py -v
#
# Run full integration after your tests pass:
#   pytest tests/test_integration.py -v
# ─────────────────────────────────────────────────────────────

from datetime import datetime

import pytest

from Wahhaj.ExternalDataSourceAdapter import ExternalDataSourceAdapter
from Wahhaj.FeatureExtractor import FeatureExtractor, Dataset
from Wahhaj.models import Raster


# ── Adapter Tests ─────────────────────────────────────────────

def test_adapter_fetch_ghi():
    """
    Basic smoke test — fetchGHI returns a valid Raster.
    """
    adapter = ExternalDataSourceAdapter()
    aoi = (46.0, 24.0, 47.0, 25.0)
    result = adapter.fetchGHI(aoi, datetime.now())

    assert isinstance(result, Raster), "fetchGHI must return a Raster"
    assert result.data is not None, "Raster data must not be None"
    assert result.data.shape == (5, 5), "fetchGHI must return a 5x5 raster"


def test_adapter_all_methods():
    """
    Verifies all 4 method names match the CONTRACT exactly.
    """
    adapter = ExternalDataSourceAdapter()
    aoi = (46.0, 24.0, 47.0, 25.0)
    t = datetime.now()

    for method_name in ["fetchGHI", "fetchLST", "fetchSunshineHours", "FetchElevation"]:
        result = getattr(adapter, method_name)(aoi, t)

        assert isinstance(result, Raster), f"{method_name} must return Raster"
        assert result.data.dtype.name == "float32", \
            f"{method_name} must return float32 — AHPModel requires this"
        assert result.nodata == -9999.0, \
            f"{method_name} nodata must be -9999.0 — normalizeData() depends on this"
        assert result.data.shape == (5, 5), \
            f"{method_name} must return a 5x5 raster after alignment"


# ── FeatureExtractor Tests ────────────────────────────────────

def test_feature_extractor_pipeline():
    """
    Verifies extractFeatures populates all expected layer keys.
    """
    extractor = FeatureExtractor()
    dataset = Dataset(name="test_dataset")
    extractor.extractFeatures(dataset)

    assert len(extractor.layers) > 0, "layers must not be empty after extractFeatures"

    expected_layers = ["ghi", "lst", "sunshine", "elevation", "slope"]
    for layer in expected_layers:
        assert layer in extractor.layers, \
            f"Layer '{layer}' missing — AHPModel will not find it"

    for name, raster in extractor.layers.items():
        assert raster.data.shape == (5, 5), f"{name} must be aligned to 5x5"


def test_normalize_data():
    """
    Verifies all layer values are in [0.0, 1.0] after normalizeData().
    """
    extractor = FeatureExtractor()
    dataset = Dataset(name="test_dataset")
    extractor.extractFeatures(dataset).normalizeData()

    for name, raster in extractor.layers.items():
        valid = raster.data[raster.data != -9999.0]
        if len(valid) > 0:
            assert valid.min() >= 0.0, f"{name}: min value < 0 after normalize"
            assert valid.max() <= 1.0, f"{name}: max value > 1 after normalize"
