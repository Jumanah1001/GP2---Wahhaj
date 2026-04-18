"""
pages/8_Final_Report.py
========================
Generate and download the final solar site suitability analysis report.

Changes in this version
-----------------------
1. save_analysis_to_history() called here after generation so the Home page
   history section actually accumulates entries across multiple runs.

2. PDF export uses Report.build_pdf_bytes() which includes:
   - A rendered matplotlib heatmap image embedded in the PDF
   - Proper reportlab tables for ranked candidates and AHP weights
   - Location information in the header
   The old minimal text-only _build_pdf() is replaced.

3. report.generate() receives the location dict so the report summary
   includes the location name.

4. Dead navigation links fixed.

5. [UI REDESIGN] Final Report page fully redesigned:
   - All emoji replaced with inline SVG icons (professional look).
   - Every section wrapped in a styled card (white bg, border, shadow).
   - Suitability Statistics section REMOVED.
   - Heatmap section uses the real matplotlib figure (from suitability raster)
     consistent with the Suitability Heatmap page — no placeholder.
   - Top-5 site cards now show a score bar instead of just numbers.
   - Location name always shown in English (from session_state).
   - AHP weights displayed as horizontal bar chart (CSS-only, no extra deps).
"""

import streamlit as st
import io
from datetime import datetime

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    require_login,
    save_analysis_to_history,
)

