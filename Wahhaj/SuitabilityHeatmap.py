from dataclasses import dataclass, field
from typing import Optional
import uuid
from wahhaj.models import SiteInfo, FileRef, Raster

@dataclass
class TileSet:
    tiles: list = field(default_factory=list)







class SuitabilityHeatmap:
    def __init__(
        self,
        resolution: float,
        color_scale: str,
    ):
        self.heatmap_id: str = str(uuid.uuid4())
        self.resolution: float = resolution
        self.color_scale: str = color_scale
        self._tile_set: Optional[TileSet] = None
        self._scores: Optional[Raster] = None

    # ---------- public methods ----------

    def generate_heatmap(self, scores: Raster) -> TileSet:
        """
        Convert a suitability scores raster into a TileSet
        for web/map rendering.
        """
        self._scores = scores
        tiles = self._rasterize_to_tiles(scores)
        self._tile_set = TileSet(tiles=tiles)
        return self._tile_set

    def display(self) -> None:
        """
        Render the heatmap visually (e.g. open in a viewer or push to UI).
        """
        if self._tile_set is None:
            raise RuntimeError("No heatmap generated yet. Call generate_heatmap() first.")
        print(f"[SuitabilityHeatmap] Displaying heatmap {self.heatmap_id}")
        print(f"  Resolution : {self.resolution}")
        print(f"  Color scale: {self.color_scale}")
        print(f"  Tiles      : {len(self._tile_set.tiles)}")

    def export_pdf(self) -> FileRef:
        """
        Export the current heatmap to a PDF and return a FileRef to it.
        """
        if self._tile_set is None:
            raise RuntimeError("No heatmap generated yet. Call generate_heatmap() first.")
        pdf_path = f"/exports/heatmap_{self.heatmap_id}.pdf"
        print(f"[SuitabilityHeatmap] Exporting PDF → {pdf_path}")
        # PDF generation logic would go here (e.g. via ReportLab / WeasyPrint)
        return FileRef(path=pdf_path, name=f"heatmap_{self.heatmap_id}.pdf")

    def render(self, tile_set: TileSet) -> TileSet:
        """
        Re-render an existing TileSet (e.g. apply a different color scale).
        """
        rendered_tiles = self._apply_color_scale(tile_set.tiles)
        return TileSet(tiles=rendered_tiles)

    def inspect(self, x: float, y: float) -> "SiteInfo":
        """
        Return site information for a given (x, y) coordinate on the heatmap.
        """
        print(f"[SuitabilityHeatmap] Inspecting coordinate ({x}, {y})")
        site_id = str(uuid.uuid4())
        description = f"Site at ({x:.4f}, {y:.4f}) — score: {self._lookup_score(x, y):.2f}"
        return SiteInfo(site_id=site_id, description=description, coordinates=(x, y))

    # ---------- private helpers ----------

    def _rasterize_to_tiles(self, scores: Raster) -> list:
        """Split a raster into map tiles according to self.resolution."""
        # Placeholder: real implementation would use e.g. gdal2tiles or mercantile
        num_tiles = max(1, int(scores.width * scores.height / (self.resolution ** 2)))
        return [{"tile_index": i, "data": None} for i in range(num_tiles)]

    def _apply_color_scale(self, tiles: list) -> list:
        """Apply the configured color scale to a list of tiles."""
        return [dict(t, color_scale=self.color_scale) for t in tiles]

    def _lookup_score(self, x: float, y: float) -> float:
        """Look up the suitability score at (x, y) from the stored raster."""
        if self._scores is None:
            return 0.0
        # Placeholder: real implementation would do a spatial lookup
        return 0.75

    # ---------- dunder ----------

    def __repr__(self) -> str:
        return (
            f"SuitabilityHeatmap(id={self.heatmap_id!r}, "
            f"resolution={self.resolution}, "
            f"color_scale={self.color_scale!r})"
        )
