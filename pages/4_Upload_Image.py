import os
import tempfile
from html import escape
from textwrap import dedent

import streamlit as st
from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
)

st.set_page_config(page_title="Upload Image", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

if "uploaded_image_name" not in st.session_state:
    st.session_state["uploaded_image_name"] = ""

if "uploaded_image_bytes" not in st.session_state:
    st.session_state["uploaded_image_bytes"] = None

if "uploaded_image_temp_path" not in st.session_state:
    st.session_state["uploaded_image_temp_path"] = ""

st.markdown(
    dedent("""
    <style>
    .upload-page {
        position: relative;
        z-index: 2;
        padding-top: 22px;
    }

    .page-title {
        font-family: 'Capriola', sans-serif;
        font-size: clamp(34px, 3vw, 44px);
        color: #5A5959;
        line-height: 1.05;
        margin-bottom: 16px;
        text-align: center;
    }

    .page-subtitle {
        font-family: 'Capriola', sans-serif;
        font-size: 14px;
        color: #5E5B5B;
        margin-top: 6px;
        margin-bottom: 28px;
        text-align: center;
    }

    /* big upload box */
    div[data-testid="stFileUploader"] {
        width: 100%;
        margin-bottom: 0 !important;
    }

    div[data-testid="stFileUploader"] > section {
        border: 3px dashed #9ED79D !important;
        border-radius: 18px !important;
        background: rgba(255,255,255,0.08) !important;
        min-height: 380px !important;
        padding: 20px !important;
        box-shadow: none !important;
        position: relative !important;
        overflow: hidden !important;
    }

    /* hide default selected-file area */
    div[data-testid="stFileUploader"] > section > div:not([data-testid="stFileUploaderDropzone"]) {
        display: none !important;
    }

    /* center content inside box */
    div[data-testid="stFileUploaderDropzone"] {
        border: none !important;
        background: transparent !important;
        min-height: 320px !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        position: relative !important;
    }

    div[data-testid="stFileUploaderDropzoneInstructions"] {
        width: 100% !important;
        text-align: center !important;
    }

    div[data-testid="stFileUploaderDropzoneInstructions"] > div {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* hide streamlit helper text */
    div[data-testid="stFileUploaderDropzoneInstructions"] span,
    div[data-testid="stFileUploaderDropzoneInstructions"] small {
        display: none !important;
    }

    /* center upload button */
    div[data-testid="stFileUploader"] button {
        position: absolute !important;
        left: 50% !important;
        top: 50% !important;
        transform: translate(-50%, -50%) !important;
        background: #0070FF !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        min-height: 42px !important;
        padding: 0 22px !important;
        font-family: 'Capriola', sans-serif !important;
        font-size: 14px !important;
        box-shadow: 4px 5px 4px rgba(0,0,0,0.16) !important;
        z-index: 4 !important;
    }

    div[data-testid="stFileUploader"] button:hover {
        background: #005fe0 !important;
        color: white !important;
    }

    /* extra safety */
    div[data-testid="stFileUploaderFile"],
    div[data-testid="stFileUploader"] ul,
    div[data-testid="stFileUploader"] li,
    div[data-testid="stFileUploader"] [role="list"],
    div[data-testid="stFileUploader"] [role="listitem"] {
        display: none !important;
    }

    /* note under upload button */
    .upload-note {
        font-family: 'Capriola', sans-serif;
        font-size: 13px;
        color: #777777;
        text-align: center;
        margin-top: -118px;
        margin-bottom: 108px;
        position: relative;
        z-index: 5;
    }

    /* uploaded status centered inside the box */
    .upload-status-inside {
        width: 520px;
        max-width: 92%;
        margin: -250px auto 195px auto;
        background: rgba(255,255,255,0.76);
        border-radius: 18px;
        backdrop-filter: blur(8px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.05);
        padding: 14px 18px 14px 18px;
        position: relative;
        z-index: 6;
    }

    .upload-status-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
    }

    .upload-file-left {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
        flex: 1;
    }

    .upload-file-icon {
        font-size: 18px;
        line-height: 1;
    }

    .upload-file-name {
        font-family: 'Capriola', sans-serif;
        color: #5A5959;
        font-size: 13px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .upload-file-close {
        color: #B2B2B2;
        font-size: 15px;
        line-height: 1;
        font-family: 'Capriola', sans-serif;
    }

    .upload-status-bar {
        height: 4px;
        background: #D7D7D7;
        border-radius: 999px;
        overflow: hidden;
        margin-top: 8px;
    }

    .upload-status-bar-fill {
        width: 100%;
        height: 100%;
        background: #0070FF;
        border-radius: 999px;
    }

    .upload-success-line {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        margin-top: 10px;
        text-align: center;
    }

    .upload-success-check {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        border-radius: 999px;
        background: #22C55E;
        color: white;
        font-size: 12px;
        font-family: 'Capriola', sans-serif;
        line-height: 1;
        font-weight: 700;
    }

    .upload-success-text {
        font-family: 'Capriola', sans-serif;
        font-size: 12px;
        color: #777777;
    }

    /* run button */
    div.stButton > button {
        background: #0070FF;
        color: white;
        border: none;
        border-radius: 6px;
        min-height: 44px;
        font-family: 'Capriola', sans-serif;
        font-size: 16px;
        box-shadow: 4px 5px 4px rgba(0,0,0,0.16);
    }

    div.stButton > button:hover {
        background: #005fe0;
        color: white;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0.35rem;
    }
    </style>
    """),
    unsafe_allow_html=True,
)

render_top_home_button("pages/2_Home.py")

st.markdown('<div class="upload-page">', unsafe_allow_html=True)
st.markdown('<div class="page-title">Upload Image</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Upload a site image to start the analysis</div>',
    unsafe_allow_html=True
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
            unsafe_allow_html=True
        )

    else:
        st.markdown(
            dedent("""
            <style>
            div[data-testid="stFileUploader"] button {
                display: none !important;
            }
            </style>
            """),
            unsafe_allow_html=True
        )

        file_bytes = uploaded_file.getvalue()
        st.session_state["uploaded_image_name"] = uploaded_file.name
        st.session_state["uploaded_image_bytes"] = file_bytes

        file_size_mb = len(file_bytes) / (1024 * 1024)
        safe_name = escape(uploaded_file.name)

        status_html = (
            '<div class="upload-status-inside">'
                '<div class="upload-status-row">'
                    '<div class="upload-file-left">'
                        '<span class="upload-file-icon">📄</span>'
                        f'<span class="upload-file-name">{safe_name}</span>'
                    '</div>'
                    '<span class="upload-file-close">×</span>'
                '</div>'
                '<div class="upload-status-bar">'
                    '<div class="upload-status-bar-fill"></div>'
                '</div>'
                '<div class="upload-success-line">'
                    '<span class="upload-success-check">✓</span>'
                    f'<span class="upload-success-text">Upload completed successfully | {file_size_mb:.2f} MB</span>'
                '</div>'
            '</div>'
        )

        st.markdown(status_html, unsafe_allow_html=True)

        btn_left, btn_center, btn_right = st.columns([3.2, 1.6, 3.2])

        with btn_center:
            run_clicked = st.button("Run Analysis", use_container_width=True)

        if run_clicked:
            suffix = os.path.splitext(uploaded_file.name)[1] or ".png"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                st.session_state["uploaded_image_temp_path"] = tmp.name

            st.switch_page("pages/5_Environmental_Data.py")

st.markdown("</div>", unsafe_allow_html=True)

render_footer()