st.set_page_config(page_title="Final Report", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# ── top-right home button ──────────────────────────────────────────────────
top_l, top_r = st.columns([9, 1])
with top_r:
    if st.button(":material/home:"):
        st.switch_page("pages/2_Home.py")

# ── page-level CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Card wrapper ── */
.rpt-card {
    background: rgba(255,255,255,0.95);
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    position: relative;
    z-index: 2;
}

/* ── Card section title ── */
.rpt-section-title {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 7px;
}

/* ── Meta table inside header card ── */
.rpt-meta-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    font-family: 'Capriola', sans-serif;
}
.rpt-meta-table td { padding: 6px 8px; vertical-align: middle; }
.rpt-meta-table tr:nth-child(odd) { background: #f8fafc; }
.rpt-meta-table .label {
    color: #64748b; font-weight: 600; white-space: nowrap; width: 130px;
}
.rpt-meta-table .value { color: #1a1a1a; font-weight: 600; }
.rpt-meta-table .value.done { color: #166534; }
.rpt-meta-table .value.mono {
    font-family: monospace; font-size: 11px; color: #475569;
}

/* ── Executive summary box ── */
.rpt-exec-summary {
    background: #1F3864; color: #dce8ff; border-radius: 10px;
    padding: 16px 20px; font-family: 'Capriola', sans-serif;
    font-size: 14px; line-height: 1.75;
}

/* ── Top-site highlight banner ── */
.rpt-top-site {
    display: flex; align-items: center; gap: 18px;
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    border: 1.5px solid rgba(217,119,6,0.30); border-radius: 12px;
    padding: 16px 20px; margin-bottom: 18px;
}
.rpt-top-site-icon {
    width: 52px; height: 52px; background: #D97706; border-radius: 12px;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.rpt-top-site-score { margin-left: auto; text-align: right; }
.rpt-top-site-score .big {
    font-size: 34px; font-weight: 800; color: #92400e;
    line-height: 1; font-family: 'Capriola', sans-serif;
}
.rpt-top-site-score .lbl {
    font-size: 11px; color: #78716c; margin-top: 2px;
    font-family: 'Capriola', sans-serif;
}

/* ── Site rank cards ── */
.rpt-site-card {
    background: rgba(255,255,255,0.95); border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 14px 12px; text-align: center;
    font-family: 'Capriola', sans-serif;
}
.rpt-site-card .rank-medal { font-size: 24px; margin-bottom: 4px; }
.rpt-site-card .score-pct {
    font-size: 22px; font-weight: 800; color: #1F3864; line-height: 1;
}
.rpt-site-card .score-bar-wrap { margin: 8px 0 6px; }
.rpt-site-card .score-bar-bg {
    background: #e2e8f0; border-radius: 4px; height: 7px; overflow: hidden;
}
.rpt-site-card .score-bar-fill {
    height: 100%; border-radius: 4px; background: #D97706;
}
.rpt-site-card .rec-badge {
    display: inline-block; font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 5px; margin: 2px 0 6px;
}
.rec-high { background: #dcfce7; color: #166534; }
.rec-med  { background: #dbeafe; color: #1e40af; }
.rec-low  { background: #f3f4f6; color: #4b5563; }
.rpt-site-card .coords { font-size: 10px; color: #64748b; line-height: 1.6; }

/* ── AHP bar rows ── */
.ahp-row {
    display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
    font-family: 'Capriola', sans-serif;
}
.ahp-name { font-size: 12px; font-weight: 600; color: #1a1a1a; min-width: 180px; }
.ahp-bar-bg { flex: 1; background: #f1f5f9; border-radius: 5px; height: 10px; overflow: hidden; }
.ahp-bar-fill { height: 100%; border-radius: 5px; }
.ahp-pct { font-size: 12px; font-weight: 700; color: #475569; min-width: 36px; text-align: right; }
.ahp-dir { font-size: 10px; color: #94a3b8; min-width: 90px; text-align: right; }
.ahp-cr {
    background: #dcfce7; border: 1px solid #bbf7d0; border-radius: 8px;
    padding: 8px 14px; font-size: 12px; font-weight: 600; color: #166534;
    margin-top: 12px; display: inline-flex; align-items: center; gap: 6px;
    font-family: 'Capriola', sans-serif;
}

/* ── Status badge ── */
.rpt-status-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: #dcfce7; color: #166534; border-radius: 8px;
    padding: 5px 12px; font-size: 12px; font-weight: 700;
    font-family: 'Capriola', sans-serif; margin-bottom: 6px;
}
            
</style>
""", unsafe_allow_html=True)

# ── SVG icon helpers ───────────────────────────────────────────────────────
def _icon(path_d, size=15, color="currentColor", sw=2):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{sw}" '
        f'stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">'
        f'{path_d}</svg>'
    )

ICON_REPORT   = _icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>')
ICON_SUN      = _icon('<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>')
ICON_MAP      = _icon('<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>')
ICON_TROPHY   = _icon('<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/>')
ICON_SCALE    = _icon('<line x1="12" y1="3" x2="12" y2="21"/><path d="M3 6l3 12"/><path d="M21 6l-3 12"/><path d="M3 6h18"/><path d="M6 18h12"/>')
ICON_DOWNLOAD = _icon('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>')
ICON_CHECK    = _icon('<polyline points="20 6 9 17 4 12"/>', color="#166534")
ICON_CLOCK    = _icon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')
ICON_PIN      = _icon('<path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z"/><circle cx="12" cy="10" r="3"/>')
ICON_HASH     = _icon('<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>')

# ── guard: need a completed run ────────────────────────────────────────────
run = st.session_state.get("analysis_run")
if run is None:
    st.markdown('<div class="rpt-card">', unsafe_allow_html=True)
    st.warning("No analysis found. Complete the pipeline first.")
    if st.button("← Back to Analysis"):
        st.switch_page("pages/5_Analysis.py")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

from Wahhaj.SiteCandidate import SiteCandidate
from Wahhaj.report import Report

loc     = st.session_state.get("selected_location", {})
ranked  = SiteCandidate.rank_all(list(run.candidates)) if run.candidates else []
summary = run.summary()
aoi     = st.session_state.get("aoi", (0, 0, 0, 0))
now     = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── generate report object (once per run) ─────────────────────────────────
if "report_obj" not in st.session_state or st.session_state["report_obj"] is None:
    rpt = Report()
    rpt.generate(run, ranked, location=loc)
    rpt._location = loc
    st.session_state["report_obj"] = rpt
else:
    rpt = st.session_state["report_obj"]
    if not hasattr(rpt, "_location"):
        rpt._location = loc

save_analysis_to_history(run, ranked, loc)

# ── convenience values ─────────────────────────────────────────────────────
lat_val   = loc.get("latitude")
lon_val   = loc.get("longitude")
coord_str = (
    f"{lat_val:.4f}°N, {lon_val:.4f}°E"
    if lat_val is not None and lon_val is not None
    else "—"
)
loc_name = loc.get("location_name", "—")

# ══════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style='position:relative;z-index:2;display:flex;align-items:center;
     justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:18px;'>
  <div>
    <h2 style='font-family:Capriola,sans-serif;color:#1a1a1a;
               margin-bottom:4px;display:flex;align-items:center;gap:10px;'>
      {ICON_REPORT} &nbsp;Final Report
    </h2>
    <p style='color:#64748b;font-size:13px;margin:0;font-family:Capriola,sans-serif;'>
      {loc_name} &nbsp;&middot;&nbsp; Generated {now}
    </p>
  </div>
  <div class="rpt-status-badge">
    {ICON_CHECK} &nbsp;Analysis Complete
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# CARD 1 — REPORT DETAILS
# ══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="rpt-card">
  <div class="rpt-section-title">{ICON_HASH} &nbsp;Report Details</div>
  <table class="rpt-meta-table">
    <tr>
      <td class="label">{ICON_PIN}&nbsp; Location</td>
      <td class="value">{loc_name}</td>
      <td class="label">{ICON_CLOCK}&nbsp; Generated</td>
      <td class="value">{now}</td>
    </tr>
    <tr>
      <td class="label">Status</td>
      <td class="value done">{summary.get("status","—")}</td>
      <td class="label">Duration</td>
      <td class="value">{summary.get("durationSec","—")} seconds</td>
    </tr>
    <tr>
      <td class="label">Coordinates</td>
      <td class="value mono">{coord_str}</td>
      <td class="label">Candidates</td>
      <td class="value">{len(ranked)} site(s)</td>
    </tr>
    <tr>
      <td class="label">Report ID</td>
      <td class="value mono">{str(rpt.report_id)[:16]}…</td>
      <td class="label">Run ID</td>
      <td class="value mono">{run.runId[:16]}…</td>
    </tr>
  </table>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# CARD 2 — EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="rpt-card">
  <div class="rpt-section-title">{ICON_SUN} &nbsp;Executive Summary</div>
  <div class="rpt-exec-summary">{rpt.summary}</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TOP-SITE BANNER
# ══════════════════════════════════════════════════════════════════════════
if ranked:
    top     = ranked[0]
    top_lat = f"{top.centroid.lat:.4f}°N" if top.centroid else "—"
    top_lon = f"{top.centroid.lon:.4f}°E" if top.centroid else "—"

    st.markdown(f"""
    <div class="rpt-top-site">
      <div class="rpt-top-site-icon">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="white">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
        </svg>
      </div>
      <div style="font-family:'Capriola',sans-serif;">
        <div style="font-size:16px;font-weight:700;color:#1a1a1a;margin-bottom:3px;">
          Top Recommended Site &mdash; Site #{top.rank}
        </div>
        <div style="font-size:12px;color:#78716c;">
          {top_lat}, {top_lon} &nbsp;&middot;&nbsp; Highly Recommended
          &nbsp;&middot;&nbsp; Rank #1 of {len(ranked)}
        </div>
      </div>
      <div class="rpt-top-site-score">
        <div class="big">{top.score*100:.1f}%</div>
        <div class="lbl">Suitability Score</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# CARD 3 — RANKED SITES (top 5)
# ══════════════════════════════════════════════════════════════════════════
if ranked:
    st.markdown(f"""
    <div class="rpt-card" style="padding-bottom:8px;">
      <div class="rpt-section-title">{ICON_TROPHY} &nbsp;Top Ranked Sites</div>
    </div>
    """, unsafe_allow_html=True)

    medals = [
    
    '<span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:linear-gradient(180deg,#FDE68A 0%,#F59E0B 100%);color:#7C2D12;font-weight:700;font-family:Capriola,sans-serif;font-size:15px;box-shadow:0 2px 6px rgba(0,0,0,0.10);">1</span>',
    '<span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:linear-gradient(180deg,#F3F4F6 0%,#9CA3AF 100%);color:#1F2937;font-weight:700;font-family:Capriola,sans-serif;font-size:15px;box-shadow:0 2px 6px rgba(0,0,0,0.10);">2</span>',
    '<span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:linear-gradient(180deg,#FED7AA 0%,#C2410C 100%);color:#7C2D12;font-weight:700;font-family:Capriola,sans-serif;font-size:15px;box-shadow:0 2px 6px rgba(0,0,0,0.10);">3</span>',

]
    cols   = st.columns(min(5, len(ranked)))
    for i, (col, c) in enumerate(zip(cols, ranked[:5])):
        s_pct = c.score * 100
        lat_s = f"{c.centroid.lat:.4f}°N" if c.centroid else "—"
        lon_s = f"{c.centroid.lon:.4f}°E" if c.centroid else "—"
        rec   = "Highly Recommended" if c.score >= 0.8 else "Recommended" if c.score >= 0.6 else "Review"
        r_cls = "rec-high" if c.score >= 0.8 else "rec-med" if c.score >= 0.6 else "rec-low"

        medal_html = (
            f'<div class="rank-medal">{medals[i]}</div>' if i < 3
            else f'<div style="font-size:18px;font-weight:700;color:#64748b;margin-bottom:4px;">#{i+1}</div>'
        )

        col.markdown(f"""
        <div class="rpt-site-card">
          {medal_html}
          <div class="score-pct">{s_pct:.1f}%</div>
          <div class="score-bar-wrap">
            <div class="score-bar-bg">
              <div class="score-bar-fill" style="width:{s_pct:.1f}%;"></div>
            </div>
          </div>
          <span class="rec-badge {r_cls}">{rec}</span>
          <div class="coords">{lat_s}<br>{lon_s}</div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════
# CARD 4 — SUITABILITY HEATMAP (same real Leaflet map as page 6)
# ══════════════════════════════════════════════════════════════════════════
if run.suitability is not None and aoi and len(aoi) == 4:
    # ── reuse the exact same helpers from page 6 ──────────────────────────
    import json as _json
    import numpy as _np
    import streamlit.components.v1 as _components
    from uuid import uuid4 as _uuid4

    def _rpt_interp(v0, v1, t):
        return int(round(v0 + (v1 - v0) * t))

    def _rpt_score_color(score):
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
                return (
                    _rpt_interp(c0[0], c1[0], t),
                    _rpt_interp(c0[1], c1[1], t),
                    _rpt_interp(c0[2], c1[2], t),
                )
        return anchors[-1][1]

    def _rpt_rgb_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _rpt_darken(rgb, f=0.78):
        return tuple(max(0, min(255, int(v * f))) for v in rgb)

    def _rpt_cell_bounds(aoi_, shape_, row_, col_):
        lon_min_, lat_min_, lon_max_, lat_max_ = aoi_
        rows_, cols_ = shape_[:2]
        lon_step = (lon_max_ - lon_min_) / cols_
        lat_step = (lat_max_ - lat_min_) / rows_
        west  = lon_min_ + col_ * lon_step
        east  = west + lon_step
        north = lat_max_ - row_ * lat_step
        south = north - lat_step
        return west, south, east, north

    def _rpt_cell_poly(aoi_, shape_, row_, col_):
        w, s, e, n = _rpt_cell_bounds(aoi_, shape_, row_, col_)
        return [[s, w], [s, e], [n, e], [n, w], [s, w]]

    # Build polygon list from suitability raster
    data_   = run.suitability.data.astype(_np.float32)
    nodata_ = getattr(run.suitability, "nodata", -9999.0)
    rows_, cols_ = data_.shape
    polygons_ = []
    for r_ in range(rows_):
        for c_ in range(cols_):
            sc = float(data_[r_, c_])
            if not _np.isfinite(sc) or sc == nodata_:
                continue
            rgb = _rpt_score_color(sc)
            polygons_.append({
                "score_text": f"{sc*100:.1f}%",
                "suitability": (
                    "Highly Suitable" if sc >= 0.75 else
                    "Suitable"        if sc >= 0.55 else
                    "Moderately Suitable" if sc >= 0.35 else
                    "Not Suitable"
                ),
                "fillColor":   _rpt_rgb_hex(rgb),
                "borderColor": _rpt_rgb_hex(_rpt_darken(rgb)),
                "coords":      _rpt_cell_poly(aoi, data_.shape, r_, c_),
            })

    # Ranked candidate markers
    markers_ = []
    for c in ranked[:7]:
        if c.centroid:
            clr = "#2ecc71" if c.score >= 0.7 else "#f1c40f" if c.score >= 0.5 else "#e74c3c"
            markers_.append({
                "rank": c.rank,
                "lat":  c.centroid.lat,
                "lon":  c.centroid.lon,
                "score_text": f"{c.score*100:.1f}%",
                "color": clr,
            })

    lon_min_, lat_min_, lon_max_, lat_max_ = aoi
    bounds_ = [[lat_min_, lon_min_], [lat_max_, lon_max_]]
    map_id_ = f"rpt_map_{_uuid4().hex}"

    poly_json_    = _json.dumps(polygons_, ensure_ascii=False)
    markers_json_ = _json.dumps(markers_,  ensure_ascii=False)
    bounds_json_  = _json.dumps(bounds_)

    _map_html = f"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body{{margin:0;padding:0;background:transparent;}}
  #{map_id_}{{width:100%;height:480px;border-radius:16px;overflow:hidden;
             box-shadow:inset 0 0 0 1px rgba(255,255,255,.35);}}
  .leaflet-container{{font-family:Arial,sans-serif;background:#eaeaea;}}
  .leaflet-control-attribution{{font-size:10px;}}
  .wh-legend{{background:rgba(255,255,255,.95);border-radius:12px;
              padding:10px 13px;box-shadow:0 4px 16px rgba(0,0,0,.12);min-width:190px;}}
  .wh-legend-title{{font-size:12px;font-weight:700;color:#1f3864;margin-bottom:6px;}}
  .wh-legend-bar{{height:9px;border-radius:999px;
                  background:linear-gradient(90deg,#e74c3c,#f4b040,#f1c40f,#7fcc50,#22c55e);
                  margin-bottom:5px;}}
  .wh-legend-scale{{display:flex;justify-content:space-between;font-size:10px;color:#666;}}
  .rank-icon div{{background:rgba(31,56,100,.92);color:#fff;padding:4px 8px;
                  border-radius:999px;font-size:11px;font-weight:700;
                  white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,.18);}}
</style>
</head><body>
<div id="{map_id_}"></div>
<script>
  const polygons  = {poly_json_};
  const markers   = {markers_json_};
  const bounds    = {bounds_json_};

  const map = L.map("{map_id_}", {{zoomControl:true,scrollWheelZoom:true,preferCanvas:true}});

  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
    {{attribution:"Tiles &copy; Esri",maxZoom:19}});
  const streets = L.tileLayer(
    "https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",
    {{attribution:"&copy; OpenStreetMap contributors",maxZoom:19}});
  satellite.addTo(map);
  L.control.layers({{"Satellite":satellite,"Streets":streets}},null,
    {{collapsed:true,position:"topright"}}).addTo(map);

  polygons.forEach(p => {{
    L.polygon(p.coords,{{
      color:p.borderColor,weight:1.2,fillColor:p.fillColor,fillOpacity:0.52
    }}).bindPopup(
      `<b style="color:#1f3864;">Zone</b><br>
       Score: ${{p.score_text}}<br>
       Suitability: ${{p.suitability}}`
    ).addTo(map);
  }});

  markers.forEach(m => {{
    const ico = L.divIcon({{
      className:"rank-icon",
      html:`<div>#${{m.rank}} — ${{m.score_text}}</div>`,
      iconSize:[90,24],iconAnchor:[45,12]
    }});
    L.circleMarker([m.lat,m.lon],{{
      radius:9,color:"#fff",weight:2.5,fillColor:m.color,fillOpacity:1
    }}).bindPopup(
      `<b style="color:#1f3864;">Site #${{m.rank}}</b><br>Score: ${{m.score_text}}`
    ).addTo(map);
    L.marker([m.lat,m.lon],{{icon:ico}}).addTo(map);
  }});

  map.fitBounds(bounds,{{padding:[24,24]}});

  const legend = L.control({{position:"bottomleft"}});
  legend.onAdd = function(){{
    const d = L.DomUtil.create("div","wh-legend");
    d.innerHTML = `<div class="wh-legend-title">Suitability Scale</div>
      <div class="wh-legend-bar"></div>
      <div class="wh-legend-scale"><span>Low</span><span>High</span></div>`;
    return d;
  }};
  legend.addTo(map);
</script>
</body></html>"""

    st.markdown(f"""
    <div class="rpt-card" style="padding-bottom:8px;">
      <div class="rpt-section-title">{ICON_MAP} &nbsp;Suitability Heatmap</div>
    </div>
    """, unsafe_allow_html=True)
    _components.html(_map_html, height=500, scrolling=False)
    st.caption(
        "Satellite basemap · colored polygons from suitability raster · "
        "numbered markers = ranked candidate sites"
    )

# ══════════════════════════════════════════════════════════════════════════
# CARD 5 — AHP CRITERIA WEIGHTS (CSS bar chart, no extra deps)
# ══════════════════════════════════════════════════════════════════════════
AHP_WEIGHTS = [
    ("Solar Irradiance (GHI)",    0.30, "Higher = Better", "#F59E0B"),
    ("Terrain Slope",             0.22, "Lower = Better",  "#3B82F6"),
    ("Sunshine Hours",            0.18, "Higher = Better", "#EF4444"),
    ("Obstacle Density",          0.13, "Lower = Better",  "#8B5CF6"),
    ("Surface Temperature (LST)", 0.10, "Lower = Better",  "#EC4899"),
    ("Elevation",                 0.07, "Moderate = Best", "#10B981"),
]

rows_html = "".join(
    f"""<div class="ahp-row">
      <div class="ahp-name">{name}</div>
      <div class="ahp-bar-bg">
        <div class="ahp-bar-fill" style="width:{w*100:.0f}%;background:{color};"></div>
      </div>
      <div class="ahp-pct">{w:.0%}</div>
      <div class="ahp-dir">{direction}</div>
    </div>"""
    for name, w, direction, color in AHP_WEIGHTS
)

check_svg = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#166534" '
    'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="20 6 9 17 4 12"/></svg>'
)

st.markdown(f"""
<div class="rpt-card">
  <div class="rpt-section-title">{ICON_SCALE} &nbsp;AHP Criteria Weights</div>
  {rows_html}
  <div class="ahp-cr">
    {check_svg} &nbsp;Consistency Ratio (CR) = 0.015 — Consistent (CR &lt; 0.10)
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# CARD 6 — EXPORT
# ══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="rpt-card" style="padding-bottom:10px;">
  <div class="rpt-section-title">{ICON_DOWNLOAD} &nbsp;Export Report</div>
</div>
""", unsafe_allow_html=True)

col_pdf, col_txt = st.columns(2)

with col_pdf:
    pdf_bytes = rpt.build_pdf_bytes(
        run,
        ranked,
        location    = loc,
        suitability = run.suitability if run else None,
        aoi         = aoi if aoi and len(aoi) == 4 else None,
    )
    if pdf_bytes:
        st.download_button(
            "⬇  Download Report (PDF)",
            data=pdf_bytes,
            file_name=f"wahhaj_report_{run.runId[:8]}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    else:
        st.info(
            "PDF export requires `pip install reportlab matplotlib`.  \n"
            "Use the .txt download below in the meantime."
        )

with col_txt:
    report_text = rpt._generate_report_content(run, ranked)
    st.download_button(
        "⬇  Download Report (.txt)",
        data=report_text.encode(),
        file_name=f"wahhaj_report_{run.runId[:8]}.txt",
        mime="text/plain",
        use_container_width=True,
    )

# ══════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════
st.markdown("<div style='position:relative;z-index:2;margin-top:4px;'>", unsafe_allow_html=True)
st.markdown("---")

st.markdown("""
<div class="rpt-card" style="text-align:center;padding:14px 20px;">
  <p style='font-size:12px;color:#64748b;font-family:Capriola,sans-serif;margin:0;'>
    <strong style='color:#1a1a1a;'>
      Danah Alhamdi &middot; Walah Alshwaier &middot; Ruba Aletri &middot; Jumanah Alharbi
    </strong><br>
    CCIS, Princess Nora bint Abdul Rahman University (PNU) &mdash; Aligned with Saudi Vision 2030
  </p>
</div>
""", unsafe_allow_html=True)

col_new, col_back = st.columns(2)
with col_new:
    if st.button("↩  Start New Analysis", use_container_width=True):
        for key in [
            "uploaded_image_name", "uploaded_image_bytes", "uploaded_image_temp_path",
            "aoi", "dataset", "selected_location", "extractor",
            "analysis_run", "report_obj", "ahp_weights_confirmed", "location_saved",
            "analysis_start_date", "analysis_end_date", "selected_site_analysis",
            "uploaded_images",
        ]:
            st.session_state.pop(key, None)
        from ui_helpers import init_state as _init
        _init()
        st.switch_page("pages/3_Choose_Location.py")

with col_back:
    if st.button("← Back to Ranked Results", use_container_width=True):
        st.switch_page("pages/7_Ranked_Results.py")

st.markdown("</div>", unsafe_allow_html=True)