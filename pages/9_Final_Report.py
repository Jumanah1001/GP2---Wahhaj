"""
pages/9_Final_Report.py
========================
Generate and download the final solar site suitability analysis report.

Changes vs original
-------------------
- "Start New Analysis" now correctly navigates to pages/3_Choose_Location.py
  (was pages/3_Upload_Image.py — old numbering)
- Adds PDF export using reportlab when available, with a clean .txt fallback
- Resets the full pipeline state on "Start New Analysis"
"""
import streamlit as st
import io
import numpy as np
from datetime import datetime

from ui_helpers import init_state, apply_global_style, render_bg, require_login

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
<h2 style='font-family:Capriola,sans-serif;color:#1a1a1a;margin-bottom:4px;'>Final Report</h2>
<p style='color:#5A5959;font-size:15px;margin-bottom:20px;'>
Summary of the solar site suitability analysis.</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="position:relative;z-index:2;">', unsafe_allow_html=True)

run = st.session_state.get("analysis_run")
if run is None:
    st.warning("No analysis found. Complete the pipeline first.")
    if st.button("← Back to Run Analysis"):
        st.switch_page("pages/6_Run_Analysis.py")
    st.stop()

from Wahhaj.SiteCandidate import SiteCandidate
from Wahhaj.report import Report

ranked  = SiteCandidate.rank_all(list(run.candidates)) if run.candidates else []
summary = run.summary()
aoi     = st.session_state.get("aoi", (0, 0, 0, 0))
now     = datetime.now().strftime("%Y-%m-%d %H:%M")
loc     = st.session_state.get("selected_location", {})

# ── generate report object (once per run) ────────────────────────────────────
if "report_obj" not in st.session_state or st.session_state["report_obj"] is None:
    rpt = Report()
    rpt.generate(run, ranked)
    st.session_state["report_obj"] = rpt

rpt = st.session_state["report_obj"]

# ── report header card ────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style='background:rgba(255,255,255,0.82);border-radius:16px;
         padding:28px 32px;border:1px solid #e0e0e0;
         box-shadow:0 4px 16px rgba(0,0,0,0.06);margin-bottom:20px;'>
    <h3 style='font-family:Capriola,sans-serif;color:#1F3864;margin-bottom:16px;'>
    ☀️ Solar Site Suitability Analysis Report</h3>
    <table style='width:100%;font-size:14px;border-collapse:collapse;'>
      <tr>
        <td style='color:#888;padding:4px 0;'>Generated</td>
        <td style='font-weight:600;'>{now}</td>
        <td style='color:#888;padding:4px 0;'>Run ID</td>
        <td style='font-weight:600;font-family:monospace;'>{run.runId[:16]}…</td>
      </tr>
      <tr>
        <td style='color:#888;padding:4px 0;'>Status</td>
        <td style='font-weight:600;color:green;'>{summary.get("status","—")}</td>
        <td style='color:#888;padding:4px 0;'>Duration</td>
        <td style='font-weight:600;'>{summary.get("durationSec","—")}s</td>
      </tr>
      <tr>
        <td style='color:#888;padding:4px 0;'>Location</td>
        <td style='font-weight:600;'>{loc.get("location_name","—")}</td>
        <td style='color:#888;padding:4px 0;'>AOI</td>
        <td style='font-weight:600;font-family:monospace;font-size:12px;'>
          ({aoi[0]:.3f},{aoi[1]:.3f})→({aoi[2]:.3f},{aoi[3]:.3f})</td>
      </tr>
      <tr>
        <td style='color:#888;padding:4px 0;'>Candidates</td>
        <td style='font-weight:600;'>{len(ranked)}</td>
        <td style='color:#888;padding:4px 0;'>Images</td>
        <td style='font-weight:600;'>
          {1 if st.session_state.get("uploaded_image_name") else 0}</td>
      </tr>
    </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── executive summary ─────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style='background:#1F3864;color:white;border-radius:12px;
         padding:18px 24px;margin-bottom:20px;'>
    <b>Executive Summary</b><br><br>
    <span style='font-size:14px;'>{rpt.summary}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── top 5 sites ───────────────────────────────────────────────────────────────
