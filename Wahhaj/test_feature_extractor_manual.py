from datetime import datetime

from wahhaj.FeatureExtractor import FeatureExtractor, Dataset

dataset = Dataset(
    name="manual-test",
    aoi=(46.0, 24.0, 47.0, 25.0),   # (lon_min, lat_min, lon_max, lat_max)
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 1, 31),
)

extractor = FeatureExtractor()
extractor.extractFeatures(dataset)

print("Extracted layer names:")
print(list(extractor.layers.keys()))

print("\nLayer shapes before normalization:")
for name, raster in extractor.layers.items():
    print(f"{name}: shape={raster.data.shape}, metadata={raster.metadata}")

extractor.normalizeData()

print("\nLayer ranges after normalization:")
for name, raster in extractor.layers.items():
    valid = raster.data[raster.data != raster.nodata]
    if valid.size > 0:
        print(f"{name}: min={valid.min():.4f}, max={valid.max():.4f}")
    else:
        print(f"{name}: no valid cells")
