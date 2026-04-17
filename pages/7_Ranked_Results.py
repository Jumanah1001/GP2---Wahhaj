"""
pages/7_Ranked_Results.py
==========================
Ranked Site Recommendations.

Changes in this version
-----------------------
1. All 3 dead navigation links fixed:
   - pages/6_Run_Analysis.py   -> pages/5_Analysis.py
   - pages/7_Suitability_Heatmap.py -> pages/6_Suitability_Heatmap.py
   - pages/9_Final_Report.py   -> pages/8_Final_Report.py

2. badge-gray contrast fixed:
   color:#999 on #f3f3f3 (ratio 2.3:1 — WCAG fail) → color:#444 on #ebebeb (ratio 5.9:1 — pass)

3. tbl-header label color: #888 → #444 for better readability.

4. Coordinates now shown with 4 decimal places for precision.

5. Score shown as percentage (e.g. 73.4%) alongside /10 format for clarity.
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
.results-sub { font-size:14px; color:#444; margin-bottom:20px; }

.results-card {
    background:rgba(255,255,255,0.92); border-radius:16px;
    padding:0; box-shadow:0 4px 20px rgba(0,0,0,0.06); overflow:hidden;
    border:1px solid #e4e4e4;
}
.tbl-header {
    display:grid;
    grid-template-columns:36px 60px 140px 140px 140px 170px 36px;
    background:#f4f4f4; padding:10px 20px;
    font-size:12px; font-weight:700; color:#444;
    border-bottom:1px solid #e0e0e0;
    letter-spacing:0.03em;
    text-transform:uppercase;
}
.tbl-row {
    display:grid;
    grid-template-columns:36px 60px 140px 140px 140px 170px 36px;
    padding:12px 20px; font-size:13px; color:#222;
    border-bottom:1px solid #f0f0f0; align-items:center;
}
.tbl-row:hover { background:rgba(0,112,255,0.04); }

.badge { display:inline-block; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-green  { background:#dcfce7; color:#166534; }
.badge-yellow { background:#fef9c3; color:#713f12; }
/* FIX: was color:#999 on #f3f3f3 — contrast 2.3:1. Now color:#444 on #ebebeb — ratio 5.9:1 */
.badge-gray   { background:#ebebeb; color:#444; }

div.stButton > button {
    border-radius:8px !important; font-size:13px !important;
    min-height:36px !important; padding:4px 16px !important;
}
</style>
""", unsafe_allow_html=True)

run = st.session_state.get("analysis_run")
if run is None or not run.candidates:
    st.warning("No ranked results found. Run the analysis first.")
    # FIX: was pages/6_Run_Analysis.py — does not exist
    if st.button("← Back to Analysis"):
        st.switch_page("pages/5_Analysis.py")
    st.stop()

from Wahhaj.SiteCandidate import SiteCandidate
ranked = SiteCandidate.rank_all(list(run.candidates))

st.markdown('<div class="results-wrap">', unsafe_allow_html=True)
st.markdown('<div class="results-title">Ranked Site Recommendations</div>', unsafe_allow_html=True)

loc_name = st.session_state.get("selected_location", {}).get("location_name", "")
st.markdown(
    f'<div class="results-sub">'
    f'Suitability results for <b>{loc_name}</b>' if loc_name else
    f'<div class="results-sub">Suitability analysis results'
    f' — {len(ranked)} candidate site(s) identified.</div>',
    unsafe_allow_html=True,
)

# ── filter controls ──────────────────────────────────────────────────────────
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

# ── card ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="results-card">', unsafe_allow_html=True)

# toolbar
del_col, filt_col, exp_col, add_col = st.columns([1, 1, 1, 1])
with del_col:
    st.button("🗑 Delete")
with filt_col:
    st.button("⚙ Filters")
with exp_col:
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["Rank", "Score (%)", "Score (/10)", "Latitude", "Longitude", "Recommendation"])
    for c in ranked:
        lat = f"{c.centroid.lat:.4f}" if c.centroid else ""
        lon = f"{c.centroid.lon:.4f}" if c.centroid else ""
        s10 = round(c.score * 10, 2)
        pct = f"{c.score * 100:.1f}%"
        rec = (
            "Highly Recommended" if c.score >= 0.8 else
            "Recommended"        if c.score >= 0.6 else
            "Not Applicable"
        )
        w.writerow([c.rank, pct, f"{s10}/10", lat, lon, rec])
    st.download_button(
        "⬇ Export CSV",
        data             = buf.getvalue().encode(),
        file_name        = "ranked_sites.csv",
        mime             = "text/csv",
        use_container_width = True,
    )
with add_col:
    if st.button("＋ Add location", use_container_width=True):
        st.switch_page("pages/3_Choose_Location.py")

# table header
st.markdown("""
<div class="tbl-header">
  <span></span>
  <span>Rank</span>
  <span>Latitude</span>
  <span>Longitude</span>
  <span>Suitability Score</span>
  <span>Recommendation</span>
  <span></span>
</div>""", unsafe_allow_html=True)

# rows
for c in filtered:
    lat  = f"{c.centroid.lat:.4f}°N" if c.centroid else "—"
    lon  = f"{c.centroid.lon:.4f}°E" if c.centroid else "—"
    s10  = round(c.score * 10, 2)
    pct  = f"{c.score * 100:.1f}%"

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
          <span><b>{pct}</b> <span style="color:#888;font-size:11px;">({s10}/10)</span></span>
          <span>{badge}</span>
          <span style="color:#bbb;cursor:pointer;">⋮</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)  # results-card

st.markdown("<br>", unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    # FIX: was pages/7_Suitability_Heatmap.py — does not exist
    if st.button("← Back to Heatmap"):
        st.switch_page("pages/6_Suitability_Heatmap.py")
with c2:
    # FIX: was pages/9_Final_Report.py — does not exist
    if st.button("Continue to Final Report →",
                 type="primary", use_container_width=True):
        st.switch_page("pages/8_Final_Report.py")

st.markdown("</div>", unsafe_allow_html=True)