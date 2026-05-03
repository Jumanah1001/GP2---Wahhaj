import os
import tempfile
from html import escape
from textwrap import dedent
from uuid import uuid4

import streamlit as st
from ui_helpers import (
    init_state,
    apply_global_style,
    apply_ui_consistency_patch,
    render_bg,
    render_footer,
    render_top_home_button,
    build_image_record,
    clear_analysis_state,
    clear_uploaded_image_state,
    set_dataset_state,
    set_image_records,
)

from Wahhaj.UploadService import UploadService
from Wahhaj.storage_service import StorageService


st.set_page_config(page_title="Upload Image", layout="wide")
init_state()
apply_global_style()

render_bg()

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")


# -----------------------------
# Session state defaults
# -----------------------------
if "uploaded_image_name" not in st.session_state:
    st.session_state["uploaded_image_name"] = ""

if "uploaded_image_bytes" not in st.session_state:
    st.session_state["uploaded_image_bytes"] = None

if "uploaded_image_temp_path" not in st.session_state:
    st.session_state["uploaded_image_temp_path"] = ""

if "uploaded_images" not in st.session_state:
    st.session_state["uploaded_images"] = []

if "upload_ui_signature" not in st.session_state:
    st.session_state["upload_ui_signature"] = ""

if "upload_ui_ready" not in st.session_state:
    st.session_state["upload_ui_ready"] = False

if "upload_uploader_key" not in st.session_state:
    st.session_state["upload_uploader_key"] = 0


def job_is_done(job) -> bool:
    state = getattr(job, "state", None)
    if state is None:
        return False
    state_value = getattr(state, "value", state)
    return str(state_value).lower() == "done"


def _file_signature(uploaded_file, file_bytes: bytes) -> str:
    return f"{uploaded_file.name}|{len(file_bytes)}"


def _render_upload_progress(file_name: str, pct: int, message: str) -> str:
    safe_name = escape(file_name)
    return f"""
    <div class="upload-status-wrap">
        <div class="upload-file-row progress">
            <div class="upload-file-left">
                <span class="upload-file-icon">📄</span>
                <span class="upload-file-name">{safe_name}</span>
            </div>
            <span class="upload-progress-pct">{pct}%</span>
        </div>
        <div class="upload-real-progress">
            <div class="upload-real-progress-fill" style="width:{pct}%;"></div>
        </div>
        <div class="upload-progress-text">{escape(message)}</div>
    </div>
    """


def _render_upload_success(file_name: str, file_size_mb: float) -> str:
    safe_name = escape(file_name)
    return f"""
    <div class="upload-status-wrap done">
        <div class="upload-file-row done">
            <div class="upload-file-left">
                <span class="upload-file-name">{safe_name}</span>
            </div>
            <div class="upload-done-right">
                <span class="upload-success-check">✓</span>
                <span class="upload-success-inline">Uploaded</span>
            </div>
        </div>
        <div class="upload-success-meta">Upload completed successfully • {file_size_mb:.2f} MB</div>
    </div>
    """


def _remove_uploaded_image() -> None:
    clear_uploaded_image_state()
    clear_analysis_state(clear_dataset=False)

    st.session_state["uploaded_image_name"] = ""
    st.session_state["uploaded_image_bytes"] = None
    st.session_state["uploaded_image_temp_path"] = ""
    st.session_state["uploaded_images"] = []
    st.session_state["upload_ui_signature"] = ""
    st.session_state["upload_ui_ready"] = False
    st.session_state["report_obj"] = None
    st.session_state["selected_site_analysis"] = None

    st.session_state["upload_uploader_key"] = int(
        st.session_state.get("upload_uploader_key", 0)
    ) + 1


