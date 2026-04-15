"""
pages/6_Run_Analysis.py
========================
Execute the full suitability analysis pipeline via AnalysisRun.

Fix applied
-----------
Readiness check previously used the key "uploaded_images" (a list, set by
the old 3_Upload_Image.py).  The active upload page (4_Upload_Image.py)
sets "uploaded_image_name" (str) and "uploaded_image_bytes" (bytes).

The check now uses:
    bool(st.session_state.get("uploaded_image_name", ""))
which correctly becomes True after the user uploads a file on page 4.
"""
import streamlit as st
import time
from ui_helpers import init_state, apply_global_style, render_bg, require_login

st.set_page_config(page_title="Run Analysis", layout="wide")
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
<h2 style='font-family:Capriola,sans-serif;color:#1a1a1a;margin-bottom:4px;'>Run Analysis</h2>
<p style='color:#5A5959;font-size:15px;margin-bottom:20px;'>
Execute the full suitability analysis pipeline.</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="position:relative;z-index:2;">', unsafe_allow_html=True)

extractor = st.session_state.get("extractor")
dataset   = st.session_state.get("dataset")
aoi       = st.session_state.get("aoi")

# ── readiness check ───────────────────────────────────────────────────────────
# Each tuple: (condition, label, fix_page)
checks = [
    (
        bool(st.session_state.get("uploaded_image_name", "")),
        "Image uploaded",
        "pages/4_Upload_Image.py",
    ),
    (
        aoi is not None,
        "AOI / Location selected",
        "pages/3_Choose_Location.py",
    ),
    (
        extractor is not None,
        "Environmental data fetched",
        "pages/4_Environmental_Data.py",
    ),
    (
        dataset is not None,
        "Dataset ready",
        "pages/3_Choose_Location.py",
    ),
]

ready = True
for ok, label, fix_page in checks:
    icon = "✅" if ok else "❌"
    if ok:
        st.markdown(f"{icon} {label}")
    else:
        col_msg, col_btn = st.columns([4, 1])
        with col_msg:
            st.markdown(f"{icon} **{label}**")
        with col_btn:
            if st.button(f"Fix →", key=f"fix_{label}"):
                st.switch_page(fix_page)
        ready = False

if not ready:
    st.warning("Complete the previous steps before running the analysis.")
    if st.button("← Back to AHP Management"):
        st.switch_page("pages/5_AHP_Management.py")
    st.stop()

st.markdown("---")

# ── run button ────────────────────────────────────────────────────────────────
run_result = st.session_state.get("analysis_run")

if run_result is None:
    st.markdown(
        f"""
        <div style='background:rgba(255,255,255,0.75);border-radius:10px;
             padding:12px 18px;border:1px solid #e0e0e0;font-size:14px;margin-bottom:16px;'>
        <b>Ready to analyse:</b> {st.session_state.get("uploaded_image_name","—")}<br>
        <b>Location:</b>
        {st.session_state.get("selected_location",{}).get("location_name","—")}<br>
        <b>AOI:</b>
        ({aoi[0]:.3f}, {aoi[1]:.3f}) → ({aoi[2]:.3f}, {aoi[3]:.3f})
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🚀 Run Suitability Analysis",
                 use_container_width=True, type="primary"):
        progress = st.progress(0, text="Initialising…")
        status   = st.empty()

        try:
            from Wahhaj.AHPModel import AHPModel
            from Wahhaj.AnalysisRun import AnalysisRun

            progress.progress(10, "Building AHP model…")
            ahp = AHPModel()

            progress.progress(30, "Configuring analysis run…")
            run = AnalysisRun(
                ahp_model        = ahp,
                feature_extractor = extractor,
                top_k_sites      = 10,
                min_site_score   = 0.0,
            )

            progress.progress(50, "Executing pipeline (feature extraction + AHP scoring)…")
            run.execute(dataset)

            progress.progress(90, "Finalising results…")
            time.sleep(0.3)

            st.session_state["analysis_run"] = run
            progress.progress(100, "Done ✓")
            status.success("Analysis completed successfully!")
            st.rerun()

        except Exception as exc:
            progress.empty()
            st.error(f"Analysis failed: {exc}")
            st.exception(exc)

else:
    # ── results summary ───────────────────────────────────────────────────────
    run = run_result
    summary = run.summary()

    st.markdown("### ✅ Analysis Complete")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status",    summary.get("status", "—"))
    col2.metric("Duration",  f"{summary.get('durationSec', 0)}s")
    col3.metric("Candidates", summary.get("candidateCount", 0))
    suit = summary.get("suitability", {})
    col4.metric(
        "Avg Score",
        f"{suit.get('mean', 0):.3f}" if suit.get("mean") else "—"
    )

    if run.candidates:
        st.markdown("#### Top 5 Sites")
        top5 = sorted(run.candidates, key=lambda c: c.score, reverse=True)[:5]
        for i, c in enumerate(top5, 1):
            loc_str = (
                f"({c.centroid.lon:.4f}°E, {c.centroid.lat:.4f}°N)"
                if c.centroid else "—"
            )
            st.markdown(
                f"""
                <div style='background:rgba(255,255,255,0.75);border-radius:8px;
                     padding:8px 14px;margin-bottom:6px;border-left:4px solid #4FC3F7;'>
                <b>#{i}</b> &nbsp;
                Score: <b style='color:#1F3864;'>{c.score:.4f}</b>
                &nbsp;|&nbsp; {loc_str}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Re-run Analysis"):
            st.session_state["analysis_run"] = None
            st.rerun()
    with c2:
        if st.button("Continue to Heatmap →",
                     use_container_width=True, type="primary"):
            st.switch_page("pages/7_Suitability_Heatmap.py")

st.markdown("</div>", unsafe_allow_html=True)