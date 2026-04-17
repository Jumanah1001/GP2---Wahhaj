"""
pages/8_Final_Report.py
========================
Generate and download the final solar site suitability analysis report.

Changes in this version
-----------------------
1. save_analysis_to_history() called here after generation so the Home page
   history section actually accumulates entries across multiple runs.

2. PDF export now uses Report.build_pdf_bytes() which includes:
   - A rendered matplotlib heatmap image embedded in the PDF
   - Proper reportlab tables for ranked candidates and AHP weights
   - Location information in the header
   The old minimal text-only _build_pdf() is replaced.

3. report.generate() now receives the location dict so the report summary
   includes the location name.

4. Dead navigation links fixed:
   - pages/6_Run_Analysis.py  ->  pages/5_Analysis.py
   - pages/8_Ranked_Results.py -> pages/7_Ranked_Results.py

5. Text color in header table: was color:#888 (weak), now color:#555 on white.
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

top_l, top_r = st.columns([9, 1])
with top_r:
    if st.button("🏠"):
        st.switch_page("pages/2_Home.py")

st.markdown("""
<div style='position:relative;z-index:2;'>
<h2 style='font-family:Capriola,sans-serif;color:#1a1a1a;margin-bottom:4px;'>
Final Report</h2>
<p style='color:#444;font-size:15px;margin-bottom:20px;'>
Summary of the solar site suitability analysis.</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="position:relative;z-index:2;">', unsafe_allow_html=True)

run = st.session_state.get("analysis_run")
if run is None:
    st.warning("No analysis found. Complete the pipeline first.")
    if st.button("← Back to Analysis"):
        # FIX: pages/6_Run_Analysis.py does not exist — correct is pages/5_Analysis.py
        st.switch_page("pages/5_Analysis.py")
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
    # Pass location so report summary includes the location name
    rpt.generate(run, ranked, location=loc)
    rpt._location = loc  # store for _generate_report_content
    st.session_state["report_obj"] = rpt
else:
    rpt = st.session_state["report_obj"]
    if not hasattr(rpt, "_location"):
        rpt._location = loc

# ── save to history (once per run, idempotent) ────────────────────────────
save_analysis_to_history(run, ranked, loc)

# ── report header card ─────────────────────────────────────────────────────
lat_val = loc.get("latitude")
lon_val = loc.get("longitude")
coord_str = (
    f"{lat_val:.4f}°N, {lon_val:.4f}°E"
    if lat_val is not None and lon_val is not None
    else "—"
)

