import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SiteCandidate:
    """
    Represents a ranked solar-site candidate produced by the analysis pipeline.

    Attributes
    ----------
    siteId   : Unique identifier (UUID string).
    score    : Normalized suitability score in range [0, 1].
    centroid : Geographic center (Point).
    attrs    : Additional properties (pixel position, solar value, etc.).
    rank     : Assigned ranking (1 = best).
    """

    siteId: str = field(default_factory=lambda: str(uuid.uuid4()))
    score: float = 0.0
    centroid: "Point" = None
    attrs: Dict[str, Any] = field(default_factory=dict)

    rank: Optional[int] = None

    def __post_init__(self) -> None:
        """
        Validate score range after initialization.
        """
        if not (0.0 <= float(self.score) <= 1.0):
            logger.warning(
                "SiteCandidate.score is outside expected range [0,1]: %s",
                self.score,
            )

    # ---------------------------------------------------------
    # Comparison logic
    # ---------------------------------------------------------

    def __lt__(self, other: "SiteCandidate") -> bool:
        """
        Defines ordering logic.

        Higher score means better candidate.
        If scores are equal, fallback to siteId for deterministic ordering.
        """
        if not isinstance(other, SiteCandidate):
            return NotImplemented

        if self.score != other.score:
            return self.score < other.score

        return self.siteId < other.siteId

    # ---------------------------------------------------------
    # Ranking utility
    # ---------------------------------------------------------

    @staticmethod
    def rank_all(candidates: List["SiteCandidate"]) -> List["SiteCandidate"]:
        """
        Sort candidates by score (descending) and assign ranking.

        Parameters
        ----------
        candidates : List of SiteCandidate objects.

        Returns
        -------
        Ranked list of SiteCandidate objects.
        """
        ranked = sorted(candidates, reverse=True)

        for i, candidate in enumerate(ranked, start=1):
            candidate.rank = i

        return ranked

    # ---------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert object to dictionary (useful for reports or storage).
        """
        return {
            "siteId": self.siteId,
            "score": float(self.score),
            "rank": self.rank,
            "centroid": {
                "lon": float(self.centroid.lon),
                "lat": float(self.centroid.lat),
            } if self.centroid else None,
            "attrs": dict(self.attrs),
            "createdAt": self.createdAt.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"SiteCandidate(rank={self.rank}, "
            f"score={self.score:.4f}, "
            f"centroid={self.centroid})"
        )


# -------------------------------------------------------------------
# Simple internal test (can be executed directly for quick validation)
# -------------------------------------------------------------------

if __name__ == "__main__":

    # Minimal Point placeholder for standalone test
    class Point:
        def __init__(self, lon, lat):
            self.lon = lon
            self.lat = lat

        def __repr__(self):
            return f"Point(lon={self.lon}, lat={self.lat})"

    print("Running SiteCandidate self-test...")

    c1 = SiteCandidate(score=0.9, centroid=Point(46.7, 24.7))
    c2 = SiteCandidate(score=0.7, centroid=Point(46.8, 24.8))
    c3 = SiteCandidate(score=0.8, centroid=Point(46.9, 24.9))

    ranked = SiteCandidate.rank_all([c1, c2, c3])
   

for c in ranked:
    print(c.score, c.rank)

    assert ranked[0].score == 0.9
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[2].rank == 3

    assert max([c1, c2, c3]).score == 0.9

 
