import os
import tempfile
import time
from html import escape
from textwrap import dedent
from uuid import uuid4

import streamlit as st
from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
    build_image_record,
    clear_analysis_state,
    set_dataset_state,
    set_image_records,
)

from Wahhaj.UploadService import UploadService
from Wahhaj.storage_service import StorageService


st.set_page_config(page_title="Upload Image", layout="wide")
init_state()
apply_global_style()
render_bg()

# ── JS enforcer: يطبّق الأبعاد على DOM مباشرة بعد كل render ──
st.markdown(
    """
    <script>
    (function applyBtnSizes() {
        const BTN_H   = "50px";
        const BTN_W   = "120px";
        const BTN_R   = "12px";
        const BTN_FS  = "18px";
        const BTN_SH  = "0 4px 14px rgba(0,112,255,0.30)";
        const BTN_PAD = "12px 18px";

        function styleBtn(btn, isDisabled) {
            btn.style.setProperty("min-height", BTN_H,  "important");
            btn.style.setProperty("height",     BTN_H,  "important");
            btn.style.setProperty("width",      BTN_W,  "important");
            btn.style.setProperty("min-width",  BTN_W,  "important");
            btn.style.setProperty("max-width",  BTN_W,  "important");
            btn.style.setProperty("padding",    BTN_PAD,"important");
            btn.style.setProperty("font-size",  BTN_FS, "important");
            btn.style.setProperty("border-radius", BTN_R,"important");
            btn.style.setProperty("line-height","1",    "important");
            btn.style.setProperty("white-space","nowrap","important");
            btn.style.setProperty("display",    "inline-flex","important");
            btn.style.setProperty("align-items","center","important");
            btn.style.setProperty("justify-content","center","important");

            if (isDisabled) {
                btn.style.setProperty("background","#d0d0d0","important");
                btn.style.setProperty("color",     "#888",   "important");
                btn.style.setProperty("border",    "1px solid #bbb","important");
                btn.style.setProperty("box-shadow","none",   "important");
                btn.style.setProperty("cursor",    "not-allowed","important");
                btn.style.setProperty("opacity",   "1",      "important");
                btn.style.setProperty("transform", "none",   "important");
            } else {
                btn.style.setProperty("background","#0070FF","important");
                btn.style.setProperty("color",     "white",  "important");
                btn.style.setProperty("border",    "none",   "important");
                btn.style.setProperty("box-shadow",BTN_SH,  "important");
            }
        }

        function applyHomeSize(b) {
            b.style.setProperty("min-height",    BTN_H,   "important");
            b.style.setProperty("height",        BTN_H,   "important");
            b.style.setProperty("width",         BTN_W,   "important");
            b.style.setProperty("min-width",     BTN_W,   "important");
            b.style.setProperty("max-width",     BTN_W,   "important");
            b.style.setProperty("padding",       BTN_PAD, "important");
            b.style.setProperty("font-size",     BTN_FS,  "important");
            b.style.setProperty("border-radius", BTN_R,   "important");
            b.style.setProperty("line-height",   "1",     "important");
            b.style.setProperty("white-space",   "nowrap","important");
            b.style.setProperty("display",       "inline-flex","important");
            b.style.setProperty("align-items",   "center","important");
            b.style.setProperty("justify-content","center","important");
            b.style.setProperty("box-shadow",    BTN_SH,  "important");
        }

        function run() {
            // Home button — fixed width like original
            document.querySelectorAll(".top-home-btn button").forEach(b => {
                applyHomeSize(b);
            });

            // Run Analysis button — full width of its column, only fix height + color
            document.querySelectorAll(".run-analysis-row button").forEach(b => {
                const isDisabled = b.disabled
                    || b.hasAttribute("disabled")
                    || b.getAttribute("aria-disabled") === "true"
                    || b.closest("[data-ready='false']") !== null;
                b.style.setProperty("min-height",    BTN_H,  "important");
                b.style.setProperty("height",        BTN_H,  "important");
                b.style.setProperty("padding",       BTN_PAD,"important");
                b.style.setProperty("font-size",     BTN_FS, "important");
                b.style.setProperty("border-radius", BTN_R,  "important");
                b.style.setProperty("line-height",   "1",    "important");
                b.style.setProperty("white-space",   "nowrap","important");
                b.style.setProperty("font-weight",   "700",  "important");
                if (isDisabled) {
                    b.style.setProperty("background", "#d0d0d0", "important");
                    b.style.setProperty("color",      "#888",    "important");
                    b.style.setProperty("border",     "1px solid #bbb","important");
                    b.style.setProperty("box-shadow", "none",    "important");
                    b.style.setProperty("cursor",     "not-allowed","important");
                    b.style.setProperty("opacity",    "1",       "important");
                } else {
                    b.style.setProperty("background", "#0070FF", "important");
                    b.style.setProperty("color",      "white",   "important");
                    b.style.setProperty("border",     "none",    "important");
                    b.style.setProperty("box-shadow", BTN_SH,   "important");
                }
            });

            // Upload (Browse files) button
            document.querySelectorAll('[data-testid="stFileUploader"] button').forEach(b => {
                applyHomeSize(b);
            });
        }

        // Run immediately + watch for DOM changes (Streamlit re-renders)
        const obs = new MutationObserver(run);
        obs.observe(document.body, { childList: true, subtree: true });
        setTimeout(run, 100);
        setTimeout(run, 500);
        setTimeout(run, 1500);
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

# -----------------------------
# session state defaults
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
                <span class="upload-file-icon">📄</span>
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


st.markdown(
    dedent("""
    <style>
    .upload-page {
        position: relative;
        z-index: 2;
        padding-top: 44px;
    }

    .page-title {
        font-family: 'Capriola', sans-serif;
        font-size: clamp(34px, 3vw, 44px);
        color: #5A5959;
        line-height: 1.05;
        margin-bottom: 10px;
        text-align: center;
    }

    .page-subtitle {
        font-family: 'Capriola', sans-serif;
        font-size: 14px;
        color: #5E5B5B;
        margin-top: 4px;
        margin-bottom: 18px;
        text-align: center;
    }

    .upload-center-shell {
        max-width: 700px;
        margin: 34px auto 0 auto;
    }

    :root {
        --upload-btn-width: 120px;
        --upload-btn-height: 50px;
        --upload-btn-radius: 12px;
        --upload-btn-font: 18px;
        --upload-btn-shadow: 0 4px 14px rgba(0,112,255,0.30);
    }

    div[data-testid="stFileUploader"] {
        width: 100%;
        margin-bottom: 0 !important;
    }

    div[data-testid="stFileUploader"] > section {
        border: 3px dashed #9ED79D !important;
        border-radius: 24px !important;
        background: rgba(255,255,255,0.10) !important;
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

    /* Upload button: matches Home button size */
    div[data-testid="stFileUploader"] button,
    div[data-testid="stFileUploader"] section button,
    div[data-testid="stFileUploader"] [role="button"] {
        position: absolute !important;
        left: 50% !important;
        top: 50% !important;
        transform: translate(-50%, -50%) !important;
        background: #0070FF !important;
        color: white !important;
        border: none !important;
        border-radius: var(--upload-btn-radius) !important;
        min-height: var(--upload-btn-height) !important;
        height: var(--upload-btn-height) !important;
        width: var(--upload-btn-width) !important;
        min-width: var(--upload-btn-width) !important;
        max-width: var(--upload-btn-width) !important;
        padding: 12px 18px !important;
        font-family: 'Capriola', sans-serif !important;
        font-size: var(--upload-btn-font) !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        box-shadow: var(--upload-btn-shadow) !important;
        z-index: 4 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
    }

    div[data-testid="stFileUploader"] button:hover,
    div[data-testid="stFileUploader"] section button:hover,
    div[data-testid="stFileUploader"] [role="button"]:hover {
        background: #005fe0 !important;
        color: white !important;
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
        font-family: 'Capriola', sans-serif;
        font-size: 13px;
        color: #777777;
        text-align: center;
        margin-top: -122px;
        margin-bottom: 112px;
        position: relative;
        z-index: 5;
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
        font-family: 'Capriola', sans-serif;
        color: #41516E;
        font-size: 13px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .upload-progress-pct {
        font-family: 'Capriola', sans-serif;
        font-size: 13px;
        color: #365277;
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
        font-family: 'Capriola', sans-serif;
        font-size: 12px;
        color: #6B7280;
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
        font-size: 12px;
        font-family: 'Capriola', sans-serif;
        line-height: 1;
        font-weight: 700;
    }

    .upload-success-inline {
        font-family: 'Capriola', sans-serif;
        font-size: 12px;
        color: #22A352;
        font-weight: 700;
    }

    .upload-success-meta {
        margin-top: 10px;
        font-family: 'Capriola', sans-serif;
        font-size: 12px;
        color: #777777;
        text-align: center;
    }

    /* Run Analysis button: matches Home button size */
    .run-analysis-row {
        width: 100%;
        margin: 4px 0 0 0;
    }

    .run-analysis-row div.stButton > button,
    .run-analysis-row div.stButton > button:focus {
        background: #0070FF !important;
        color: white !important;
        border: none !important;
        border-radius: var(--upload-btn-radius) !important;
        min-height: var(--upload-btn-height) !important;
        height: var(--upload-btn-height) !important;
        width: var(--upload-btn-width) !important;
        min-width: var(--upload-btn-width) !important;
        max-width: var(--upload-btn-width) !important;
        padding: 12px 18px !important;
        font-family: 'Capriola', sans-serif !important;
        font-size: var(--upload-btn-font) !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        box-shadow: var(--upload-btn-shadow) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
        white-space: nowrap !important;
    }

    .run-analysis-row div.stButton > button:hover {
        background: #005fe0 !important;
        color: white !important;
        transform: translateY(-1px) !important;
    }

    .run-analysis-row div.stButton > button:disabled,
    .run-analysis-row div.stButton > button[disabled] {
        background: #d0d0d0 !important;
        color: #888 !important;
        border: 1px solid #bbb !important;
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

        .run-analysis-row {
            width: var(--upload-btn-width);
        }
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

left_sp, center, right_sp = st.columns([2.0, 3.8, 2.0])

with center:
    st.markdown('<div class="upload-center-shell">', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload site image",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        label_visibility="collapsed",
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
            steps = [
                (18, "Preparing uploaded image..."),
                (42, "Validating file format..."),
                (71, "Finalising upload preview..."),
                (100, "Upload completed successfully."),
            ]
            for pct, msg in steps:
                progress_slot.markdown(
                    _render_upload_progress(uploaded_file.name, pct, msg),
                    unsafe_allow_html=True,
                )
                time.sleep(0.18)
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
            st.markdown(
                f'<div class="run-analysis-row" data-ready="{str(is_ready).lower()}">',
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
            # خزني نسخة مؤقتة للواجهة / أي استخدام لاحق
            suffix = os.path.splitext(uploaded_file.name)[1] or ".png"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                st.session_state["uploaded_image_temp_path"] = tmp.name

            # صفري نتائج قديمة مرتبطة بأي Run سابق، لكن احتفظي بمسودة الموقع الحالية
            clear_analysis_state(clear_dataset=False)
            st.session_state["report_obj"] = None
            st.session_state["selected_site_analysis"] = None

            # رفع فعلي للباك إند
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
