"""
pages/7_Ranked_Results.py
==========================
Ranked Site Recommendations — matches design mockup.

Fixes applied
-------------
- Auth guard replaced with require_login() for clean redirect
- Removed unused `import numpy as np`
- No other logic changes; the table, CSV export, and filter controls
  were already correct
"""
import streamlit as st
import io
import csv

from ui_helpers import init_state, apply_global_style, render_bg, require_login

st.set_page_config(page_title="Ranked Results", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

st.markdown("""
<style>
.results-wrap { position:relative; z-index:2; padding:24px 32px; }
.results-title {
    font-family:'Capriola',sans-serif; font-size:28px;
    font-weight:700; color:#1a1a1a; margin-bottom:4px;
}
.results-sub { font-size:13px; color:#888; margin-bottom:20px; }
.results-card {
    background:rgba(255,255,255,0.82); border-radius:16px;
    padding:0; box-shadow:0 4px 20px rgba(0,0,0,0.06); overflow:hidden;
}
.tbl-header {
    display:grid;
    grid-template-columns:36px 60px 130px 140px 140px 160px 36px;
    background:#f8f8f8; padding:10px 20px;
    font-size:12px; font-weight:600; color:#888;
    border-bottom:1px solid #f0f0f0;
}
.tbl-row {
    display:grid;
    grid-template-columns:36px 60px 130px 140px 140px 160px 36px;
    padding:11px 20px; font-size:13px; color:#333;
    border-bottom:1px solid #f8f8f8; align-items:center;
}
.tbl-row:hover { background:rgba(0,112,255,0.03); }
.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-green  { background:#e6f9ee; color:#1a9e52; }
.badge-yellow { background:#fff8e1; color:#c8841a; }
.badge-gray   { background:#f3f3f3; color:#999; }
div.stButton > button { border-radius:8px !important; font-size:13px !important; min-height:36px !important; padding:4px 16px !important; }
</style>
""", unsafe_allow_html=True)

run = st.session_state.get("analysis_run")
if run is None or not run.candidates:
    st.warning("No ranked results found. Run the analysis first.")
    if st.button("← Back to Run Analysis"):
        st.switch_page("pages/6_Run_Analysis.py")
    st.stop()

from Wahhaj.SiteCandidate import SiteCandidate
ranked = SiteCandidate.rank_all(list(run.candidates))

st.markdown('<div class="results-wrap">', unsafe_allow_html=True)
st.markdown(
    '<div class="results-title">Ranked Site Recommendations</div>',
    unsafe_allow_html=True,
)

loc_name = st.session_state.get("selected_location", {}).get("location_name", "")
st.markdown(
    f'<div class="results-sub">By processing and analysing your uploaded location'
    f'{" — " + loc_name if loc_name else ""}.</div>',
    unsafe_allow_html=True,
)

# ── filter controls ───────────────────────────────────────────────────────────
col_l, col_r = st.columns([3, 2])
with col_l:
    min_score = st.slider(
        "Min suitability score",
        0.0, 1.0, 0.0, 0.01,
        label_visibility="collapsed",
    )
with col_r:
    top_n = st.selectbox(
        "Show top N sites",
        [5, 10, 20, "All"],
        index=1,
        label_visibility="collapsed",
    )

filtered = [c for c in ranked if c.score >= min_score]
if top_n != "All":
    filtered = filtered[: int(top_n)]

# ── card ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="results-card">', unsafe_allow_html=True)

# toolbar
del_col, filt_col, exp_col, add_col = st.columns([1, 1, 1, 1])
with del_col:
    st.button("🗑 Delete")
with filt_col:
    st.button("⚙ Filters")
with exp_col:
    # CSV export
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["Rank", "Suitability Score", "Latitude", "Longitude", "Recommendation"])
    for c in ranked:
        lat   = f"{c.centroid.lat:.4f}" if c.centroid else ""
        lon   = f"{c.centroid.lon:.4f}" if c.centroid else ""
        s10   = round(c.score * 10, 2)
        rec   = (
            "Highly Recommended" if c.score >= 0.8 else
            "Recommended"         if c.score >= 0.6 else
            "Not Applicable"
        )
        w.writerow([c.rank, f"{s10}/10", lat, lon, rec])
    st.download_button(
        "⬇ Export CSV",
        data        = buf.getvalue().encode(),
        file_name   = "ranked_sites.csv",
        mime        = "text/csv",
        use_container_width = True,
    )
with add_col:
    if st.button("＋ Add location", use_container_width=True):
        st.switch_page("pages/3_Choose_Location.py")

# table header
st.markdown("""
<div class="tbl-header">
  <span></span>
  <span>Candidate #</span>
  <span>Latitude</span>
  <span>Longitude</span>
  <span>Suitability Score</span>
  <span>Recommendation</span>
  <span></span>
</div>""", unsafe_allow_html=True)

# rows
for c in filtered:
    lat  = f"{c.centroid.lat:.1f}°N" if c.centroid else "—"
    lon  = f"{c.centroid.lon:.1f}°E" if c.centroid else "—"
    s10  = round(c.score * 10, 2)

    if c.score >= 0.8:
        badge = '<span class="badge badge-green">✦ Highly Recommended</span>'
    elif c.score >= 0.6:
        badge = '<span class="badge badge-yellow">✦ Recommended</span>'
    else:
        badge = '<span class="badge badge-gray">✦ Not Applicable</span>'

    st.markdown(
        f"""
        <div class="tbl-row">
          <span><input type="checkbox"></span>
          <span><b>{c.rank}</b></span>
          <span>{lat}</span>
          <span>{lon}</span>
          <span>{s10}/10</span>
          <span>{badge}</span>
          <span style="color:#aaa;cursor:pointer;">⋮</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)  # results-card

st.markdown("<br>", unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    if st.button("← Back to Heatmap"):
        st.switch_page("pages/7_Suitability_Heatmap.py")
with c2:
    if st.button("Continue to Final Report →",
                 type="primary", use_container_width=True):
        st.switch_page("pages/9_Final_Report.py")

st.markdown("</div>", unsafe_allow_html=True)