def _render_clear_image_button() -> bool:
    """Render Clear Image using the same action-button wrapper as Run Analysis."""
    st.markdown(
        '<div class="upload-action-btn-row" data-ready="true">',
        unsafe_allow_html=True,
    )
    clear_clicked = st.button(
        "Clear Image",
        key="clear_image_action",
        help="Remove this image",
        use_container_width=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
    return clear_clicked


# -----------------------------
# Page-specific CSS
# -----------------------------
st.markdown(
    dedent("""
    <style>
    :root {
        --upload-btn-width: 184px;
        --upload-btn-height: var(--wahhaj-button-height, 58px);
        --upload-btn-radius: 14px;
        --upload-btn-font: var(--wahhaj-button-font, 16px);
        --upload-btn-shadow: 0 4px 14px rgba(0,112,255,0.30);
    }

    .main .block-container {
        max-width: 1280px !important;
        padding-top: 1.2rem !important;
        padding-bottom: 1.2rem !important;
    }

    .upload-page {
        position: relative;
        z-index: 2;
        padding-top: 28px;
    }

    /*
       Do not style .page-title or .page-subtitle here.
       They must stay controlled by ui_helpers.py to match all pages.
       This page only controls spacing and upload-box layout.
    */

    .upload-center-shell {
        max-width: 760px;
        margin: 0 auto 0 auto !important;
        position: relative !important;
        z-index: 2 !important;
    }

    div[data-testid="stFileUploader"] {
        width: 100%;
        margin-bottom: 0 !important;
    }

    div[data-testid="stFileUploader"] > section {
        border: 3px dashed #9ED79D !important;
        border-radius: 24px !important;
        background: rgba(255,255,255,0.08) !important;
        min-height: 420px !important;
        padding: 24px !important;
        box-shadow: none !important;
        position: relative !important;
        overflow: hidden !important;
        backdrop-filter: blur(4px);
    }

    div[data-testid="stFileUploader"] > section > div:not([data-testid="stFileUploaderDropzone"]) {
        display: none !important;
    }

    div[data-testid="stFileUploaderDropzone"] {
        border: none !important;
        background: transparent !important;
        min-height: 360px !important;
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

    div[data-testid="stFileUploaderDropzoneInstructions"] span,
    div[data-testid="stFileUploaderDropzoneInstructions"] small {
        display: none !important;
    }

    /* Upload button: icon + text are drawn as one centered group. */
    div[data-testid="stFileUploader"] button,
    div[data-testid="stFileUploader"] section button,
    div[data-testid="stFileUploader"] [role="button"] {
        position: absolute !important;
        left: 50% !important;
        top: 50% !important;
        transform: translate(-50%, -50%) !important;
        background: #0070FF !important;
        background-color: #0070FF !important;
        color: transparent !important;
        border: none !important;
        border-radius: var(--upload-btn-radius) !important;
        min-height: var(--upload-btn-height) !important;
        height: var(--upload-btn-height) !important;
        width: var(--upload-btn-width) !important;
        min-width: var(--upload-btn-width) !important;
        max-width: var(--upload-btn-width) !important;
        padding: 12px 18px !important;
        font-family: 'Capriola', sans-serif !important;
        font-size: 0 !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        box-shadow: var(--upload-btn-shadow) !important;
        z-index: 4 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        column-gap: 8px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        overflow-wrap: normal !important;
    }

    /* Hide Streamlit native children completely to prevent uploadUpload and spacing issues. */
    div[data-testid="stFileUploader"] button > *,
    div[data-testid="stFileUploader"] section button > *,
    div[data-testid="stFileUploader"] [role="button"] > * {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
        height: 0 !important;
        font-size: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        overflow: hidden !important;
    }

    /* Custom centered upload icon. */
    div[data-testid="stFileUploader"] button::before,
    div[data-testid="stFileUploader"] section button::before,
    div[data-testid="stFileUploader"] [role="button"]::before {
        content: "" !important;
        display: inline-block !important;
        width: 18px !important;
        height: 18px !important;
        flex: 0 0 18px !important;
        margin: 0 !important;
        background: #FFFFFF !important;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpath d='M17 8l-5-5-5 5'/%3E%3Cpath d='M12 3v12'/%3E%3C/svg%3E") center / contain no-repeat !important;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpath d='M17 8l-5-5-5 5'/%3E%3Cpath d='M12 3v12'/%3E%3C/svg%3E") center / contain no-repeat !important;
    }

    /* Custom centered Upload text. */
    div[data-testid="stFileUploader"] button::after,
    div[data-testid="stFileUploader"] section button::after,
    div[data-testid="stFileUploader"] [role="button"]::after {
        content: "Upload" !important;
        display: inline-block !important;
        flex: 0 0 auto !important;
        margin: 0 !important;
        padding: 0 !important;
        color: #FFFFFF !important;
        font-family: 'Capriola', sans-serif !important;
        font-size: var(--upload-btn-font) !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        white-space: nowrap !important;
    }
    div[data-testid="stFileUploader"] button:hover,
    div[data-testid="stFileUploader"] section button:hover,
    div[data-testid="stFileUploader"] [role="button"]:hover {
        background: #005fe0 !important;
        background-color: #005fe0 !important;
        color: #FFFFFF !important;
        transform: translate(-50%, -50%) translateY(-1px) !important;
    }

    div[data-testid="stFileUploaderFile"],
    div[data-testid="stFileUploader"] ul,
    div[data-testid="stFileUploader"] li,
    div[data-testid="stFileUploader"] [role="list"],
    div[data-testid="stFileUploader"] [role="listitem"] {
        display: none !important;
    }

    .upload-note {
        font-family: 'Capriola', sans-serif !important;
        font-size: 15px !important;
        color: #777777 !important;
        text-align: center !important;
        margin-top: -122px !important;
        margin-bottom: 112px !important;
        position: relative !important;
        z-index: 5 !important;
        font-weight: 600 !important;
    }

    .upload-status-wrap {
        width: 420px;
        max-width: 90%;
        margin: -222px auto 136px auto;
        background: rgba(255,255,255,0.82);
        border-radius: 20px;
        backdrop-filter: blur(8px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.05);
        padding: 14px 18px 14px 18px;
        position: relative;
        z-index: 6;
        border: 1px solid rgba(224,231,255,0.70);
    }

    .upload-status-wrap.done {
        padding-bottom: 12px;
    }

    .upload-file-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
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
        flex-shrink: 0;
    }

    .upload-file-name {
        font-family: 'Capriola', sans-serif !important;
        color: #41516E !important;
        font-size: 15px !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .upload-progress-pct {
        font-family: 'Capriola', sans-serif !important;
        font-size: 15px !important;
        color: #365277 !important;
        font-weight: 700;
        flex-shrink: 0;
    }

    .upload-real-progress {
        margin-top: 10px;
        height: 7px;
        border-radius: 999px;
        background: #DDE5F0;
        overflow: hidden;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.06);
    }

    .upload-real-progress-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #003CAA 0%, #0070FF 28%, #38B6FF 58%, #0070FF 82%, #003CAA 100%);
        background-size: 300% 100%;
        animation: uploadShimmer 2s linear infinite;
        transition: width .5s ease;
    }

    @keyframes uploadShimmer {
        0% { background-position: 200% center; }
        100% { background-position: -200% center; }
    }

    .upload-progress-text {
        margin-top: 10px;
        font-family: 'Capriola', sans-serif !important;
        font-size: 14px !important;
        color: #6B7280 !important;
        text-align: center;
    }

    .upload-done-right {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
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
        font-size: 13px;
        font-family: 'Capriola', sans-serif;
        line-height: 1;
        font-weight: 700;
    }

    .upload-success-inline {
        font-family: 'Capriola', sans-serif;
        font-size: 14px;
        color: #22A352;
        font-weight: 700;
    }

    .upload-success-meta {
        margin-top: 10px;
        font-family: 'Capriola', sans-serif !important;
        font-size: 14px !important;
        color: #777777 !important;
        text-align: center;
    }

    .upload-action-btn-row {
        width: 100% !important;
        margin: 8px 0 0 0 !important;
    }

    .upload-action-btn-row div.stButton,
    .upload-action-btn-row [data-testid="stButton"],
    .upload-action-btn-row [data-testid="stButton"] > div {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
    }

    .upload-action-btn-row div.stButton > button,
    .upload-action-btn-row [data-testid="stButton"] button,
    .upload-action-btn-row div.stButton > button:focus,
    .upload-action-btn-row div.stButton > button:active {
        background: var(--wahhaj-blue, #0070FF) !important;
        background-color: var(--wahhaj-blue, #0070FF) !important;
        color: #FFFFFF !important;
        border: 1px solid var(--wahhaj-blue, #0070FF) !important;
        border-radius: var(--upload-btn-radius) !important;

        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;

        min-height: var(--upload-btn-height) !important;
        height: var(--upload-btn-height) !important;
        max-height: var(--upload-btn-height) !important;

        padding: 13px 24px !important;
        font-family: var(--wahhaj-font, 'Capriola', sans-serif) !important;
        font-size: var(--upload-btn-font) !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        letter-spacing: 0.02em !important;

        box-shadow: 0 4px 16px rgba(0,112,255,0.30), 0 2px 6px rgba(0,0,0,0.08) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        white-space: nowrap !important;
        box-sizing: border-box !important;
        opacity: 1 !important;
        margin: 0 !important;
    }

    .upload-action-btn-row div.stButton > button p,
    .upload-action-btn-row div.stButton > button > div {
        font-family: var(--wahhaj-font, 'Capriola', sans-serif) !important;
        font-size: var(--upload-btn-font) !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        margin: 0 !important;
        padding: 0 !important;
        color: inherit !important;
        text-align: center !important;
    }

    .upload-action-btn-row div.stButton > button:hover {
        background: var(--wahhaj-blue-hover, #005fe0) !important;
        background-color: var(--wahhaj-blue-hover, #005fe0) !important;
        border-color: var(--wahhaj-blue-hover, #005fe0) !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 22px rgba(0,112,255,0.42), 0 2px 8px rgba(0,0,0,0.10) !important;
    }

    .upload-action-btn-row div.stButton > button:disabled,
    .upload-action-btn-row div.stButton > button[disabled] {
        background: #d0d0d0 !important;
        background-color: #d0d0d0 !important;
        color: #888888 !important;
        border: 1px solid #bbbbbb !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
        opacity: 1 !important;
        transform: none !important;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0.35rem;
    }

    @media (max-width: 900px) {
        .upload-center-shell {
            max-width: 94%;
            margin-top: 18px;
        }

        div[data-testid="stFileUploader"] > section {
            min-height: 340px !important;
        }

        div[data-testid="stFileUploaderDropzone"] {
            min-height: 280px !important;
        }

        .upload-status-wrap {
            width: 92%;
            margin: -188px auto 110px auto;
        }
    }
    </style>
    """),
    unsafe_allow_html=True,
)


# Apply the shared UI system after the page CSS.
# Page title/subtitle are not styled locally, so they now match the rest of WAHHAJ.
apply_ui_consistency_patch()


# -----------------------------
# Small JS enforcement for stable button styling
# -----------------------------
st.markdown(
    """
    <script>
    (function applyStableUploadStyles() {
        const BTN_H   = "58px";
        const BTN_W   = "184px";
        const BTN_R   = "14px";
        const BTN_FS  = "16px";
        const BTN_SH  = "0 4px 16px rgba(0,112,255,0.30), 0 2px 6px rgba(0,0,0,0.08)";
        const BTN_PAD = "13px 24px";

        function forceBlueButton(btn, fullWidth) {
            btn.style.setProperty("appearance", "none", "important");
            btn.style.setProperty("background", "#0070FF", "important");
            btn.style.setProperty("background-color", "#0070FF", "important");
            btn.style.setProperty("color", "#FFFFFF", "important");
            btn.style.setProperty("border", "1px solid #0070FF", "important");
            btn.style.setProperty("border-radius", BTN_R, "important");

            if (fullWidth) {
                btn.style.setProperty("width", "100%", "important");
                btn.style.setProperty("min-width", "100%", "important");
                btn.style.setProperty("max-width", "100%", "important");
            } else {
                btn.style.setProperty("width", BTN_W, "important");
                btn.style.setProperty("min-width", BTN_W, "important");
                btn.style.setProperty("max-width", BTN_W, "important");
            }

            btn.style.setProperty("height", BTN_H, "important");
            btn.style.setProperty("min-height", BTN_H, "important");
            btn.style.setProperty("padding", BTN_PAD, "important");
            btn.style.setProperty("font-family", "'Capriola', sans-serif", "important");
            btn.style.setProperty("font-size", BTN_FS, "important");
            btn.style.setProperty("font-weight", "800", "important");
            btn.style.setProperty("line-height", "1.25", "important");
            btn.style.setProperty("box-shadow", BTN_SH, "important");
            btn.style.setProperty("display", "inline-flex", "important");
            btn.style.setProperty("align-items", "center", "important");
            btn.style.setProperty("justify-content", "center", "important");
            btn.style.setProperty("gap", "8px", "important");
            btn.style.setProperty("column-gap", "8px", "important");
            btn.style.setProperty("white-space", "nowrap", "important");
            btn.style.setProperty("opacity", "1", "important");
        }

        function forceUploaderButton(btn) {
            forceBlueButton(btn, false);
            btn.style.setProperty("color", "transparent", "important");
            btn.style.setProperty("font-size", "0", "important");
            btn.setAttribute("aria-label", "Upload");
            Array.from(btn.children).forEach(el => {
                el.style.setProperty("display", "none", "important");
                el.style.setProperty("width", "0", "important");
                el.style.setProperty("min-width", "0", "important");
                el.style.setProperty("max-width", "0", "important");
                el.style.setProperty("height", "0", "important");
                el.style.setProperty("font-size", "0", "important");
                el.style.setProperty("margin", "0", "important");
                el.style.setProperty("padding", "0", "important");
                el.style.setProperty("opacity", "0", "important");
                el.style.setProperty("overflow", "hidden", "important");
            });
        }

        function hideNativeUploaderIcon(btn) {
            forceUploaderButton(btn);
        }

        function forceDisabledButton(btn) {
            btn.style.setProperty("background", "#d0d0d0", "important");
            btn.style.setProperty("background-color", "#d0d0d0", "important");
            btn.style.setProperty("color", "#888", "important");
            btn.style.setProperty("border", "1px solid #bbb", "important");
            btn.style.setProperty("box-shadow", "none", "important");
            btn.style.setProperty("cursor", "not-allowed", "important");
            btn.style.setProperty("opacity", "1", "important");
            btn.style.setProperty("transform", "none", "important");
        }

        function run() {
            document.querySelectorAll(".top-home-btn button").forEach(btn => {
                forceBlueButton(btn, false);
            });

            document.querySelectorAll('[data-testid="stFileUploader"] button').forEach(btn => {
                forceUploaderButton(btn);
            });

            document.querySelectorAll(".upload-action-btn-row button").forEach(btn => {
                const forceReady = btn.closest("[data-ready='true']") !== null;
                const isDisabled = !forceReady && (
                    btn.disabled ||
                    btn.hasAttribute("disabled") ||
                    btn.getAttribute("aria-disabled") === "true" ||
                    btn.closest("[data-ready='false']") !== null
                );

                if (isDisabled) {
                    forceDisabledButton(btn);
                } else {
                    forceBlueButton(btn, true);
                }
            });

            document.querySelectorAll("button").forEach(btn => {
                const label = (btn.innerText || btn.textContent || "").trim();

                if (label === "Clear Image") {
                    forceBlueButton(btn, true);
                }
            });
        }

        const obs = new MutationObserver(run);
        obs.observe(document.body, { childList: true, subtree: true });

        run();
        setTimeout(run, 100);
        setTimeout(run, 300);
        setTimeout(run, 700);
        setTimeout(run, 1500);
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

# Final Upload page protection:
# - title/subtitle font comes from ui_helpers.py
# - this block only adds spacing so the dashed upload border cannot collide with the subtitle
# - it also protects the custom Upload button icon/text alignment
st.markdown(
    """
    <style>
    .upload-heading-block {
        width: 100% !important;
        text-align: center !important;
        position: relative !important;
        z-index: 5 !important;
        margin: 0 auto 42px auto !important;
        padding: 0 !important;
    }

    .upload-heading-block .page-title {
        margin: 0 0 8px 0 !important;
        padding: 0 !important;
        line-height: 1.10 !important;
    }

    .upload-heading-block .page-subtitle {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.45 !important;
    }

    .upload-center-shell {
        margin-top: 0 !important;
    }

    div[data-testid="stFileUploader"] button,
    div[data-testid="stFileUploader"] section button,
    div[data-testid="stFileUploader"] [role="button"] {
        width: var(--upload-btn-width) !important;
        min-width: var(--upload-btn-width) !important;
        max-width: var(--upload-btn-width) !important;
        height: var(--upload-btn-height) !important;
        min-height: var(--upload-btn-height) !important;
        padding: 12px 18px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        column-gap: 8px !important;
        color: transparent !important;
        font-size: 0 !important;
        background: var(--wahhaj-blue, #0070FF) !important;
        background-color: var(--wahhaj-blue, #0070FF) !important;
    }

    div[data-testid="stFileUploader"] button::before,
    div[data-testid="stFileUploader"] section button::before,
    div[data-testid="stFileUploader"] [role="button"]::before {
        width: 18px !important;
        height: 18px !important;
        flex: 0 0 18px !important;
        margin: 0 !important;
    }

    div[data-testid="stFileUploader"] button::after,
    div[data-testid="stFileUploader"] section button::after,
    div[data-testid="stFileUploader"] [role="button"]::after {
        content: "Upload" !important;
        color: #FFFFFF !important;
        font-family: var(--wahhaj-font, 'Capriola', sans-serif) !important;
        font-size: var(--upload-btn-font, 16px) !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        white-space: nowrap !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


render_top_home_button("pages/2_Home.py")

st.markdown('<div class="upload-page">', unsafe_allow_html=True)
st.markdown(
    '''
    <div class="upload-heading-block">
        <div class="page-title upload-page-title">Upload Image</div>
        <div class="page-subtitle upload-page-subtitle">Upload a site image to start the analysis</div>
    </div>
    ''',
    unsafe_allow_html=True,
)

left_sp, center, right_sp = st.columns([2.0, 3.8, 2.0])

with center:
    st.markdown('<div class="upload-center-shell">', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload site image",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        key=f"upload_image_file_{st.session_state['upload_uploader_key']}",
    )

    if uploaded_file is None:
        st.session_state["upload_ui_signature"] = ""
        st.session_state["upload_ui_ready"] = False

        st.markdown(
            '<div class="upload-note">Accepted formats: JPEG / PNG | Max size: 500 MB</div>',
            unsafe_allow_html=True
        )

    else:
        st.markdown(
            dedent("""
            <style>
            div[data-testid="stFileUploader"] button,
            div[data-testid="stFileUploader"] section button,
            div[data-testid="stFileUploader"] [role="button"] {
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
        file_sig = _file_signature(uploaded_file, file_bytes)

        if st.session_state.get("upload_ui_signature") != file_sig:
            st.session_state["upload_ui_signature"] = file_sig
            st.session_state["upload_ui_ready"] = False

        progress_slot = st.empty()

        if not st.session_state.get("upload_ui_ready", False):
            progress_slot.markdown(
                _render_upload_success(uploaded_file.name, file_size_mb),
                unsafe_allow_html=True,
            )

            st.session_state["upload_ui_ready"] = True
            st.rerun()

        else:
            progress_slot.markdown(
                _render_upload_success(uploaded_file.name, file_size_mb),
                unsafe_allow_html=True,
            )

        is_ready = st.session_state.get("upload_ui_ready", False)
        _gap1, _btn_col, _gap2 = st.columns([1.5, 1.5, 1.5])

        with _btn_col:
            if st.session_state.get("upload_ui_ready", False):
                clear_clicked = _render_clear_image_button()
                if clear_clicked:
                    _remove_uploaded_image()
                    st.rerun()

            st.markdown(
                f'<div class="upload-action-btn-row" data-ready="{str(is_ready).lower()}">',
                unsafe_allow_html=True,
            )
            run_clicked = st.button(
                "Run Analysis",
                key="run_analysis_upload",
                disabled=not is_ready,
                use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        if run_clicked:
            suffix = os.path.splitext(uploaded_file.name)[1] or ".png"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                st.session_state["uploaded_image_temp_path"] = tmp.name

            clear_analysis_state(clear_dataset=False)
            st.session_state["report_obj"] = None
            st.session_state["selected_site_analysis"] = None

            storage = StorageService()
            upload_service = UploadService(storage_service=storage)
            unique_storage_name = f"uploads/{uuid4().hex}_{uploaded_file.name}"

            with st.spinner("Uploading image and preparing backend data..."):
                try:
                    job = upload_service.upload_file(
                        file_data=file_bytes,
                        file_path=unique_storage_name,
                        metadata={
                            "source": "streamlit",
                            "original_name": uploaded_file.name,
                            "resolution": "unknown",
                        },
                    )
                except Exception as e:
                    st.error(f"Backend upload failed: {e}")
                    st.stop()

            if not job_is_done(job) or getattr(upload_service, "last_database", None) is None:
                st.error(getattr(job, "message", "Upload failed."))
                st.stop()

            uploaded_cache_items = [
                {
                    "name": uploaded_file.name,
                    "size_kb": round(len(file_bytes) / 1024, 1),
                    "db": upload_service.last_database,
                }
            ]
            st.session_state["uploaded_images"] = uploaded_cache_items

            image_records = [
                build_image_record(
                    name=uploaded_file.name,
                    size_bytes=len(file_bytes),
                    storage_path=unique_storage_name,
                    temp_path=st.session_state.get("uploaded_image_temp_path"),
                    mime_type=getattr(uploaded_file, "type", None),
                    db=upload_service.last_database,
                    job=job,
                )
            ]
            set_image_records(image_records, cache_items=uploaded_cache_items)

            current_dataset = st.session_state.get("_dataset_cache") or st.session_state.get("dataset")
            dataset_name = (
                getattr(current_dataset, "name", None)
                or (st.session_state.get("selected_location") or {}).get("location_name")
                or "wahhaj_selected_site_analysis"
            )
            set_dataset_state(
                current_dataset,
                status="image_uploaded",
                source="session",
                image_count=len(image_records),
                aoi=st.session_state.get("aoi"),
                name=dataset_name,
            )

            st.switch_page("pages/5_Analysis.py")

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
render_footer()
