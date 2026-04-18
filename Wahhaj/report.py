"""
Wahhaj/report.py
================
Report class — generates comprehensive analysis reports.

Changes in this version
-----------------------
1. generate() now accepts optional location dict and suitability raster
   so the report can include the location name and heatmap image.

2. _generate_report_content() completely rewritten:
   - Professional header with location, date, run ID
   - Clear executive summary
   - AHP criteria weights table
   - Ranked recommendations table (up to 10 sites)
   - Statistical summary with score distribution
   - Methodology section

3. New method: build_pdf_bytes(run, ranked, location, suitability)
   - Uses reportlab to build a proper PDF.
   - Embeds a matplotlib heatmap image if suitability raster is available.
   - Returns bytes directly for st.download_button().
   - Falls back gracefully if reportlab or matplotlib is not installed.

4. The old placeholder export() method is kept for compatibility but
   the real export path is build_pdf_bytes().
"""

import io
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class Report:
    """
    Generate and export analysis reports for solar site selection.

    Attributes
    ----------
    report_id : UUID
    date      : datetime
    summary   : str  — executive summary sentence
    file_path : str  — logical path (not a real file, legacy attribute)
    """

    def __init__(self):
        self.report_id: UUID     = uuid4()
        self.date: datetime      = datetime.now()
        self.summary: str        = ""
        self.file_path: str      = ""

    # ── Public API ────────────────────────────────────────────────────────

    def generate(self, run, ranks: List, location: Optional[dict] = None) -> None:
        """
        Build the summary string and set file_path.

        Parameters
        ----------
        run      : AnalysisRun
        ranks    : List[SiteCandidate]  (already ranked)
        location : dict with optional keys "location_name", "latitude", "longitude"
        """
        loc_name = (location or {}).get("location_name", "Unknown Location")

        if ranks:
            top = ranks[0].score
            self.summary = (
                f"Solar site analysis for {loc_name} completed on "
                f"{self.date.strftime('%Y-%m-%d')}. "
                f"Identified {len(ranks)} candidate site(s). "
                f"Top site achieved a suitability score of {top * 100:.1f}%."
            )
        else:
            self.summary = (
                f"Solar site analysis for {loc_name} completed on "
                f"{self.date.strftime('%Y-%m-%d')}. "
                "No candidate sites were identified in the selected area."
            )

        self.file_path = f"/reports/solar_analysis_{self.report_id}.pdf"
        logger.info("Report generated: %s", self.summary[:80])

    def export(self):
        """Legacy stub — kept for compatibility. Use build_pdf_bytes() instead."""
        if not self.file_path:
            raise ValueError("Call generate() before export().")
        logger.info("Report export requested (stub): %s", self.file_path)
        return None

    def build_pdf_bytes(
        self,
        run,
        ranked: List,
        location: Optional[dict] = None,
        suitability=None,       # Raster or None
        aoi: Optional[tuple] = None,
    ) -> Optional[bytes]:
        """
        Build and return a PDF as bytes using reportlab.

        Includes:
        - Title page with location and date
        - Executive summary
        - Suitability heatmap image (if suitability raster is available)
        - Ranked recommendations table
        - AHP criteria weights
        - Statistical summary
        - Methodology

        Returns None if reportlab is not installed (caller should fall back
        to the .txt download).
        """
        try:
            return self._build_pdf_reportlab(run, ranked, location, suitability, aoi)
        except ImportError:
            logger.warning("reportlab not installed — PDF export unavailable.")
            return None
        except Exception as exc:
            logger.error("PDF build failed: %s", exc, exc_info=True)
            return None

    # ── Text report (always available) ───────────────────────────────────

    def _generate_report_content(self, run, ranks: List) -> str:
        """Generate a plain-text version of the report."""
        content = []
        loc     = getattr(self, "_location", {}) or {}
        loc_name = loc.get("location_name", "—")

        W = 80
        content.append("=" * W)
        content.append("  WAHHAJ — SOLAR SITE SUITABILITY ANALYSIS REPORT")
        content.append("=" * W)
        content.append(f"\n  Location : {loc_name}")
        content.append(f"  Generated: {self.date.strftime('%Y-%m-%d %H:%M')}")
        content.append(f"  Report ID: {self.report_id}")
        content.append(f"  Run ID   : {run.runId}")
        content.append(f"\n{'-' * W}\n")

        # Executive summary
        content.append("EXECUTIVE SUMMARY")
        content.append("-" * W)
        content.append(self.summary)
        content.append(f"\n{'-' * W}\n")

        # Analysis details
        content.append("ANALYSIS DETAILS")
        content.append("-" * W)
        summary = run.summary()
        content.append(f"  Status  : {summary.get('status', '—')}")
        content.append(f"  Started : {run.startedAt.strftime('%Y-%m-%d %H:%M:%S') if run.startedAt else '—'}")
        if run.finishedAt:
            content.append(f"  Finished: {run.finishedAt.strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"  Duration: {run.durationSec} seconds")
        content.append(f"\n{'-' * W}\n")

        # AHP weights
        content.append("AHP CRITERIA WEIGHTS")
        content.append("-" * W)
        weights = [
            ("Solar Irradiance (GHI)",    0.30, False),
            ("Terrain Slope",             0.22, True),
            ("Sunshine Hours",            0.18, False),
            ("Obstacle Density",          0.13, True),
            ("Surface Temperature (LST)", 0.10, True),
            ("Elevation",                 0.07, False),
        ]
        for name, w, inv in weights:
            inv_note = " (lower is better)" if inv else ""
            bar = "▓" * int(w * 40)
            content.append(f"  {name:<30}{bar}  {w:.0%}{inv_note}")
        content.append(f"\n{'-' * W}\n")

        # Ranked recommendations
        content.append("RANKED SITE RECOMMENDATIONS")
        content.append("-" * W)
        if ranks:
            header = f"  {'Rank':<6}{'Score':>8}  {'Score/10':>9}  {'Latitude':>12}  {'Longitude':>12}  Recommendation"
            content.append(header)
            content.append("  " + "-" * (len(header) - 2))
            for c in ranks[:10]:
                s10  = round(c.score * 10, 2)
                lat  = f"{c.centroid.lat:.4f}°N" if c.centroid else "—"
                lon  = f"{c.centroid.lon:.4f}°E" if c.centroid else "—"
                rec  = (
                    "Highly Recommended" if c.score >= 0.8 else
                    "Recommended"        if c.score >= 0.6 else
                    "Not Applicable"
                )
                content.append(f"  {c.rank:<6}{c.score:>8.4f}  {s10:>9.2f}  {lat:>12}  {lon:>12}  {rec}")
            if len(ranks) > 10:
                content.append(f"\n  ... and {len(ranks) - 10} more site(s).")
        else:
            content.append("  No candidate sites identified.")
        content.append(f"\n{'-' * W}\n")

        # Statistical summary
        if ranks:
            scores = [c.score for c in ranks]
            content.append("STATISTICAL SUMMARY")
            content.append("-" * W)
            content.append(f"  Total sites evaluated : {len(ranks)}")
            content.append(f"  Highest score         : {max(scores) * 100:.1f}%")
            content.append(f"  Average score         : {sum(scores)/len(scores) * 100:.1f}%")
            content.append(f"  Lowest score          : {min(scores) * 100:.1f}%")

            excellent = sum(1 for s in scores if s > 0.8)
            high      = sum(1 for s in scores if 0.6 < s <= 0.8)
            moderate  = sum(1 for s in scores if 0.4 < s <= 0.6)
            low       = sum(1 for s in scores if s <= 0.4)
            n = len(ranks)

            content.append(f"\n  Score distribution:")
            content.append(f"    Highly Suitable (>80%)  : {excellent:3d}  ({excellent/n*100:.1f}%)")
            content.append(f"    Suitable (60–80%)       : {high:3d}  ({high/n*100:.1f}%)")
            content.append(f"    Moderate (40–60%)       : {moderate:3d}  ({moderate/n*100:.1f}%)")
            content.append(f"    Low (<40%)              : {low:3d}  ({low/n*100:.1f}%)")
            content.append(f"\n{'-' * W}\n")

        # Methodology
        content.append("METHODOLOGY")
        content.append("-" * W)
        content.append("  Framework : UAV photogrammetry + GIS + AHP multi-criteria analysis")
        content.append("  AI model  : YOLOv8 for obstacle detection")
        content.append("  Data layers:")
        content.append("    • Global Horizontal Irradiance (GHI) — Open-Meteo API")
        content.append("    • Land Surface Temperature (LST)     — MODIS / synthetic")
        content.append("    • Terrain Slope                      — derived from elevation")
        content.append("    • Elevation (DEM)                    — SRTM / synthetic")
        content.append("    • Sunshine Hours                     — Open-Meteo API")
        content.append("    • Obstacle Density                   — YOLOv8 detection")
        content.append(f"\n{'-' * W}")
        content.append("  Aligned with Saudi Vision 2030 — National Net-Zero 2060 Pathway")
        content.append("  CCIS — Princess Nora bint Abdul Rahman University (PNU)")
        content.append(f"\n{'=' * W}")
        content.append("  End of Report")
        content.append("=" * W)

        return "\n".join(content)

    # ── Private: PDF builder ──────────────────────────────────────────────

    def _build_pdf_reportlab(
        self,
        run,
        ranked: List,
        location: Optional[dict],
        suitability,
        aoi: Optional[tuple],
    ) -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        loc_name = (location or {}).get("location_name", "Unknown Location")
        lat      = (location or {}).get("latitude")
        lon      = (location or {}).get("longitude")
        summary_obj = run.summary()

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        BLUE   = colors.HexColor("#0070FF")
        DARK   = colors.HexColor("#1a1a1a")
        GREY   = colors.HexColor("#555555")
        LGREY  = colors.HexColor("#f4f4f4")
        GREEN  = colors.HexColor("#166534")
        AMBER  = colors.HexColor("#713f12")
        ORANGE_DARK = colors.HexColor("#D97706")
        ORANGE_LIGHT = colors.HexColor("#FFF3E8")

        h1 = ParagraphStyle("h1", parent=styles["Heading1"],
                             fontSize=22, textColor=ORANGE_DARK, spaceAfter=4,
                             fontName="Helvetica-Bold", alignment=TA_CENTER)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"],
                             fontSize=14, textColor=DARK, spaceBefore=14, spaceAfter=4,
                             fontName="Helvetica-Bold", borderPad=2)
        normal = ParagraphStyle("nm", parent=styles["Normal"],
                                fontSize=10, textColor=DARK, leading=14)
        small  = ParagraphStyle("sm", parent=styles["Normal"],
                                fontSize=9, textColor=GREY, leading=12)
        center = ParagraphStyle("ctr", parent=styles["Normal"],
                                fontSize=10, textColor=DARK, alignment=TA_CENTER)
        sum_style = ParagraphStyle("sum", parent=styles["Normal"],
                                   fontSize=11, textColor=DARK, leading=16,
                                   backColor=colors.HexColor("#f0f7ff"),
                                   borderPad=8, borderWidth=1,
                                   borderColor=ORANGE_DARK, borderRadius=4)

        story = []

        # ── Title ──────────────────────────────────────────────────────
        story.append(Paragraph("WAHHAJ", h1))
        story.append(Paragraph(
            "Solar Site Suitability Analysis Report",
            ParagraphStyle("sub", parent=h1, fontSize=13, textColor=GREY),
        ))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=2, color=ORANGE_DARK))
        story.append(Spacer(1, 0.2*cm))

        # ── Meta table ──────────────────────────────────────────────────
        coord_str = f"{lat:.4f}°N, {lon:.4f}°E" if lat and lon else "—"
        meta_data = [
            ["Location",  loc_name,              "Generated", self.date.strftime("%Y-%m-%d %H:%M")],
            ["Status",    summary_obj.get("status", "—"),
             "Duration",  f"{summary_obj.get('durationSec', '—')} seconds"],
            ["Candidates", str(len(ranked)),
             "Coordinates", coord_str],
            ["Report ID",  str(self.report_id)[:16] + "…",
             "Run ID", run.runId[:16] + "…"],
        ]
        meta_tbl = Table(meta_data, colWidths=[3*cm, 6.5*cm, 3*cm, 5.5*cm])
        meta_tbl.setStyle(TableStyle([
            ("FONT",      (0, 0), (-1, -1), "Helvetica",      9),
            ("FONT",      (0, 0), (0, -1),  "Helvetica-Bold", 9),
            ("FONT",      (2, 0), (2, -1),  "Helvetica-Bold", 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
            ("TEXTCOLOR", (0, 0), (0, -1),  GREY),
            ("TEXTCOLOR", (2, 0), (2, -1),  GREY),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LGREY]),
            ("GRID",      (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(meta_tbl)
        story.append(Spacer(1, 0.4*cm))

        # ── Executive summary ───────────────────────────────────────────
        story.append(Paragraph("Executive Summary", h2))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(self.summary, sum_style))
        story.append(Spacer(1, 0.3*cm))

        # ── Heatmap image ────────────────────────────────────────────────
        heatmap_img = self._render_heatmap_image(suitability, aoi, ranked)
        if heatmap_img is not None:
            story.append(Paragraph("Suitability Heatmap", h2))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
            story.append(Spacer(1, 0.15*cm))
            story.append(heatmap_img)
            story.append(Spacer(1, 0.1*cm))
            story.append(Paragraph(
                "Color scale: Red = Low suitability &nbsp;→&nbsp; Green = High suitability. "
                "Numbered markers indicate top-ranked candidate sites.",
                small,
            ))
            story.append(Spacer(1, 0.3*cm))

        # ── Ranked recommendations ───────────────────────────────────────
        story.append(Paragraph("Ranked Site Recommendations", h2))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
        story.append(Spacer(1, 0.15*cm))

        if ranked:
            tbl_data = [["Rank", "Score", "Score/10", "Latitude", "Longitude", "Recommendation"]]
            tbl_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), ORANGE_DARK),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONT",       (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("FONT",       (0, 1), (-1, -1), "Helvetica", 9),
                ("TEXTCOLOR",  (0, 1), (-1, -1), DARK),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",      (5, 1), (5, -1), "LEFT"),
                ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ORANGE_LIGHT]),
            ]
            for i, c in enumerate(ranked[:10], 1):
                s10  = round(c.score * 10, 2)
                lat_s = f"{c.centroid.lat:.4f}°N" if c.centroid else "—"
                lon_s = f"{c.centroid.lon:.4f}°E" if c.centroid else "—"
                rec  = (
                    "Highly Recommended" if c.score >= 0.8 else
                    "Recommended"        if c.score >= 0.6 else
                    "Not Applicable"
                )
                rec_color = GREEN if c.score >= 0.8 else (AMBER if c.score >= 0.6 else GREY)
                tbl_data.append([
                    str(i),
                    f"{c.score:.4f}",
                    f"{s10}/10",
                    lat_s,
                    lon_s,
                    rec,
                ])
                tbl_styles.append(("TEXTCOLOR", (5, i), (5, i), rec_color))
                tbl_styles.append(("FONT",       (5, i), (5, i), "Helvetica-Bold", 9))

            rec_tbl = Table(
                tbl_data,
                colWidths=[1.2*cm, 2.0*cm, 2.0*cm, 3.0*cm, 3.0*cm, 4.8*cm],
            )
            rec_tbl.setStyle(TableStyle(tbl_styles))
            story.append(rec_tbl)

            if len(ranked) > 10:
                story.append(Spacer(1, 0.1*cm))
                story.append(Paragraph(
                    f"… and {len(ranked) - 10} additional site(s) not shown.",
                    small,
                ))
        else:
            story.append(Paragraph("No candidate sites were identified.", normal))
        story.append(Spacer(1, 0.3*cm))

        # ── AHP weights ──────────────────────────────────────────────────
        story.append(Paragraph("AHP Criteria Weights", h2))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
        story.append(Spacer(1, 0.15*cm))

        ahp_data = [["Criterion", "Weight", "Direction", "Description"]]
        ahp_rows = [
            ("Solar Irradiance (GHI)",    "30%", "Higher = Better", "Global Horizontal Irradiance"),
            ("Terrain Slope",             "22%", "Lower = Better",  "Flat terrain preferred"),
            ("Sunshine Hours",            "18%", "Higher = Better", "Annual sunshine duration"),
            ("Obstacle Density",          "13%", "Lower = Better",  "Detected obstacles (YOLOv8)"),
            ("Surface Temperature (LST)", "10%", "Lower = Better",  "Land Surface Temperature"),
            ("Elevation",                 "7%",  "Moderate = Best", "Terrain elevation"),
        ]
        for row in ahp_rows:
            ahp_data.append(list(row))

        ahp_tbl = Table(ahp_data, colWidths=[5*cm, 1.8*cm, 3.5*cm, 7.7*cm])
        ahp_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), ORANGE_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONT",          (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("FONT",          (0, 1), (-1, -1), "Helvetica", 9),
            ("TEXTCOLOR",     (0, 1), (-1, -1), DARK),
            ("ALIGN",         (1, 0), (1, -1), "CENTER"),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ORANGE_LIGHT]),
        ]))
        story.append(ahp_tbl)
        story.append(Spacer(1, 0.1*cm))
        story.append(Paragraph(
            "Consistency Ratio (CR) = 0.015 — Consistent (CR < 0.10).",
            small,
        ))
        story.append(Spacer(1, 0.3*cm))

        # ── Statistical summary ──────────────────────────────────────────
        if ranked:
            scores = [c.score for c in ranked]
            n = len(scores)
            excellent = sum(1 for s in scores if s > 0.8)
            high      = sum(1 for s in scores if 0.6 < s <= 0.8)
            moderate  = sum(1 for s in scores if 0.4 < s <= 0.6)
            low       = sum(1 for s in scores if s <= 0.4)

            story.append(Paragraph("Statistical Summary", h2))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
            story.append(Spacer(1, 0.15*cm))

            stat_data = [
                ["Total sites evaluated",   str(n),
                 "Highest score",   f"{max(scores)*100:.1f}%"],
                ["Average score",    f"{sum(scores)/n*100:.1f}%",
                 "Lowest score",   f"{min(scores)*100:.1f}%"],
                [f"Highly Suitable (>80%)",  f"{excellent} ({excellent/n*100:.0f}%)",
                 f"Suitable (60–80%)",       f"{high} ({high/n*100:.0f}%)"],
                [f"Moderate (40–60%)",       f"{moderate} ({moderate/n*100:.0f}%)",
                 f"Low (<40%)",              f"{low} ({low/n*100:.0f}%)"],
            ]
            stat_tbl = Table(stat_data, colWidths=[5*cm, 3*cm, 5*cm, 5*cm])
            stat_tbl.setStyle(TableStyle([
                ("FONT",      (0, 0), (-1, -1), "Helvetica", 9),
                ("FONT",      (0, 0), (0, -1),  "Helvetica-Bold", 9),
                ("FONT",      (2, 0), (2, -1),  "Helvetica-Bold", 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
                ("GRID",      (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, ORANGE_LIGHT]),
            ]))
            story.append(stat_tbl)
            story.append(Spacer(1, 0.3*cm))

        # ── Footer ────────────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=1, color=ORANGE_DARK))
        story.append(Spacer(1, 0.1*cm))
        story.append(Paragraph(
            "Danah Alhamdi · Walah Alshwaier · Ruba Aletri · Jumanah Alharbi  —  "
            "CCIS, Princess Nora bint Abdul Rahman University (PNU)  —  "
            "Aligned with Saudi Vision 2030",
            ParagraphStyle("footer", parent=small, alignment=TA_CENTER),
        ))

        doc.build(story)
        return buf.getvalue()

    # ── Private: heatmap image builder ────────────────────────────────────

    def _render_heatmap_image(self, suitability, aoi, ranked):
        """
        Render a PNG for the PDF that matches the Suitability Heatmap page (page 6).
        Uses PIL + requests to fetch Esri satellite tiles as the basemap,
        then draws colored cells and ranked-site pill labels on top — pure PIL,
        no new dependencies beyond what the project already uses.
        Falls back to a plain colored grid if tiles cannot be fetched.
        """
        if suitability is None or not hasattr(suitability, "data"):
            return None

        try:
            import math, io as _io
            import numpy as np
            import requests as _req
            from PIL import Image as PILImage, ImageDraw, ImageFont
            from reportlab.platypus import Image as RLImage
            from reportlab.lib.units import cm

            effective_aoi = aoi if (aoi and len(aoi) == 4) else (0, 0, 1, 1)
            lon_min, lat_min, lon_max, lat_max = effective_aoi

            data   = suitability.data.astype(np.float32)
            nodata = getattr(suitability, "nodata", -9999.0)
            rows, cols = data.shape

            # ── output canvas size ────────────────────────────────────────
            IMG_W, IMG_H = 1200, 680

            # ── coordinate → pixel helpers ────────────────────────────────
            def lon_to_px(lon):
                return int((lon - lon_min) / (lon_max - lon_min) * IMG_W)

            def lat_to_px(lat):
                return int((1 - (lat - lat_min) / (lat_max - lat_min)) * IMG_H)

            # ── same color scale as page 6 ────────────────────────────────
            def _score_rgb(score):
                score = float(max(0.0, min(1.0, score)))
                anchors = [
                    (0.00, (231, 76,  60)),
                    (0.35, (244, 176, 64)),
                    (0.55, (241, 196, 15)),
                    (0.75, (127, 204, 80)),
                    (1.00, (34,  197, 94)),
                ]
                for i in range(len(anchors) - 1):
                    s0, c0 = anchors[i]
                    s1, c1 = anchors[i + 1]
                    if s0 <= score <= s1:
                        t = 0.0 if s1 == s0 else (score - s0) / (s1 - s0)
                        return tuple(int(round(c0[k] + (c1[k] - c0[k]) * t)) for k in range(3))
                return (34, 197, 94)

            # ── fetch Esri satellite tiles ────────────────────────────────
            def _deg2tile(lat, lon, z):
                lr = math.radians(lat)
                n  = 2 ** z
                x  = int((lon + 180) / 360 * n)
                y  = int((1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n)
                return x, y

            def _tile2lon(tx, z):
                return tx / (2 ** z) * 360 - 180

            def _tile2lat(ty, z):
                return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / (2 ** z)))))

            def _fetch_basemap(zoom=11):
                x0, y0 = _deg2tile(lat_max, lon_min, zoom)
                x1, y1 = _deg2tile(lat_min, lon_max, zoom)
                x0, x1 = min(x0, x1), max(x0, x1)
                y0, y1 = min(y0, y1), max(y0, y1)
                TS = 256
                mosaic = PILImage.new("RGB", ((x1-x0+1)*TS, (y1-y0+1)*TS), (210, 180, 140))
                fetched = 0
                hdrs = {"User-Agent": "Mozilla/5.0 WAHHAJ/1.0"}
                for tx in range(x0, x1+1):
                    for ty in range(y0, y1+1):
                        url = (
                            "https://server.arcgisonline.com/ArcGIS/rest/services"
                            f"/World_Imagery/MapServer/tile/{zoom}/{ty}/{tx}"
                        )
                        try:
                            r = _req.get(url, headers=hdrs, timeout=8)
                            if r.status_code == 200:
                                tile = PILImage.open(_io.BytesIO(r.content)).convert("RGB")
                                mosaic.paste(tile, ((tx-x0)*TS, (ty-y0)*TS))
                                fetched += 1
                        except Exception:
                            pass
                if fetched == 0:
                    return None, None, None, None
                # tile extent in degrees
                t_lon_min = _tile2lon(x0,    zoom)
                t_lon_max = _tile2lon(x1+1,  zoom)
                t_lat_max = _tile2lat(y0,    zoom)
                t_lat_min = _tile2lat(y1+1,  zoom)
                # crop and resize to canvas
                def _lon2px_t(lon): return int((lon - t_lon_min) / (t_lon_max - t_lon_min) * mosaic.width)
                def _lat2px_t(lat): return int((1 - (lat - t_lat_min) / (t_lat_max - t_lat_min)) * mosaic.height)
                cx0 = max(0, _lon2px_t(lon_min))
                cy0 = max(0, _lat2px_t(lat_max))
                cx1 = min(mosaic.width,  _lon2px_t(lon_max))
                cy1 = min(mosaic.height, _lat2px_t(lat_min))
                cropped = mosaic.crop((cx0, cy0, cx1, cy1)).resize((IMG_W, IMG_H), PILImage.LANCZOS)
                return cropped, fetched, None, None

            basemap, n_tiles, _, __ = _fetch_basemap(zoom=11)

            # ── build canvas ──────────────────────────────────────────────
            if basemap is not None:
                canvas = basemap.copy()
            else:
                # fallback: sandy desert background matching Esri palette
                canvas = PILImage.new("RGB", (IMG_W, IMG_H), (210, 175, 130))

            draw = ImageDraw.Draw(canvas, "RGBA")

            # ── draw suitability cells ────────────────────────────────────
            lon_step = (lon_max - lon_min) / cols
            lat_step = (lat_max - lat_min) / rows
            CELL_ALPHA = 140  # ~55% opacity like page 6
            for r in range(rows):
                for c in range(cols):
                    sc = float(data[r, c])
                    if not np.isfinite(sc) or sc == nodata:
                        continue

                    # row 0 = north, last row = south
                    cell_lon_min = lon_min + c * lon_step
                    cell_lon_max = cell_lon_min + lon_step

                    cell_lat_max = lat_max - r * lat_step
                    cell_lat_min = cell_lat_max - lat_step

                    # pixel bounds
                    px0 = lon_to_px(cell_lon_min)
                    px1 = lon_to_px(cell_lon_max)
                    py0 = lat_to_px(cell_lat_max)   # top
                    py1 = lat_to_px(cell_lat_min)   # bottom

                    rgb = _score_rgb(sc)
                    fill_rgba = rgb + (CELL_ALPHA,)
                    border_rgba = tuple(int(v * 0.75) for v in rgb) + (200,)
                    draw.rectangle([px0, py0, px1, py1], fill=fill_rgba, outline=border_rgba)

            # ── ranked candidate pill labels ──────────────────────────────
            PILL_BG   = (31, 56, 100, 230)   # dark navy like page 6
            PILL_TEXT = (255, 255, 255, 255)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            except Exception:
                font = ImageFont.load_default()

            if ranked:
                for c_site in ranked[:7]:
                    if not c_site.centroid:
                        continue
                    cx = lon_to_px(c_site.centroid.lon)
                    cy = lat_to_px(c_site.centroid.lat)
                    label = f"#{c_site.rank} \u2014 {c_site.score * 100:.1f}%"
                    # measure text
                    bbox = draw.textbbox((0, 0), label, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    pad_x, pad_y = 14, 8
                    pill_w = tw + pad_x * 2
                    pill_h = th + pad_y * 2
                    pill_x = cx - pill_w - 8   # left of the cell cluster
                    pill_y = cy - pill_h // 2
                    # draw pill
                    draw.rounded_rectangle(
                        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                        radius=pill_h // 2,
                        fill=PILL_BG,
                    )
                    draw.text((pill_x + pad_x, pill_y + pad_y), label, font=font, fill=PILL_TEXT)

            # ── legend bar (bottom-left like page 6) ──────────────────────
            LG_X, LG_Y = 30, IMG_H - 110
            LG_W, LG_H = 200, 14

            draw.rounded_rectangle([LG_X - 10, LG_Y - 35, LG_X + LG_W + 10, LG_Y + LG_H + 35],
                                   radius=10, fill=(255, 255, 255, 220))
            try:
                font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                font_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except Exception:
                font_sm = font_xs = ImageFont.load_default()

            draw.text((LG_X, LG_Y - 28), "Suitability Scale", font=font_sm, fill=(31, 56, 100, 255))
            # gradient bar
            for i in range(LG_W):
                t = i / LG_W
                rgb = _score_rgb(t)
                draw.line([(LG_X + i, LG_Y), (LG_X + i, LG_Y + LG_H)], fill=rgb)
            draw.text((LG_X,          LG_Y + LG_H + 4), "Low",  font=font_xs, fill=(80, 80, 80, 255))
            draw.text((LG_X + LG_W - 20, LG_Y + LG_H + 4), "High", font=font_xs, fill=(80, 80, 80, 255))

            # ── encode to PNG → reportlab Image ──────────────────────────
            buf = _io.BytesIO()
            canvas.save(buf, format="PNG", dpi=(150, 150))
            buf.seek(0)
            return RLImage(buf, width=17 * cm, height=9.5 * cm)

        except Exception as exc:
            logger.warning("Heatmap image generation failed: %s", exc, exc_info=True)
            return None


    # ── Dunder ─────────────────────────────────────────────────────────────

    def __str__(self):
        return (
            f"Report(id={self.report_id}, "
            f"date={self.date.strftime('%Y-%m-%d')}, "
            f"summary='{self.summary[:60]}…')"
        )

    def __repr__(self):
        return (
            f"Report(report_id={self.report_id!r}, "
            f"date={self.date!r}, "
            f"file_path={self.file_path!r})"
        )