if ranked:
    st.markdown("### 🏆 Top 5 Sites")
    top5_cols = st.columns(min(5, len(ranked)))
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (col, c) in enumerate(zip(top5_cols, ranked[:5])):
        loc_str = f"{c.centroid.lat:.4f}°N" if c.centroid else "—"
        col.markdown(
            f"""
            <div style='background:rgba(255,255,255,0.78);border-radius:10px;
                 padding:12px;text-align:center;border:1px solid #e0e0e0;'>
            <div style='font-size:22px;'>{medals[i]}</div>
            <div style='font-size:20px;font-weight:800;color:#1F3864;'>{c.score:.3f}</div>
            <div style='font-size:11px;color:#666;'>{loc_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── AHP weights ───────────────────────────────────────────────────────────────
st.markdown("### ⚖️ Criteria Weights Applied")
weights = {
    "GHI": 0.30, "Slope": 0.22, "Sunshine": 0.18,
    "Obstacle": 0.13, "LST": 0.10, "Elevation": 0.07,
}
w_cols = st.columns(len(weights))
colors = ["#4FC3F7", "#91D895", "#F9B233", "#FE753F", "#0066FF", "#4472C4"]
for col, (name, w), clr in zip(w_cols, weights.items(), colors):
    col.markdown(
        f"""
        <div style='background:rgba(255,255,255,0.75);border-radius:8px;
             padding:10px;text-align:center;border-top:4px solid {clr};'>
        <div style='font-size:12px;color:#666;'>{name}</div>
        <div style='font-size:18px;font-weight:800;color:#1F3864;'>{w:.0%}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── suitability stats ─────────────────────────────────────────────────────────
if run.suitability:
    st.markdown("### 📊 Suitability Statistics")
    stats = run.suitability.statistics()
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Min",   f"{stats['min']:.4f}"  if stats["min"]  is not None else "—")
    s2.metric("Max",   f"{stats['max']:.4f}"  if stats["max"]  is not None else "—")
    s3.metric("Mean",  f"{stats['mean']:.4f}" if stats["mean"] is not None else "—")
    s4.metric("Cells", stats["count"])

# ═══════════════════════════════════════════════════════════════════════════
# Export buttons
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("---")

report_text = rpt._generate_report_content(run, ranked)

# ── PDF export (reportlab) or .txt fallback ───────────────────────────────────
def _build_pdf(text_content: str) -> bytes:
    """
    Build a minimal PDF from plain text using reportlab.
    Returns PDF bytes.  Raises ImportError if reportlab is not installed.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    story  = []
    for line in text_content.split("\n"):
        if line.startswith("="):
            story.append(Paragraph(
                f"<b>{line}</b>", styles["Heading2"]
            ))
        elif line.startswith("-"):
            story.append(Paragraph(line, styles["Heading3"]))
        elif line.strip():
            story.append(Paragraph(line, styles["Normal"]))
        else:
            story.append(Spacer(1, 0.3*cm))
    doc.build(story)
    return buf.getvalue()


col_pdf, col_txt = st.columns(2)

with col_pdf:
    try:
        pdf_bytes = _build_pdf(report_text)
        st.download_button(
            "⬇️  Download Report (PDF)",
            data=pdf_bytes,
            file_name=f"wahhaj_report_{run.runId[:8]}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    except ImportError:
        st.info(
            "PDF export requires reportlab: `pip install reportlab`  \n"
            "Use the .txt download below in the meantime."
        )

with col_txt:
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
    # ── FIXED: reset state and navigate to the correct starting page ─────────
    for key in [
        "uploaded_image_name", "uploaded_image_bytes", "uploaded_image_temp_path",
        "aoi", "dataset", "selected_location", "extractor",
        "analysis_run", "report_obj", "ahp_weights_confirmed", "location_saved",
        "analysis_start_date", "analysis_end_date",
    ]:
        st.session_state.pop(key, None)
    # Re-init so defaults are restored
    from ui_helpers import init_state as _init
    _init()
    st.switch_page("pages/3_Choose_Location.py")

if st.button("← Back to Ranked Results"):
    st.switch_page("pages/8_Ranked_Results.py")

st.markdown("</div>", unsafe_allow_html=True)