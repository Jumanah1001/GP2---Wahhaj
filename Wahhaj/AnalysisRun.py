from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from wahhaj.models import Raster, SiteInfo, FileRef
from wahhaj.SiteCandidate import SiteCandidate
from wahhaj.SuitabilityHeatmap import SuitabilityHeatmap

# Reuse shared types from the adapter module
from external_data_source_adapter import Raster

logger = logging.getLogger(__name__)

NODATA: float = -9999.0


# ---------------------------------------------------------------------------
# Supporting domain types referenced by AnalysisRun
# ---------------------------------------------------------------------------

class RunStatus(str, Enum):
    QUEUED  = "Queued"
    RUNNING = "Running"
    DONE    = "Done"
    ERROR   = "Error"


@dataclass
class EdgeNodeSpec:
    """
    Specification for a remote edge-computing node.

    Attributes
    ----------
    host : IP or hostname of the node.
    port : gRPC / REST port exposed on the node.
    auth_token : Bearer token or API key (omit from logs).
    max_cores : CPU-core budget for this run.
    gpu_enabled : Whether the node exposes a CUDA device.
    """
    host: str = "localhost"
    port: int = 8080
    auth_token: str = ""
    max_cores: int = 4
    gpu_enabled: bool = False

    def __repr__(self) -> str:
        return (
            f"EdgeNodeSpec(host={self.host!r}, port={self.port}, "
            f"cores={self.max_cores}, gpu={self.gpu_enabled})"
        )


@dataclass
class Point:
    """Geographic point (WGS-84 decimal degrees)."""
    lon: float
    lat: float

    def __str__(self) -> str:
        return f"({self.lat:.6f}°, {self.lon:.6f}°)"




# ---------------------------------------------------------------------------
# AnalysisRun
# ---------------------------------------------------------------------------

