"""
pages/4_Environmental_Data.py
==============================
Fetch and preview the five environmental layers for the selected AOI.

Key wiring
----------
- Reads  st.session_state["aoi"]     (set by 3_Choose_Location)
- Reads  st.session_state["dataset"] (set by 3_Choose_Location, images attached by 4_Upload)
- Writes st.session_state["extractor"] after successful fetch
- Writes st.session_state["dataset"]  with updated start/end dates
"""
import streamlit as st
import numpy as np
from datetime import datetime

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    require_login,
    get_aoi,
    get_dataset,
)

st.set_page_config(page_title="Environmental Data", layout="wide")
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
Environmental Data</h2>
<p style='color:#5A5959;font-size:15px;margin-bottom:20px;'>
Fetch and preview the environmental layers for your selected AOI.</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="position:relative;z-index:2;">', unsafe_allow_html=True)

# ── guard: AOI must exist ─────────────────────────────────────────────────────
aoi = get_aoi()
if aoi is None:
    st.warning("No AOI found. Please choose a location first.")
    if st.button("← Back to Choose Location"):
        st.switch_page("pages/3_Choose_Location.py")
    st.stop()

a = aoi
st.markdown(
    f"""
    <div style='background:rgba(255,255,255,0.75);border-radius:10px;
         padding:12px 18px;border:1px solid #e0e0e0;font-size:14px;margin-bottom:16px;'>
    <b>AOI:</b>
    lon {a[0]:.4f} → {a[2]:.4f} &nbsp;|&nbsp; lat {a[1]:.4f} → {a[3]:.4f}
    </div>
    """,
    unsafe_allow_html=True,
)

# ── fetch button ──────────────────────────────────────────────────────────────
if st.button("🌐 Fetch Environmental Data", use_container_width=True, type="primary"):
    with st.spinner("Fetching data from external sources…"):
        try:
            # NOTE: ExternalDataSourceAdapter no longer calls ee.Initialize
            # at import time — GEE is initialised lazily on first LST call.
            from Wahhaj.ExternalDataSourceAdapter import ExternalDataSourceAdapter
            from Wahhaj.FeatureExtractor import FeatureExtractor

            adapter   = ExternalDataSourceAdapter()
            extractor = FeatureExtractor(adapter=adapter)

            dataset = get_dataset()
            if dataset is None:
                st.error("Dataset not found. Complete the Choose Location step.")
                st.stop()

            # Ensure dates are set
            if dataset.start_date is None:
                dataset.start_date = st.session_state.get(
                    "analysis_start_date", datetime.now()
                )
            if dataset.end_date is None:
                dataset.end_date = st.session_state.get(
                    "analysis_end_date", datetime.now()
                )

            extractor.extractFeatures(dataset)
            extractor.normalizeData()

            st.session_state["extractor"] = extractor
            st.session_state["dataset"]   = dataset
            st.success("✓ Environmental layers fetched and normalised!")

        except Exception as exc:
            st.error(f"Error fetching environmental data: {exc}")
            st.exception(exc)
            st.session_state["extractor"] = None

# ── preview layers ────────────────────────────────────────────────────────────
extractor = st.session_state.get("extractor")
if extractor and extractor.layers:
    st.markdown("### Layer Preview")
    layer_names = list(extractor.layers.keys())
    cols = st.columns(min(len(layer_names), 3))

    LAYER_LABELS = {
        "ghi":       ("☀️ GHI",       "Global Horizontal Irradiance"),
        "lst":       ("🌡️ LST",       "Land Surface Temperature"),
        "sunshine":  ("🌤️ Sunshine",  "Sunshine Hours"),
        "elevation": ("⛰️ Elevation", "Terrain Elevation (m)"),
        "slope":     ("📐 Slope",     "Terrain Slope (°)"),
        "obstacle":  ("🏗️ Obstacle",  "Obstacle Density"),
    }

    for i, name in enumerate(layer_names):
        with cols[i % 3]:
            label, desc = LAYER_LABELS.get(name, (name, name))
            raster = extractor.layers[name]
            data   = raster.data
            valid  = data[data != raster.nodata]
            mn  = float(valid.min())  if valid.size else 0
            mx  = float(valid.max())  if valid.size else 0
            avg = float(valid.mean()) if valid.size else 0

            try:
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(3, 2.5))
                im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
                ax.set_title(label, fontsize=10)
                ax.axis("off")
                plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                plt.tight_layout()
                st.pyplot(fig, use_container_width=True)
                plt.close()
            except Exception:
                st.markdown(f"**{label}**")
                st.dataframe(
                    {f"row{r}": list(data[r]) for r in range(data.shape[0])},
                    use_container_width=True,
                )

            st.markdown(
                f"<small style='color:#666;'>{desc}<br>"
                f"min: {mn:.3f} | max: {mx:.3f} | avg: {avg:.3f}</small>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    if st.button("Continue to AHP Management →",
                 use_container_width=True, type="primary"):
        st.switch_page("pages/5_AHP_Management.py")

st.markdown("</div>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    # ── FIXED: back link now points to the active upload page ────────────────
    if st.button("← Back to Upload"):
        st.switch_page("pages/4_Upload_Image.py")