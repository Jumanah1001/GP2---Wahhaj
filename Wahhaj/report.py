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
import re
import unicodedata
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


def _pdf_safe_text(value, fallback="Selected Site") -> str:
    """Clean dynamic text before it is sent to ReportLab/Helvetica.

    The Streamlit UI can keep Arabic labels normally. This helper is only for
    PDF output, where Arabic/unsupported glyphs otherwise appear as squares.
    It removes Arabic-script runs while preserving English location parts.
    """
    text = str(value or "").strip()
    if not text:
        return fallback
    text = re.sub(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+", " ", text)
    text = (text.replace("’", "'")
                .replace("‘", "'")
                .replace("“", '"')
                .replace("”", '"')
                .replace("—", "-")
                .replace("–", "-"))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,;-\t\n\r")
    return text or fallback


def _as_float(value):
    """Safely convert dynamic coordinate or score values to float."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _format_coords(lat, lon):
    """Format coordinates for PDF without crashing on string values."""
    lat_f = _as_float(lat)
    lon_f = _as_float(lon)
    if lat_f is None or lon_f is None:
        return "—"
    return f"{lat_f:.4f}°N, {lon_f:.4f}°E"


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

    def generate(
        self,
        run,
        ranks: List,
        location: Optional[dict] = None,
        selected_site: Optional[dict] = None,
    ) -> None:
        """
        Build the summary string and set file_path.

        Parameters
        ----------
        run      : AnalysisRun
        ranks    : List[SiteCandidate]  (already ranked)
        location : dict with optional keys "location_name", "latitude", "longitude"
        selected_site : dict with the official selected-site result from page 5
        """
        loc_name = _pdf_safe_text((location or {}).get("location_name"), "Selected Site")
        selected_site = selected_site or {}

        site_score = selected_site.get("score")
        site_label = _pdf_safe_text(selected_site.get("label"), "")

        if site_score is not None:
            try:
                site_score = float(site_score)
            except Exception:
                site_score = None

        if site_score is not None:
            label_sentence = f" and was classified as {site_label}" if site_label else ""
            self.summary = (
                f"The selected site in {loc_name} achieved a suitability score of "
                f"{site_score * 100:.1f}%{label_sentence}. "
                "This result integrates solar availability, environmental conditions, "
                "and terrain characteristics to provide a balanced decision-support "
                "assessment for solar deployment."
            )
        elif ranks:
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
        selected_site: Optional[dict] = None,
        global_ranked_sites: Optional[list] = None,
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
            return self._build_pdf_reportlab(run, ranked, location, suitability, aoi, selected_site, global_ranked_sites)
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
        selected_site: Optional[dict],
        global_ranked_sites: Optional[list] = None,
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

        loc_name = _pdf_safe_text((location or {}).get("location_name"), "Selected Site")
        lat      = (location or {}).get("latitude")
        lon      = (location or {}).get("longitude")
        summary_obj = run.summary()
        global_ranked_sites = list(global_ranked_sites or [])

        selected_site = selected_site or {}
        site_score = selected_site.get("score")
        try:
            site_score_float = float(site_score) if site_score is not None else None
        except Exception:
            site_score_float = None
        site_label = _pdf_safe_text(selected_site.get("label"), "") or "—"
        ai_assessment = _pdf_safe_text(selected_site.get("ai_assessment"), "Pending AI model result")

        current_rank = None
        total_ranked = len(global_ranked_sites)
        run_id = str(getattr(run, "runId", ""))
        for item in global_ranked_sites:
            if str(item.get("run_id")) == run_id:
                current_rank = item.get("rank")
                break

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

        def _p(value, style=normal, fallback="-"):
            # Keep this helper defensive because some calls pass a fallback as
            # the second argument, while others pass a ParagraphStyle.
            # If a plain string is received in the style slot, treat it as
            # fallback text instead of sending it to ReportLab as a style.
            if not hasattr(style, "fontName"):
                fallback = str(style) if style is not None else fallback
                style = normal
            return Paragraph(_pdf_safe_text(value, fallback), style)

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
        coord_str = _format_coords(lat, lon)
        meta_data = [
            [_p("Location", small),  _p(loc_name),              _p("Generated", small), _p(self.date.strftime("%Y-%m-%d %H:%M"))],
            [_p("Status", small),    _p(summary_obj.get("status", "-")),
             _p("Duration", small),  _p(f"{summary_obj.get('durationSec', '-')} seconds")],
            [_p("Saved Sites", small), _p(str(total_ranked)),
             _p("Coordinates", small), _p(coord_str)],
            [_p("Report ID", small),  _p(str(self.report_id)[:16] + "..."),
             _p("Run ID", small), _p(str(run.runId)[:16] + "...")],
        ]
        meta_tbl = Table(meta_data, colWidths=[2.7*cm, 7.1*cm, 2.7*cm, 5.5*cm])
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
        story.append(Paragraph(_pdf_safe_text(self.summary, "Solar site analysis report generated successfully."), sum_style))
        story.append(Spacer(1, 0.3*cm))

        # ── Heatmap image ────────────────────────────────────────────────
        heatmap_img = self._render_heatmap_image(suitability, aoi, location=location, selected_site=selected_site)
        if heatmap_img is not None:
            story.append(Paragraph("Main Site Map", h2))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
            story.append(Spacer(1, 0.15*cm))
            story.append(heatmap_img)
            story.append(Spacer(1, 0.1*cm))
            story.append(Paragraph(
                "This map highlights the selected analysis boundary and the current site marker. "
                "The overlay summarizes the suitability level for the selected site area.",
                small,
            ))
            story.append(Spacer(1, 0.3*cm))

        # ── AI insight ───────────────────────────────────────────────────
        story.append(Paragraph("AI-Based Insight", h2))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(
            "The AI-based assessment is presented as a decision cue that supports the final suitability result. "
            "It should be interpreted together with the weighted GIS/AHP criteria, where solar availability, "
            "environmental conditions, and terrain characteristics are evaluated as one connected decision framework.",
            normal,
        ))
        story.append(Spacer(1, 0.12*cm))
        story.append(Paragraph(f"<b>AI assessment:</b> {ai_assessment}", sum_style))
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

        # ── Global ranked comparison ─────────────────────────────────────
        story.append(Paragraph("Ranked Sites Comparison", h2))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
        story.append(Spacer(1, 0.15*cm))

        if global_ranked_sites:
            rank_sentence = (
                f"This site is ranked <b>#{current_rank} out of {total_ranked}</b> saved evaluated site(s). "
                if current_rank else
                f"This report is compared against {total_ranked} saved evaluated site(s). "
            )
            story.append(Paragraph(
                rank_sentence +
                "The ranking compares completed site analyses using the final selected-site suitability score, "
                "helping the user choose the strongest location rather than reviewing each site in isolation.",
                normal,
            ))
            story.append(Spacer(1, 0.15*cm))

            rank_data = [[_p("Rank", small), _p("Location", small), _p("Score", small), _p("Recommendation", small), _p("Coordinates", small)]]
            rank_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), ORANGE_DARK),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONT",       (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("FONT",       (0, 1), (-1, -1), "Helvetica", 8.5),
                ("TEXTCOLOR",  (0, 1), (-1, -1), DARK),
                ("ALIGN",      (0, 0), (0, -1), "CENTER"),
                ("ALIGN",      (2, 0), (2, -1), "CENTER"),
                ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ORANGE_LIGHT]),
            ]
            for i, item in enumerate(global_ranked_sites[:10], start=1):
                lat_v = item.get("lat")
                lon_v = item.get("lon")
                coords = _format_coords(lat_v, lon_v)
                is_current = str(item.get("run_id")) == run_id
                rank_location = _pdf_safe_text(item.get("location_name"), "Unnamed Site") + (" (Current)" if is_current else "")
                rank_data.append([
                    _p(f"#{item.get('rank', i)}"),
                    _p(rank_location),
                    _p(f"{float(item.get('score', 0.0)) * 100:.1f}%"),
                    _p(item.get("label") or item.get("recommendation"), "-"),
                    _p(coords),
                ])
                if is_current:
                    row = len(rank_data) - 1
                    rank_styles.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#EAF3FF")))
                    rank_styles.append(("FONT", (0, row), (-1, row), "Helvetica-Bold", 8.5))

            rank_tbl = Table(rank_data, colWidths=[1.4*cm, 5.2*cm, 2.1*cm, 4.0*cm, 5.3*cm])
            rank_tbl.setStyle(TableStyle(rank_styles))
            story.append(rank_tbl)
            story.append(Spacer(1, 0.25*cm))

            ranked_map_img = self._render_ranked_sites_map_image(global_ranked_sites, current_run_id=run_id)
            if ranked_map_img is not None:
                story.append(Paragraph("Ranked Sites Map", h2))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d0d0")))
                story.append(Spacer(1, 0.15*cm))
                story.append(ranked_map_img)
                story.append(Spacer(1, 0.1*cm))
                story.append(Paragraph(
                    "This zoomed-out map shows the spatial distribution of saved analysed sites, "
                    "with each marker labeled by its global rank.",
                    small,
                ))
        else:
            story.append(Paragraph(
                "No saved ranked-site comparison is available yet. Complete and save more analyses to enable global ranking.",
                normal,
            ))
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

    def _render_heatmap_image(self, suitability, aoi, location=None, selected_site=None):
        """
        Render a PNG for the PDF that matches the Suitability Heatmap page.
        It keeps the same AOI-centred framing, blue outline, fill behaviour,
        and selected-site marker instead of drawing alternative candidates.
        """
        if suitability is None or not hasattr(suitability, "data"):
            return None

        try:
            import io as _io
            import math
            import numpy as np
            import requests as _req
            from PIL import Image as PILImage, ImageDraw, ImageFont
            from reportlab.platypus import Image as RLImage
            from reportlab.lib.units import cm

            effective_aoi = aoi if (aoi and len(aoi) == 4) else (0, 0, 1, 1)
            lon_min, lat_min, lon_max, lat_max = effective_aoi
            span_lon = max(lon_max - lon_min, 1e-6)
            span_lat = max(lat_max - lat_min, 1e-6)

            # Add padding so the PDF map is readable and not over-zoomed.
            pad_lon = max(span_lon * 0.16, 0.01)
            pad_lat = max(span_lat * 0.16, 0.01)
            view_lon_min = lon_min - pad_lon
            view_lon_max = lon_max + pad_lon
            view_lat_min = lat_min - pad_lat
            view_lat_max = lat_max + pad_lat

            IMG_W, IMG_H = 1400, 820

            def lon_to_px(lon):
                return int((lon - view_lon_min) / (view_lon_max - view_lon_min) * IMG_W)

            def lat_to_px(lat):
                return int((1 - (lat - view_lat_min) / (view_lat_max - view_lat_min)) * IMG_H)

            def _score_rgb(score):
                score = float(max(0.0, min(1.0, score)))
                anchors = [
                    (0.00, (231, 76, 60)),
                    (0.35, (244, 176, 64)),
                    (0.55, (241, 196, 15)),
                    (0.75, (127, 204, 80)),
                    (1.00, (34, 197, 94)),
                ]
                for i in range(len(anchors) - 1):
                    s0, c0 = anchors[i]
                    s1, c1 = anchors[i + 1]
                    if s0 <= score <= s1:
                        t = 0.0 if s1 == s0 else (score - s0) / (s1 - s0)
                        return tuple(int(round(c0[k] + (c1[k] - c0[k]) * t)) for k in range(3))
                return anchors[-1][1]

            def _suitability_badge(score: float) -> str:
                s = float(score) * 100
                if s >= 75:
                    return "Highly Suitable"
                if s >= 55:
                    return "Suitable"
                if s >= 35:
                    return "Moderately Suitable"
                return "Not Suitable"

            def _display_location_name(location_name, lat, lon):
                name = (location_name or "").strip()
                if name and any(ch.isalpha() for ch in name):
                    return _pdf_safe_text(name, "Selected Site")
                if lat is not None and lon is not None:
                    return f"Selected Site ({lat:.4f}, {lon:.4f})"
                return "Selected Site"

            def _resolve_site_score(lat, lon):
                if lat is None or lon is None:
                    return None
                data = suitability.data.astype(np.float32)
                nodata = getattr(suitability, "nodata", -9999.0)
                rows, cols = data.shape
                row = int(round((lat_max - lat) / span_lat * (rows - 1)))
                col = int(round((lon - lon_min) / span_lon * (cols - 1)))
                row = max(0, min(rows - 1, row))
                col = max(0, min(cols - 1, col))
                val = float(data[row, col])
                if not np.isfinite(val) or val == nodata:
                    valid = data[(data != nodata) & np.isfinite(data)]
                    if valid.size == 0:
                        return None
                    return float(np.nanmean(valid))
                return float(val)

            def _deg2tile(lat, lon, z):
                lr = math.radians(lat)
                n = 2 ** z
                x = int((lon + 180) / 360 * n)
                y = int((1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n)
                return x, y

            def _tile2lon(tx, z):
                return tx / (2 ** z) * 360 - 180

            def _tile2lat(ty, z):
                return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / (2 ** z)))))

            def _best_zoom():
                max_span = max(view_lon_max - view_lon_min, view_lat_max - view_lat_min)
                if max_span <= 0.10:
                    return 12
                if max_span <= 0.22:
                    return 11
                if max_span <= 0.40:
                    return 10
                return 9

            def _fetch_basemap(zoom=None):
                if zoom is None:
                    zoom = _best_zoom()
                x0, y0 = _deg2tile(view_lat_max, view_lon_min, zoom)
                x1, y1 = _deg2tile(view_lat_min, view_lon_max, zoom)
                x0, x1 = min(x0, x1), max(x0, x1)
                y0, y1 = min(y0, y1), max(y0, y1)
                TS = 256
                mosaic = PILImage.new("RGB", ((x1 - x0 + 1) * TS, (y1 - y0 + 1) * TS), (214, 190, 160))
                fetched = 0
                hdrs = {"User-Agent": "Mozilla/5.0 WAHHAJ/1.0"}
                for tx in range(x0, x1 + 1):
                    for ty in range(y0, y1 + 1):
                        url = (
                            "https://server.arcgisonline.com/ArcGIS/rest/services"
                            f"/World_Imagery/MapServer/tile/{zoom}/{ty}/{tx}"
                        )
                        try:
                            r = _req.get(url, headers=hdrs, timeout=8)
                            if r.status_code == 200:
                                tile = PILImage.open(_io.BytesIO(r.content)).convert("RGB")
                                mosaic.paste(tile, ((tx - x0) * TS, (ty - y0) * TS))
                                fetched += 1
                        except Exception:
                            pass
                if fetched == 0:
                    return None

                t_lon_min = _tile2lon(x0, zoom)
                t_lon_max = _tile2lon(x1 + 1, zoom)
                t_lat_max = _tile2lat(y0, zoom)
                t_lat_min = _tile2lat(y1 + 1, zoom)

                def _lon2px_t(lon):
                    return int((lon - t_lon_min) / (t_lon_max - t_lon_min) * mosaic.width)

                def _lat2px_t(lat):
                    return int((1 - (lat - t_lat_min) / (t_lat_max - t_lat_min)) * mosaic.height)

                cx0 = max(0, _lon2px_t(view_lon_min))
                cy0 = max(0, _lat2px_t(view_lat_max))
                cx1 = min(mosaic.width, _lon2px_t(view_lon_max))
                cy1 = min(mosaic.height, _lat2px_t(view_lat_min))
                return mosaic.crop((cx0, cy0, cx1, cy1)).resize((IMG_W, IMG_H), PILImage.LANCZOS)

            basemap = _fetch_basemap()
            canvas = basemap.copy() if basemap is not None else PILImage.new("RGB", (IMG_W, IMG_H), (226, 205, 178))
            draw = ImageDraw.Draw(canvas, "RGBA")

            site = selected_site or {}
            site_lat = site.get("latitude", (location or {}).get("latitude"))
            site_lon = site.get("longitude", (location or {}).get("longitude"))
            site_name = _display_location_name(site.get("location_name", (location or {}).get("location_name")), site_lat, site_lon)
            site_score = site.get("score")
            if site_score is None:
                site_score = _resolve_site_score(site_lat, site_lon)
            if site_score is None:
                valid = suitability.data[np.isfinite(suitability.data)]
                site_score = float(np.nanmean(valid)) if getattr(valid, "size", 0) else 0.0

            fill_rgb = _score_rgb(site_score)
            poly = [
                (lon_to_px(lon_min), lat_to_px(lat_max)),
                (lon_to_px(lon_max), lat_to_px(lat_max)),
                (lon_to_px(lon_max), lat_to_px(lat_min)),
                (lon_to_px(lon_min), lat_to_px(lat_min)),
            ]
            data = suitability.data.astype(np.float32)
            nodata = getattr(suitability, "nodata", -9999.0)
            rows, cols = data.shape[:2]

            for r in range(rows):
                for c in range(cols):
                    score = float(data[r, c])

                    if not np.isfinite(score) or score == nodata:
                        continue

                    score = max(0.0, min(1.0, score))
                    cell_rgb = _score_rgb(score)

                    cell_lon_min = lon_min + (c / cols) * span_lon
                    cell_lon_max = lon_min + ((c + 1) / cols) * span_lon
                    cell_lat_max = lat_max - (r / rows) * span_lat
                    cell_lat_min = lat_max - ((r + 1) / rows) * span_lat

                    x0 = lon_to_px(cell_lon_min)
                    y0 = lat_to_px(cell_lat_max)
                    x1 = lon_to_px(cell_lon_max)
                    y1 = lat_to_px(cell_lat_min)

                    draw.rectangle(
                        [x0, y0, x1, y1],
                        fill=cell_rgb + (105,),
                        outline=(74, 143, 42, 130),
                        width=2,
                    )

            draw.line(poly + [poly[0]], fill=(0, 112, 255, 255), width=6)

            if site_lat is not None and site_lon is not None:
                mx = lon_to_px(site_lon)
                my = lat_to_px(site_lat)
                draw.ellipse([mx - 13, my - 13, mx + 13, my + 13], fill=(255,255,255,245), outline=(0, 112, 255, 255), width=5)
                draw.ellipse([mx - 8, my - 8, mx + 8, my + 8], fill=(0, 112, 255, 255))
                try:
                    font_lbl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
                except Exception:
                    font_lbl = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), site_name, font=font_lbl)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                pad_x, pad_y = 16, 10
                pill_w = tw + pad_x * 2
                pill_h = th + pad_y * 2
                pill_x = max(24, min(IMG_W - pill_w - 24, mx - pill_w // 2))
                pill_y = max(24, my - pill_h - 26)
                draw.rounded_rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + pill_h], radius=16, fill=(31, 56, 100, 228))
                draw.text((pill_x + pad_x, pill_y + pad_y - 1), site_name, font=font_lbl, fill=(255, 255, 255, 255))

            LG_X, LG_Y = 30, IMG_H - 132
            LEG_W, LEG_H = 250, 16
            draw.rounded_rectangle([LG_X - 12, LG_Y - 42, LG_X + LEG_W + 12, LG_Y + LEG_H + 74], radius=12, fill=(255,255,255,224))
            try:
                font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                font_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
            except Exception:
                font_sm = font_xs = ImageFont.load_default()
            draw.text((LG_X, LG_Y - 32), "Site Suitability Scale", font=font_sm, fill=(31, 56, 100, 255))
            for i in range(LEG_W):
                t = i / max(1, LEG_W - 1)
                draw.line([(LG_X + i, LG_Y), (LG_X + i, LG_Y + LEG_H)], fill=_score_rgb(t))
            draw.text((LG_X, LG_Y + LEG_H + 6), "Low", font=font_xs, fill=(80,80,80,255))
            draw.text((LG_X + LEG_W - 24, LG_Y + LEG_H + 6), "High", font=font_xs, fill=(80,80,80,255))
            draw.text((LG_X, LG_Y + LEG_H + 28), "Blue outline = selected analysis boundary", font=font_xs, fill=(80,80,80,255))
            draw.text((LG_X, LG_Y + LEG_H + 46), f"Filled area = {_suitability_badge(site_score)}", font=font_xs, fill=(80,80,80,255))
            draw.text((LG_X, LG_Y + LEG_H + 64), "Blue marker = selected site center", font=font_xs, fill=(80,80,80,255))

            buf = _io.BytesIO()
            canvas.save(buf, format="PNG", dpi=(170, 170))
            buf.seek(0)
            return RLImage(buf, width=17 * cm, height=9.9 * cm)

        except Exception as exc:
            logger.warning("Heatmap image generation failed: %s", exc, exc_info=True)
            return None


    def _render_ranked_sites_map_image(self, ranked_sites: list, current_run_id=None):
        """Render a zoomed-out ranked-sites map image for the PDF."""
        if not ranked_sites:
            return None

        try:
            import io as _io
            import math
            from PIL import Image as PILImage, ImageDraw, ImageFont
            from reportlab.platypus import Image as RLImage
            from reportlab.lib.units import cm

            points = []
            bounds = []
            for item in ranked_sites:
                lat = item.get("lat")
                lon = item.get("lon")
                try:
                    lat = float(lat) if lat is not None else None
                    lon = float(lon) if lon is not None else None
                except Exception:
                    lat = lon = None

                aoi = item.get("aoi")
                if isinstance(aoi, (list, tuple)) and len(aoi) == 4:
                    try:
                        lon_min, lat_min, lon_max, lat_max = [float(v) for v in aoi]
                        bounds.extend([(lat_min, lon_min), (lat_max, lon_max)])
                        if lat is None or lon is None:
                            lat = (lat_min + lat_max) / 2
                            lon = (lon_min + lon_max) / 2
                    except Exception:
                        pass

                if lat is not None and lon is not None:
                    bounds.append((lat, lon))
                    copied = dict(item)
                    copied["lat"] = lat
                    copied["lon"] = lon
                    points.append(copied)

            if not points:
                return None

            IMG_W, IMG_H = 1500, 850
            lat_values = [p[0] for p in bounds]
            lon_values = [p[1] for p in bounds]
            lat_min, lat_max = min(lat_values), max(lat_values)
            lon_min, lon_max = min(lon_values), max(lon_values)
            lat_pad = max((lat_max - lat_min) * 0.22, 0.015)
            lon_pad = max((lon_max - lon_min) * 0.22, 0.015)
            view_lat_min = max(-85, lat_min - lat_pad)
            view_lat_max = min(85, lat_max + lat_pad)
            view_lon_min = lon_min - lon_pad
            view_lon_max = lon_max + lon_pad

            def _score_rgb(score):
                try:
                    score = float(score)
                except Exception:
                    score = 0.0
                if score >= 0.80:
                    return (47, 158, 68)
                if score >= 0.60:
                    return (240, 173, 0)
                return (226, 83, 74)

            def lon_to_px(lon):
                return int((lon - view_lon_min) / max(1e-9, view_lon_max - view_lon_min) * IMG_W)

            def lat_to_px(lat):
                return int((view_lat_max - lat) / max(1e-9, view_lat_max - view_lat_min) * IMG_H)

            def _deg2tile(lat, lon, z):
                lat = max(min(lat, 85.0511), -85.0511)
                lr = math.radians(lat)
                n = 2 ** z
                x = int((lon + 180) / 360 * n)
                y = int((1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n)
                return x, y

            def _tile2lon(tx, z):
                return tx / (2 ** z) * 360 - 180

            def _tile2lat(ty, z):
                return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / (2 ** z)))))

            def _best_zoom():
                max_span = max(view_lon_max - view_lon_min, view_lat_max - view_lat_min)
                if max_span <= 0.08:
                    return 13
                if max_span <= 0.18:
                    return 12
                if max_span <= 0.35:
                    return 11
                if max_span <= 0.8:
                    return 10
                return 8

            def _fetch_basemap():
                try:
                    import requests as _req
                    zoom = _best_zoom()
                    x0, y0 = _deg2tile(view_lat_max, view_lon_min, zoom)
                    x1, y1 = _deg2tile(view_lat_min, view_lon_max, zoom)
                    x0, x1 = min(x0, x1), max(x0, x1)
                    y0, y1 = min(y0, y1), max(y0, y1)
                    TS = 256
                    mosaic = PILImage.new("RGB", ((x1 - x0 + 1) * TS, (y1 - y0 + 1) * TS), (226, 226, 226))
                    fetched = 0
                    hdrs = {"User-Agent": "Mozilla/5.0 WAHHAJ/1.0"}
                    for tx in range(x0, x1 + 1):
                        for ty in range(y0, y1 + 1):
                            url = (
                                "https://server.arcgisonline.com/ArcGIS/rest/services"
                                f"/World_Imagery/MapServer/tile/{zoom}/{ty}/{tx}"
                            )
                            try:
                                r = _req.get(url, headers=hdrs, timeout=6)
                                if r.status_code == 200:
                                    tile = PILImage.open(_io.BytesIO(r.content)).convert("RGB")
                                    mosaic.paste(tile, ((tx - x0) * TS, (ty - y0) * TS))
                                    fetched += 1
                            except Exception:
                                pass
                    if fetched == 0:
                        return None
                    t_lon_min = _tile2lon(x0, zoom)
                    t_lon_max = _tile2lon(x1 + 1, zoom)
                    t_lat_max = _tile2lat(y0, zoom)
                    t_lat_min = _tile2lat(y1 + 1, zoom)
                    cx0 = max(0, int((view_lon_min - t_lon_min) / (t_lon_max - t_lon_min) * mosaic.width))
                    cx1 = min(mosaic.width, int((view_lon_max - t_lon_min) / (t_lon_max - t_lon_min) * mosaic.width))
                    cy0 = max(0, int((1 - (view_lat_max - t_lat_min) / (t_lat_max - t_lat_min)) * mosaic.height))
                    cy1 = min(mosaic.height, int((1 - (view_lat_min - t_lat_min) / (t_lat_max - t_lat_min)) * mosaic.height))
                    return mosaic.crop((cx0, cy0, cx1, cy1)).resize((IMG_W, IMG_H), PILImage.LANCZOS)
                except Exception:
                    return None

            canvas = _fetch_basemap()
            if canvas is None:
                canvas = PILImage.new("RGB", (IMG_W, IMG_H), (235, 239, 242))

            draw = ImageDraw.Draw(canvas, "RGBA")
            try:
                font_rank = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
                font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
            except Exception:
                font_rank = font_label = font_small = ImageFont.load_default()

            current_run_id = str(current_run_id) if current_run_id is not None else None
            for item in points[:12]:
                x = lon_to_px(item["lon"])
                y = lat_to_px(item["lat"])
                score = item.get("score", 0.0)
                rgb = _score_rgb(score)
                is_current = current_run_id and str(item.get("run_id")) == current_run_id
                radius = 32 if is_current else 27
                draw.ellipse([x-radius-5, y-radius-5, x+radius+5, y+radius+5], fill=(255,255,255,230))
                draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=rgb + (245,), outline=(255,255,255,255), width=5)
                rank_text = str(item.get("rank", ""))
                bbox = draw.textbbox((0, 0), rank_text, font=font_rank)
                draw.text((x - (bbox[2]-bbox[0])/2, y - (bbox[3]-bbox[1])/2 - 2), rank_text, font=font_rank, fill=(255,255,255,255))

                if is_current:
                    name = str(item.get("location_name") or "Current Site")[:30]
                    label = "Current: #{} · {:.1f}%".format(item.get("rank"), float(score) * 100)
                    pad_x, pad_y = 16, 10
                    bbox1 = draw.textbbox((0,0), name, font=font_label)
                    bbox2 = draw.textbbox((0,0), label, font=font_small)
                    w = max(bbox1[2]-bbox1[0], bbox2[2]-bbox2[0]) + pad_x*2
                    h = (bbox1[3]-bbox1[1]) + (bbox2[3]-bbox2[1]) + pad_y*3
                    lx = max(20, min(IMG_W-w-20, x + 38))
                    ly = max(20, min(IMG_H-h-20, y - h - 28))
                    draw.rounded_rectangle([lx, ly, lx+w, ly+h], radius=18, fill=(31,56,100,232))
                    draw.text((lx+pad_x, ly+pad_y), name, font=font_label, fill=(255,255,255,255))
                    draw.text((lx+pad_x, ly+pad_y+(bbox1[3]-bbox1[1])+8), label, font=font_small, fill=(235,245,255,255))

            lx, ly = 28, IMG_H - 145
            draw.rounded_rectangle([lx, ly, lx+280, ly+118], radius=16, fill=(255,255,255,225))
            draw.text((lx+16, ly+14), "Ranked Sites Map", font=font_label, fill=(31,56,100,255))
            legend = [("High", (47,158,68)), ("Medium", (240,173,0)), ("Low", (226,83,74))]
            for idx, (name, rgb) in enumerate(legend):
                yy = ly + 50 + idx*24
                draw.ellipse([lx+18, yy, lx+34, yy+16], fill=rgb+(255,))
                draw.text((lx+44, yy-2), name, font=font_small, fill=(60,60,60,255))

            buf = _io.BytesIO()
            canvas.save(buf, format="PNG", dpi=(180, 180))
            buf.seek(0)
            return RLImage(buf, width=17 * cm, height=9.6 * cm)

        except Exception as exc:
            logger.warning("Ranked map image generation failed: %s", exc, exc_info=True)
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