st.markdown(
    f"""
    <div style='background:rgba(255,255,255,0.92);border-radius:16px;
         padding:28px 32px;border:1px solid #dde3ee;
         box-shadow:0 4px 16px rgba(0,0,0,0.06);margin-bottom:20px;'>
    <h3 style='font-family:Capriola,sans-serif;color:#1F3864;margin-bottom:16px;'>
    ☀️ Solar Site Suitability Analysis Report</h3>
    <table style='width:100%;font-size:14px;border-collapse:collapse;'>
      <tr>
        <td style='color:#555;padding:5px 0;font-weight:600;'>Generated</td>
        <td style='font-weight:600;color:#1a1a1a;'>{now}</td>
        <td style='color:#555;padding:5px 0;font-weight:600;'>Run ID</td>
        <td style='font-weight:600;color:#1a1a1a;font-family:monospace;font-size:12px;'>{run.runId[:16]}…</td>
      </tr>
      <tr>
        <td style='color:#555;padding:5px 0;font-weight:600;'>Status</td>
        <td style='font-weight:700;color:#166534;'>{summary.get("status","—")}</td>
        <td style='color:#555;padding:5px 0;font-weight:600;'>Duration</td>
        <td style='font-weight:600;color:#1a1a1a;'>{summary.get("durationSec","—")}s</td>
      </tr>
      <tr>
        <td style='color:#555;padding:5px 0;font-weight:600;'>Location</td>
        <td style='font-weight:700;color:#1a1a1a;'>{loc.get("location_name","—")}</td>
        <td style='color:#555;padding:5px 0;font-weight:600;'>Coordinates</td>
        <td style='font-weight:600;color:#1a1a1a;font-family:monospace;font-size:12px;'>{coord_str}</td>
      </tr>
      <tr>
        <td style='color:#555;padding:5px 0;font-weight:600;'>Candidates</td>
        <td style='font-weight:700;color:#1a1a1a;'>{len(ranked)}</td>
        <td style='color:#555;padding:5px 0;font-weight:600;'>Image</td>
        <td style='font-weight:600;color:#1a1a1a;'>
          {"1 uploaded" if st.session_state.get("uploaded_image_name") else "—"}</td>
      </tr>
    </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── executive summary ──────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style='background:#1F3864;color:white;border-radius:12px;
         padding:18px 24px;margin-bottom:20px;'>
    <b style='color:#e8f0fe;font-size:13px;text-transform:uppercase;
       letter-spacing:.05em;'>Executive Summary</b><br><br>
    <span style='font-size:14px;color:#dce8ff;line-height:1.7;'>{rpt.summary}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── top 5 sites ────────────────────────────────────────────────────────────
if ranked:
    st.markdown("### 🏆 Top 5 Sites")
    top5_cols = st.columns(min(5, len(ranked)))
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (col, c) in enumerate(zip(top5_cols, ranked[:5])):
        lat_s = f"{c.centroid.lat:.4f}°N" if c.centroid else "—"
        lon_s = f"{c.centroid.lon:.4f}°E" if c.centroid else "—"
        rec_clr = (
            "#166534" if c.score >= 0.8 else
            "#713f12" if c.score >= 0.6 else
            "#555"
        )
        col.markdown(
            f"""
            <div style='background:rgba(255,255,255,0.92);border-radius:10px;
                 padding:12px 8px;text-align:center;border:1px solid #dde3ee;'>
            <div style='font-size:22px;'>{medals[i]}</div>
            <div style='font-size:20px;font-weight:800;color:#1F3864;'>
                {c.score * 100:.1f}%</div>
            <div style='font-size:11px;font-weight:700;color:{rec_clr};margin:4px 0;'>
                {"Highly Recommended" if c.score>=0.8 else "Recommended" if c.score>=0.6 else "Review"}</div>
            <div style='font-size:11px;color:#444;'>{lat_s}</div>
            <div style='font-size:11px;color:#444;'>{lon_s}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── AHP weights ────────────────────────────────────────────────────────────
st.markdown("### ⚖️ Criteria Weights Applied")
weights = {
    "GHI": 0.30, "Slope": 0.22, "Sunshine": 0.18,
    "Obstacle": 0.13, "LST": 0.10, "Elevation": 0.07,
}
w_cols  = st.columns(len(weights))
colors  = ["#4FC3F7", "#91D895", "#F9B233", "#FE753F", "#0066FF", "#4472C4"]
for col, (name, w), clr in zip(w_cols, weights.items(), colors):
    col.markdown(
        f"""
        <div style='background:rgba(255,255,255,0.92);border-radius:8px;
             padding:10px;text-align:center;
             border-top:4px solid {clr};border:1px solid #dde3ee;
             border-top:4px solid {clr};'>
        <div style='font-size:12px;color:#333;font-weight:600;'>{name}</div>
        <div style='font-size:18px;font-weight:800;color:#1F3864;'>{w:.0%}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── suitability stats ──────────────────────────────────────────────────────
if run.suitability:
    st.markdown("### 📊 Suitability Statistics")
    stats = run.suitability.statistics()
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Min",   f"{stats['min']:.4f}"  if stats["min"]  is not None else "—")
    s2.metric("Max",   f"{stats['max']:.4f}"  if stats["max"]  is not None else "—")
    s3.metric("Mean",  f"{stats['mean']:.4f}" if stats["mean"] is not None else "—")
    s4.metric("Cells", stats["count"])

# ── heatmap preview ────────────────────────────────────────────────────────
if run.suitability is not None:
    st.markdown("### 🗺️ Suitability Heatmap Preview")
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        data = run.suitability.data.astype(np.float32)
        aoi_t = aoi if aoi and len(aoi) == 4 else (0, 0, 1, 1)
        extent = [aoi_t[0], aoi_t[2], aoi_t[1], aoi_t[3]]

        fig, ax = plt.subplots(figsize=(9, 4))
        im = ax.imshow(
            data, cmap="RdYlGn", vmin=0, vmax=1,
            extent=extent, aspect="auto", origin="lower",
            interpolation="bilinear", alpha=0.90,
        )
        if ranked:
            for c in ranked[:7]:
                if c.centroid:
                    clr = "#2ecc71" if c.score >= 0.7 else "#f1c40f" if c.score >= 0.5 else "#e74c3c"
                    ax.scatter(c.centroid.lon, c.centroid.lat,
                               s=200, c=clr, edgecolors="white", linewidths=1.5, zorder=5)
                    ax.text(c.centroid.lon, c.centroid.lat, str(c.rank),
                            ha="center", va="center", fontsize=8,
                            fontweight="bold", color="white", zorder=6)
        plt.colorbar(im, ax=ax, label="Suitability [0–1]", fraction=0.025, pad=0.02)
        ax.set_xlabel("Longitude", fontsize=9)
        ax.set_ylabel("Latitude",  fontsize=9)
        ax.tick_params(labelsize=8)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()
    except Exception as _e:
        st.caption(f"Heatmap preview unavailable: {_e}")

# ── export ─────────────────────────────────────────────────────────────────
st.markdown("---")

col_pdf, col_txt = st.columns(2)

with col_pdf:
    # Use build_pdf_bytes which includes the heatmap image
    pdf_bytes = rpt.build_pdf_bytes(
        run,
        ranked,
        location   = loc,
        suitability = run.suitability if run else None,
        aoi        = aoi if aoi and len(aoi) == 4 else None,
    )
    if pdf_bytes:
        st.download_button(
            "⬇️  Download Report (PDF)",
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
        "⬇️  Download Report (.txt)",
        data=report_text.encode(),
        file_name=f"wahhaj_report_{run.runId[:8]}.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.markdown("---")
st.success("🎉 Analysis complete! You can start a new analysis from the Choose Location page.")

if st.button("↩️  Start New Analysis", use_container_width=True):
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

# FIX: was pages/8_Ranked_Results.py — does not exist. Correct is pages/7_Ranked_Results.py
if st.button("← Back to Ranked Results"):
    st.switch_page("pages/7_Ranked_Results.py")

st.markdown("</div>", unsafe_allow_html=True)