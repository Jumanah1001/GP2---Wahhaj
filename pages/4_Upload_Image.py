"""
pages/4_Upload_Image.py
========================
Upload UAV image(s) and attach them to the Dataset in session_state.

Key wiring
----------
- Reads  st.session_state["dataset"]  (created by 3_Choose_Location.py)
- Creates UAVImage objects and appends them to dataset.images
- Also keeps st.session_state["uploaded_image_*"] for backwards compat

After upload, "Run Analysis" navigates to 4_Environmental_Data.py.
"""
import os
import tempfile
from html import escape
from textwrap import dedent
from datetime import datetime, timedelta

import streamlit as st

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
    require_login,
    get_dataset,
)

st.set_page_config(page_title="Upload Image", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# Guard: must have a saved location/dataset
if not st.session_state.get("location_saved") or get_dataset() is None:
    st.warning("Please choose and save a location first.")
    if st.button("← Back to Choose Location"):
        st.switch_page("pages/3_Choose_Location.py")
    st.stop()

# ── analysis date range defaults ─────────────────────────────────────────────
if "analysis_start_date" not in st.session_state:
    st.session_state["analysis_start_date"] = datetime.now() - timedelta(days=30)
if "analysis_end_date" not in st.session_state:
    st.session_state["analysis_end_date"] = datetime.now()

st.markdown(
    dedent("""
    <style>
    .upload-page { position:relative; z-index:2; padding-top:22px; }
    .page-title {
        font-family:'Capriola',sans-serif; font-size:clamp(34px,3vw,44px);
        color:#5A5959; line-height:1.05; margin-bottom:16px; text-align:center;
    }
    .page-subtitle {
        font-family:'Capriola',sans-serif; font-size:14px; color:#5E5B5B;
        margin-top:6px; margin-bottom:28px; text-align:center;
    }
    div[data-testid="stFileUploader"] { width:100%; margin-bottom:0 !important; }
    div[data-testid="stFileUploader"] > section {
        border:3px dashed #9ED79D !important; border-radius:18px !important;
        background:rgba(255,255,255,0.08) !important; min-height:380px !important;
        padding:20px !important; box-shadow:none !important;
        position:relative !important; overflow:hidden !important;
    }
    div[data-testid="stFileUploader"] > section > div:not([data-testid="stFileUploaderDropzone"]) {
        display:none !important;
    }
    div[data-testid="stFileUploaderDropzone"] {
        border:none !important; background:transparent !important;
        min-height:320px !important; width:100% !important;
        display:flex !important; align-items:center !important;
        justify-content:center !important; text-align:center !important;
        position:relative !important;
    }
    div[data-testid="stFileUploaderDropzoneInstructions"] {
        width:100% !important; text-align:center !important;
    }
    div[data-testid="stFileUploaderDropzoneInstructions"] > div {
        width:100% !important; display:flex !important; flex-direction:column !important;
        align-items:center !important; justify-content:center !important;
    }
    div[data-testid="stFileUploaderDropzoneInstructions"] span,
    div[data-testid="stFileUploaderDropzoneInstructions"] small { display:none !important; }
    div[data-testid="stFileUploader"] button {
        position:absolute !important; left:50% !important; top:50% !important;
        transform:translate(-50%,-50%) !important; background:#0070FF !important;
        color:white !important; border:none !important; border-radius:6px !important;
        min-height:42px !important; padding:0 22px !important;
        font-family:'Capriola',sans-serif !important; font-size:14px !important;
        box-shadow:4px 5px 4px rgba(0,0,0,0.16) !important; z-index:4 !important;
    }
    div[data-testid="stFileUploader"] button:hover { background:#005fe0 !important; }
    div[data-testid="stFileUploaderFile"],
    div[data-testid="stFileUploader"] ul,
    div[data-testid="stFileUploader"] li,
    div[data-testid="stFileUploader"] [role="list"],
    div[data-testid="stFileUploader"] [role="listitem"] { display:none !important; }
    .upload-note {
        font-family:'Capriola',sans-serif; font-size:13px; color:#777777;
        text-align:center; margin-top:-118px; margin-bottom:108px;
        position:relative; z-index:5;
    }
    .upload-status-inside {
        width:520px; max-width:92%; margin:-250px auto 195px auto;
        background:rgba(255,255,255,0.76); border-radius:18px;
        backdrop-filter:blur(8px); box-shadow:0 8px 24px rgba(0,0,0,0.05);
        padding:14px 18px 14px 18px; position:relative; z-index:6;
    }
    .upload-status-row { display:flex; align-items:center; justify-content:space-between; gap:10px; }
    .upload-file-left  { display:flex; align-items:center; gap:10px; min-width:0; flex:1; }
    .upload-file-icon  { font-size:18px; line-height:1; }
    .upload-file-name  {
        font-family:'Capriola',sans-serif; color:#5A5959; font-size:13px;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }
    .upload-file-close { color:#B2B2B2; font-size:15px; line-height:1; }
    .upload-status-bar { height:4px; background:#D7D7D7; border-radius:999px; overflow:hidden; margin-top:8px; }
    .upload-status-bar-fill { width:100%; height:100%; background:#0070FF; border-radius:999px; }
    .upload-success-line {
        display:flex; align-items:center; justify-content:center;
        gap:8px; margin-top:10px; text-align:center;
    }
    .upload-success-check {
        display:inline-flex; align-items:center; justify-content:center;
        width:18px; height:18px; border-radius:999px; background:#22C55E;
        color:white; font-size:12px; font-weight:700;
    }
    .upload-success-text { font-family:'Capriola',sans-serif; font-size:12px; color:#777777; }
    div.stButton > button {
        background:#0070FF; color:white; border:none; border-radius:6px;
        min-height:44px; font-family:'Capriola',sans-serif; font-size:16px;
        box-shadow:4px 5px 4px rgba(0,0,0,0.16);
    }
    div.stButton > button:hover { background:#005fe0; color:white; }
    div[data-testid="stVerticalBlock"] { gap:0.35rem; }
    </style>
    """),
    unsafe_allow_html=True,
)

render_top_home_button("pages/2_Home.py")

st.markdown('<div class="upload-page">', unsafe_allow_html=True)
st.markdown('<div class="page-title">Upload Image</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Upload a UAV site image to start the analysis</div>',
    unsafe_allow_html=True,
)

# ── show location context ─────────────────────────────────────────────────────
loc = st.session_state.get("selected_location", {})
if loc.get("location_name"):
    aoi = st.session_state.get("aoi")
    aoi_str = (
        f"AOI: ({aoi[0]:.3f}, {aoi[1]:.3f}) → ({aoi[2]:.3f}, {aoi[3]:.3f})"
        if aoi else ""
    )
    st.markdown(
        f"""
        <div style='background:rgba(0,112,255,0.07);border-radius:10px;
             padding:10px 18px;font-size:13px;color:#0050bb;margin-bottom:12px;'>
        📍 Location: <b>{loc['location_name']}</b>
        &nbsp;|&nbsp; {aoi_str}
        </div>
        """,
        unsafe_allow_html=True,
    )

_, center, _ = st.columns([0.8, 8.4, 0.8])

with center:
    uploaded_file = st.file_uploader(
        "Upload site image",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )

    if uploaded_file is None:
        st.markdown(
            '<div class="upload-note">Accepted formats: JPEG / PNG | Max size: 500 MB</div>',
            unsafe_allow_html=True,
        )
    else:
        # ── hide the uploader button after selection ───────────────────────
        st.markdown(
            dedent("""
            <style>
            div[data-testid="stFileUploader"] button { display:none !important; }
            </style>
            """),
            unsafe_allow_html=True,
        )

        file_bytes = uploaded_file.getvalue()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        safe_name = escape(uploaded_file.name)

        # ── persist to session_state ───────────────────────────────────────
        st.session_state["uploaded_image_name"]  = uploaded_file.name
        st.session_state["uploaded_image_bytes"] = file_bytes

        # ── attach UAVImage to Dataset ─────────────────────────────────────
        dataset = get_dataset()
        if dataset is not None:
            try:
                from Wahhaj.UAVImage import UAVImage
                # Write to a temp file so UAVImage has a real path
                suffix = os.path.splitext(uploaded_file.name)[1] or ".png"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                st.session_state["uploaded_image_temp_path"] = tmp_path

                uav = UAVImage(filePath=tmp_path, resolution="unknown")
                # Replace images list with just this upload (single-image workflow)
                dataset.images = [uav]
                # Also set date range on the dataset for ExternalDataSourceAdapter
                dataset.start_date = st.session_state.get(
                    "analysis_start_date", None
                )
                dataset.end_date = st.session_state.get(
                    "analysis_end_date", None
                )
            except Exception as _e:
                # UAVImage creation failure is non-fatal — the image bytes
                # are still in session_state for the rest of the pipeline
                st.caption(f"Note: UAVImage attachment skipped ({_e})")

        # ── upload success card ────────────────────────────────────────────
        st.markdown(
            f"""
            <div class="upload-status-inside">
              <div class="upload-status-row">
                <div class="upload-file-left">
                  <span class="upload-file-icon">📄</span>
                  <span class="upload-file-name">{safe_name}</span>
                </div>
                <span class="upload-file-close">×</span>
              </div>
              <div class="upload-status-bar">
                <div class="upload-status-bar-fill"></div>
              </div>
              <div class="upload-success-line">
                <span class="upload-success-check">✓</span>
                <span class="upload-success-text">
                  Upload completed successfully | {file_size_mb:.2f} MB
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── date range ────────────────────────────────────────────────────
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("**📅 Analysis Date Range** (for environmental data)")
        dc1, dc2 = st.columns(2)
        with dc1:
            start_d = st.date_input(
                "From", value=st.session_state["analysis_start_date"],
                label_visibility="collapsed",
            )
        with dc2:
            end_d = st.date_input(
                "To", value=st.session_state["analysis_end_date"],
                label_visibility="collapsed",
            )
        st.session_state["analysis_start_date"] = datetime.combine(
            start_d, datetime.min.time()
        )
        st.session_state["analysis_end_date"] = datetime.combine(
            end_d, datetime.min.time()
        )
        # Keep dataset in sync
        if dataset:
            dataset.start_date = st.session_state["analysis_start_date"]
            dataset.end_date   = st.session_state["analysis_end_date"]

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ── Run Analysis button ───────────────────────────────────────────
        btn_left, btn_center, btn_right = st.columns([3.2, 1.6, 3.2])
        with btn_center:
            run_clicked = st.button("Run Analysis →", use_container_width=True)

        if run_clicked:
            # ── FIXED: navigate to the active Environmental Data page ─────
            st.switch_page("pages/4_Environmental_Data.py")

st.markdown("</div>", unsafe_allow_html=True)
render_footer()