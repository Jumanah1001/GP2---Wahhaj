# tests/test_feature_extraction.py
# ─────────────────────────────────────────────────────────────
# Unit Tests for Layer: Data Extraction
#
# Run your tests only:
#   pytest tests/test_feature_extraction.py -v
#
# Run full integration after your tests pass:
#   pytest tests/test_integration.py -v
#
# Pre-PR checklist:
#   1. All 4 tests below pass
#   2. test_integration.py passes (you didn't break other layers)
#   3. No duplicate class definitions:
#        grep -r "class ExternalDataSourceAdapter" wahhaj/   → 1 result only
#        grep -r "class FeatureExtractor" wahhaj/            → 1 result only
# ─────────────────────────────────────────────────────────────

import pytest
from Wahhaj.ExternalDataSourceAdapter import ExternalDataSourceAdapter
from Wahhaj.FeatureExtractor import FeatureExtractor, Dataset
from Wahhaj.models import Raster
from datetime import datetime


# ── Adapter Tests ─────────────────────────────────────────────

def test_adapter_fetch_ghi():
    """
    Basic smoke test — fetchGHI returns a valid Raster.
    If this fails, the adapter is not importable or method name is wrong.
    """
    adapter = ExternalDataSourceAdapter()
    aoi = (46.0, 24.0, 47.0, 25.0)
    result = adapter.fetchGHI(aoi, datetime.now())

    assert isinstance(result, Raster), "fetchGHI must return a Raster"
    assert result.data is not None, "Raster data must not be None"


def test_adapter_all_methods():
    """
    Verifies all 4 method names match the CONTRACT exactly.
    This catches any remaining snake_case vs camelCase mismatches.

    NOTE: FetchElevation has capital F — this is intentional,
    it must match exactly what FeatureExtractor calls.
    """
    adapter = ExternalDataSourceAdapter()
    aoi = (46.0, 24.0, 47.0, 25.0)
    t = datetime.now()

    # NOTE: these names must match ExternalDataSourceAdapter exactly
    for method_name in ["fetchGHI", "fetchLST", "fetchSunshineHours", "FetchElevation"]:
        result = getattr(adapter, method_name)(aoi, t)
        assert isinstance(result, Raster), f"{method_name} must return Raster"
        assert result.data.dtype.name == "float32", \
            f"{method_name} must return float32 — AHPModel requires this"
        assert result.nodata == -9999.0, \
            f"{method_name} nodata must be -9999.0 — normalizeData() depends on this"


# ── FeatureExtractor Tests ────────────────────────────────────

def test_feature_extractor_pipeline():
    """
    Verifies extractFeatures populates all expected layer keys.
    Layer names must match AHPModel.WEIGHTS keys exactly.
    """
    extractor = FeatureExtractor()
    dataset = Dataset(name="test_dataset")
    extractor.extractFeatures(dataset)

    assert len(extractor.layers) > 0, "layers must not be empty after extractFeatures"

    # NOTE: these are the exact keys AHPModel expects
    expected_layers = ["ghi", "lst", "sunshine", "elevation", "slope"]
    for layer in expected_layers:
        assert layer in extractor.layers, \
            f"Layer '{layer}' missing — AHPModel will not find it"


def test_normalize_data():
    """
    Verifies all layer values are in [0.0, 1.0] after normalizeData().
    AHPModel multiplies values by weights and sums — un-normalized
    values will produce incorrect suitability scores.

    Skips nodata cells (-9999.0) in the check.
    """
    extractor = FeatureExtractor()
    dataset = Dataset(name="test_dataset")
    extractor.extractFeatures(dataset).normalizeData()

    for name, raster in extractor.layers.items():
        valid = raster.data[raster.data != -9999.0]
        if len(valid) > 0:
            assert valid.min() >= 0.0, f"{name}: min value < 0 after normalize"
            assert valid.max() <= 1.0, f"{name}: max value > 1 after normalize"
