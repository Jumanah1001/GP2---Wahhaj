"""
3_Upload_Image.py — Upload UAV Images only, then go to location picker
"""
import streamlit as st
from datetime import datetime, timedelta
from ui_helpers import init_state, apply_global_style, render_bg
from Wahhaj.UploadService import UploadService
from Wahhaj.storage_service import StorageService

st.set_page_config(page_title="Upload UAV Data", layout="centered")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

st.markdown("""
<style>
.upload-card {
    background: rgba(255,255,255,0.82);
    border-radius: 20px;
    padding: 40px 48px 36px 48px;
    max-width: 680px;
    margin: 32px auto 0 auto;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
    position: relative; z-index: 2;
}
.upload-title {
    font-family: 'Capriola', sans-serif;
    font-size: 28px; font-weight: 700; color: #1a1a1a;
    text-align: center; margin-bottom: 6px;
}
.upload-sub {
    font-size: 14px; color: #888;
    text-align: center; margin-bottom: 24px;
}
.drop-zone {
    border: 2.5px dashed #4CAF50;
    border-radius: 14px;
    padding: 44px 32px;
    text-align: center;
    background: rgba(255,255,255,0.5);
    margin-bottom: 0px;
}
.drop-icon  { font-size: 44px; margin-bottom: 10px; }
.drop-text  { font-size: 16px; color: #333; }
.drop-or    { font-size: 13px; color: #bbb; margin: 4px 0; }
.file-row {
    display: flex; align-items: center; gap: 12px;
    background: rgba(255,255,255,0.92);
    border-radius: 10px; padding: 10px 16px;
    margin-bottom: 8px; border: 1px solid #eee;
}
.file-icon { font-size: 20px; }
.file-name { font-size: 14px; color: #333; flex: 1; }
.file-size { font-size: 12px; color: #aaa; }
.hint-text { font-size: 12px; color: #aaa; text-align:center; margin-top: 6px; }
div.stButton > button[kind="primary"] {
    background: #0070FF !important; color: white !important;
    border-radius: 10px !important; font-size: 16px !important;
    padding: 10px 32px !important; min-height: 48px !important;
    font-family: 'Capriola', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# session init
for key, val in {
    "uploaded_images": [],
    "analysis_start_date": datetime.now() - timedelta(days=30),
    "analysis_end_date": datetime.now(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.markdown('<div class="upload-card">', unsafe_allow_html=True)
st.markdown('<div class="upload-title">Upload UAV Data</div>', unsafe_allow_html=True)
st.markdown('<div class="upload-sub">Upload drone-captured images for analysis</div>', unsafe_allow_html=True)

# Drop zone visual
st.markdown("""
<div class="drop-zone">
  <div class="drop-icon">☁️</div>
  <div class="drop-text">Drag and drop</div>
  <div class="drop-or">Or</div>
</div>
""", unsafe_allow_html=True)

# Actual uploader (Streamlit native)
uploaded_files = st.file_uploader(
    "Browse",
    type=["jpg", "jpeg", "png", "tiff", "tif"],
    accept_multiple_files=True,
    label_visibility="visible",
)
st.markdown('<div class="hint-text">Accepted formats: JPEG / PNG &nbsp;|&nbsp; Max size: 500 MB</div>', unsafe_allow_html=True)
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# Process uploads
if uploaded_files:
    storage = StorageService()
    svc = UploadService(storage_service=storage)
    processed = []
    for uf in uploaded_files:
        data = uf.read()
        job = svc.upload_file(file_data=data, file_path=uf.name,
                              metadata={"source": "streamlit"})
        if job.state.value == "done":
            processed.append({"name": uf.name,
                               "size_kb": round(len(data)/1024, 1),
                               "db": svc.last_database})
        else:
            st.error(f"✗ {uf.name} — {job.message}")
    if processed:
        st.session_state["uploaded_images"] = processed

# Show uploaded files
if st.session_state["uploaded_images"]:
    for img in st.session_state["uploaded_images"]:
        st.markdown(f"""
        <div class="file-row">
          <span class="file-icon">🖼️</span>
          <span class="file-name">{img['name']}</span>
          <span class="file-size">{img['size_kb']} KB</span>
        </div>""", unsafe_allow_html=True)

# Date range
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
st.markdown("**📅 Analysis Date Range**")
c1, c2 = st.columns(2)
with c1:
    start = st.date_input("From", value=st.session_state["analysis_start_date"],
                          label_visibility="collapsed")
with c2:
    end = st.date_input("To",   value=st.session_state["analysis_end_date"],
                        label_visibility="collapsed")
st.session_state["analysis_start_date"] = datetime.combine(start, datetime.min.time())
st.session_state["analysis_end_date"]   = datetime.combine(end,   datetime.min.time())

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# Run Analysis button → goes to location picker
_, btn_col = st.columns([2, 1])
with btn_col:
    if st.button("Run Analysis →", type="primary", use_container_width=True):
        if not st.session_state.get("uploaded_images"):
            st.error("Upload at least one image first.")
        else:
            st.switch_page("pages/2_Choose_Location.py")

st.markdown('</div>', unsafe_allow_html=True)