class AnalysisRun:
    """
    Represents one complete end-to-end suitability analysis execution.

    Lifecycle
    ---------
    1. Instantiate with an AHPModel and FeatureExtractor already configured.
    2. Call ``execute(dataset)`` or ``processOnEdgeNode()`` to run the pipeline.
    3. Read ``suitability`` (Raster), ``candidates`` (List[SiteCandidate]),
       and ``heatmap`` (SuitabilityHeatmap) from the instance.

    UML attributes
    --------------
    runId        : str (UUID)
    startedAt    : datetime
    finishedAt   : datetime
    durationSec  : int
    suitability  : Raster          – final composite suitability grid [0, 1]
    status       : RunStatus
    edgeNode     : EdgeNodeSpec

    UML methods
    -----------
    processOnEdgeNode()
        Serialises the run request, ships it to the configured EdgeNodeSpec,
        and blocks until a result arrives.  Falls back to local execution
        when no edge node is configured.
    """

    def __init__(
        self,
        ahp_model: Any,               # AHPModel – typed as Any to avoid circular import
        feature_extractor: Any,       # FeatureExtractor
        edge_node: Optional[EdgeNodeSpec] = None,
        top_k_sites: int = 10,
        min_site_score: float = 0.6,
    ) -> None:
        # UML attributes ─────────────────────────────────────────────────────
        self.runId:       str           = str(uuid.uuid4())
        self.startedAt:   Optional[datetime] = None
        self.finishedAt:  Optional[datetime] = None
        self.durationSec: int           = 0
        self.suitability: Optional[Raster]   = None
        self.status:      RunStatus     = RunStatus.QUEUED
        self.edgeNode:    Optional[EdgeNodeSpec] = edge_node

        # Internal references
        self._ahp       = ahp_model
        self._extractor = feature_extractor
        self._top_k     = top_k_sites
        self._min_score = min_site_score

        # Outputs populated after execution
        self.candidates: List[SiteCandidate] = []
        self.heatmap:    Optional[SuitabilityHeatmap] = None

        logger.info(
            "AnalysisRun created | id=%s | edgeNode=%s | top_k=%d",
            self.runId[:8], self.edgeNode, self._top_k,
        )

    # -----------------------------------------------------------------------
    # Public interface  (UML methods + orchestration helpers)
    # -----------------------------------------------------------------------

    def execute(self, dataset: Any) -> "AnalysisRun":
        """
        Run the full analysis pipeline locally.

        Steps
        -----
        1. Feature extraction  (FeatureExtractor.extractFeatures + normalizeData)
        2. AHP suitability scoring  (AHPModel.computeSuitabilityScore)
        3. Candidate site extraction
        4. Heatmap materialisation

        Parameters
        ----------
        dataset : Dataset  – survey area + UAV images.

        Returns
        -------
        AnalysisRun  – *self* for chaining.
        """
        self._start()

        try:
            # Step 1: Extract and normalise feature layers
            logger.info("[%s] Step 1 – Feature extraction …", self.runId[:8])
            self._extractor.extractFeatures(dataset)
            self._extractor.normalizeData()
            layers = list(self._extractor.layers.values())

            # Step 2: Compute suitability via AHP
            logger.info("[%s] Step 2 – AHP suitability scoring …", self.runId[:8])
            self.suitability = self._ahp.computeSuitabilityScore(layers)

            # Step 3: Extract top-K candidate sites
            logger.info("[%s] Step 3 – Extracting candidate sites …", self.runId[:8])
            self.candidates = self._extract_candidates(self.suitability, dataset)

            # Step 4: Materialise heatmap
            logger.info("[%s] Step 4 – Materialising SuitabilityHeatmap …", self.runId[:8])
            self.heatmap = SuitabilityHeatmap(
                scores=self.suitability,
                resolution=dataset.aoi.resolution_m,
            )
            self.heatmap.generateHeatmap(self.suitability)

            self._finish(success=True)

        except Exception as exc:
            logger.error("[%s] Analysis failed: %s", self.runId[:8], exc, exc_info=True)
            self._finish(success=False)
            raise

        return self

    def processOnEdgeNode(self, dataset: Any) -> "AnalysisRun":
        """
        Delegate execution to the configured edge node.

        If :attr:`edgeNode` is ``None`` or the node is unreachable, the method
        falls back to local execution transparently.

        Parameters
        ----------
        dataset : Dataset – survey area + UAV images.

        Returns
        -------
        AnalysisRun  – *self*.
        """
        if self.edgeNode is None:
            logger.warning(
                "[%s] processOnEdgeNode called but no edgeNode configured – "
                "falling back to local execution.",
                self.runId[:8],
            )
            return self.execute(dataset)

        logger.info(
            "[%s] Dispatching to edge node %s:%d …",
            self.runId[:8], self.edgeNode.host, self.edgeNode.port,
        )

        try:
            self._dispatch_to_edge(dataset)
        except EdgeNodeError as exc:
            logger.error(
                "[%s] Edge node unreachable (%s) – falling back to local execution.",
                self.runId[:8], exc,
            )
            return self.execute(dataset)

        return self

    # -----------------------------------------------------------------------
    # Result accessors
    # -----------------------------------------------------------------------

    def get_top_candidates(self, n: Optional[int] = None) -> List[SiteCandidate]:
        """Return the top-*n* candidate sites ranked by score (descending)."""
        ranked = sorted(self.candidates, key=lambda s: s.score, reverse=True)
        return ranked[:n] if n else ranked

    def summary(self) -> Dict[str, Any]:
        """Return a serialisable run summary dict."""
        suit_stats = self.suitability.statistics() if self.suitability else {}
        return {
            "runId":        self.runId,
            "status":       self.status.value,
            "startedAt":    self.startedAt.isoformat() if self.startedAt else None,
            "finishedAt":   self.finishedAt.isoformat() if self.finishedAt else None,
            "durationSec":  self.durationSec,
            "candidateCount": len(self.candidates),
            "suitability":  suit_stats,
            "edgeNode":     repr(self.edgeNode),
        }

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _start(self) -> None:
        """Mark the run as started."""
        self.status    = RunStatus.RUNNING
        self.startedAt = datetime.utcnow()
        logger.info("[%s] AnalysisRun STARTED at %s", self.runId[:8], self.startedAt.isoformat())

    def _finish(self, success: bool) -> None:
        """Mark the run as finished and compute wall-clock duration."""
        self.finishedAt  = datetime.utcnow()
        delta            = self.finishedAt - (self.startedAt or self.finishedAt)
        self.durationSec = int(delta.total_seconds())
        self.status      = RunStatus.DONE if success else RunStatus.ERROR
        logger.info(
            "[%s] AnalysisRun %s in %ds",
            self.runId[:8], self.status.value, self.durationSec,
        )

    def _extract_candidates(
        self, suitability: Raster, dataset: Any
    ) -> List[SiteCandidate]:
        """
        Identify the top-K contiguous high-suitability areas.

        Uses a simple peak-finding approach: rank all valid pixels by score,
        select the top-K that are spatially separated by at least one pixel
        (greedy non-maximum suppression).

        Parameters
        ----------
        suitability : Raster – normalised grid [0, 1].
        dataset     : Dataset – provides the AOI transform.

        Returns
        -------
        List[SiteCandidate]
        """
        data  = suitability.data
        valid = data != suitability.nodata
        x_origin, x_res, y_origin, y_res = suitability.transform
        rows, cols = data.shape[:2]

        # Flatten and sort valid pixels
        flat_scores = data.copy()
        flat_scores[~valid] = -np.inf
        flat_idx = np.argsort(flat_scores, axis=None)[::-1]

        candidates: List[SiteCandidate] = []
        suppressed = np.zeros((rows, cols), dtype=bool)
        nms_radius = max(2, rows // 50)          # suppress within ~2% of extent

        for linear_idx in flat_idx:
            if len(candidates) >= self._top_k:
                break
            r, c = divmod(int(linear_idx), cols)
            if suppressed[r, c]:
                continue
            score = float(data[r, c])
            if score < self._min_score:
                break

            # Convert pixel centre → geographic coordinates
            lon = x_origin + (c + 0.5) * x_res
            lat = y_origin + (r + 0.5) * y_res   # y_res is negative (north-up)

            candidates.append(SiteCandidate(
                score    = score,
                centroid = Point(lon=lon, lat=lat),
                attrs    = {
                    "pixel_row": r,
                    "pixel_col": c,
                    "rank":      len(candidates) + 1,
                },
            ))

            # Suppress neighbourhood
            r0 = max(0, r - nms_radius)
            r1 = min(rows, r + nms_radius + 1)
            c0 = max(0, c - nms_radius)
            c1 = min(cols, c + nms_radius + 1)
            suppressed[r0:r1, c0:c1] = True

        logger.info(
            "[%s] Candidate extraction: %d sites with score ≥ %.2f",
            self.runId[:8], len(candidates), self._min_score,
        )
        return candidates

    def _dispatch_to_edge(self, dataset: Any) -> None:
        """
        Send the analysis job to the remote edge node via HTTP/gRPC.

        This is a stub.  In production:
          1. Serialise ``dataset`` + AHP weights to JSON / protobuf.
          2. POST to ``http://{host}:{port}/api/v1/runs``.
          3. Poll ``/api/v1/runs/{runId}/status`` until done.
          4. Fetch results and deserialise back into ``self.suitability``
             and ``self.candidates``.
        """
        node = self.edgeNode
        logger.info(
            "[%s] _dispatch_to_edge → %s:%d (stub – simulating network call)",
            self.runId[:8], node.host, node.port,
        )
        # Simulate a failed connection to trigger the fallback in tests
        raise EdgeNodeError(
            f"Connection refused: {node.host}:{node.port}"
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EdgeNodeError(RuntimeError):
    """Raised when the remote edge node is unreachable or returns an error."""

