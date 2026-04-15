"""
pages/7_Suitability_Heatmap.py
================================
View the suitability heatmap and inspect individual site details.

Fixes applied
-------------
1. Variable name shadowing: the original code assigned `st_min`, `st_max`,
   `st_mean` inside a `with col_info:` block immediately after importing
   Streamlit as `st`.  In CPython these don't actually shadow the module
   object, but they are confusing and can conflict if the variable names
   are ever refactored.  Renamed to `score_min`, `score_max`, `score_mean`.

2. Auth guard: replaced `st.warning + st.stop()` with `require_login()`
   which calls `st.switch_page` for a clean redirect.

3. Site inspection: added a site-selector dropdown so the user can click
   through any ranked candidate and see its individual layer values in the
   "Site Details" panel — matches the report's "Inspect Site Information"
   use-case description (Figure 16 in the report).
"""
import streamlit as st
import numpy as np

from ui_helpers import init_state, apply_global_style, render_bg, require_login

st.set_page_config(page_title="Suitability Heatmap", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

st.markdown("""
<style>
.heatmap-wrap { position:relative; z-index:2; padding:24px 40px; }
.heatmap-title {
    font-family:'Capriola',sans-serif; font-size:34px;
    font-weight:700; color:#1a1a1a; margin-bottom:28px;
}
.site-popup {
    background:rgba(255,255,255,0.92); border-radius:14px;
    padding:18px 24px; box-shadow:0 4px 20px rgba(0,0,0,0.10);
    font-size:14px; max-width:280px;
}
.site-popup-title { font-weight:700; font-size:16px; margin-bottom:12px; color:#1a1a1a; }
.site-popup ul { margin:0; padding-left:16px; color:#333; line-height:2; }
div.stButton > button[kind="primary"] {
    background:#0070FF !important; color:white !important;
    border-radius:10px !important; font-size:15px !important;
    padding:10px 28px !important; min-height:46px !important;
}
</style>
""", unsafe_allow_html=True)

run = st.session_state.get("analysis_run")
if run is None or run.suitability is None:
    st.warning("No analysis results. Run the analysis first.")
    if st.button("← Back to Run Analysis"):
        st.switch_page("pages/6_Run_Analysis.py")
    st.stop()

suitability = run.suitability
data        = suitability.data
aoi         = st.session_state.get("aoi", (46.0, 24.0, 47.0, 25.0))

st.markdown('<div class="heatmap-wrap">', unsafe_allow_html=True)
st.markdown('<div class="heatmap-title">View Suitability Heatmap</div>',
            unsafe_allow_html=True)

col_map, col_info = st.columns([1.8, 1], gap="large")

# ═══════════════════════════════════════════════════════════════════════════
# LEFT: heatmap plot
# ═══════════════════════════════════════════════════════════════════════════
with col_map:
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 5.5))
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")

        # extent = [left, right, bottom, top] = [lon_min, lon_max, lat_min, lat_max]
        extent = [aoi[0], aoi[2], aoi[1], aoi[3]]
        im = ax.imshow(
            data, cmap="RdYlGn", vmin=0, vmax=1,
            extent=extent, aspect="auto", origin="lower",
            interpolation="bilinear", alpha=0.85,
        )

        # Overlay ranked candidates with their rank numbers
        if run.candidates:
            from Wahhaj.SiteCandidate import SiteCandidate
            ranked = SiteCandidate.rank_all(list(run.candidates))
            for c in ranked[:7]:
                if c.centroid:
                    color = (
                        "#2ecc71" if c.score >= 0.7 else
                        "#f1c40f" if c.score >= 0.5 else
                        "#e74c3c"
                    )
                    ax.scatter(
                        c.centroid.lon, c.centroid.lat,
                        s=320, c=color, edgecolors="white",
                        linewidths=1.5, zorder=5,
                    )
                    ax.text(
                        c.centroid.lon, c.centroid.lat, str(c.rank),
                        ha="center", va="center", fontsize=9,
                        fontweight="bold", color="white", zorder=6,
                    )

        ax.set_xlabel("Longitude", fontsize=10)
        ax.set_ylabel("Latitude",  fontsize=10)
        ax.tick_params(labelsize=9)
        plt.colorbar(im, ax=ax, label="Suitability [0–1]",
                     fraction=0.035, pad=0.03)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()

    except Exception as exc:
        st.error(f"Could not render heatmap: {exc}")

# ═══════════════════════════════════════════════════════════════════════════
# RIGHT: score summary + site inspection panel
# ═══════════════════════════════════════════════════════════════════════════
with col_info:
    # ── score summary ─────────────────────────────────────────────────────
    valid      = data[data != suitability.nodata]
    # FIXED: renamed from st_min / st_max / st_mean to avoid any potential
    #        confusion with the st (streamlit) module object.
    score_min  = float(valid.min())  if valid.size else 0.0
    score_max  = float(valid.max())  if valid.size else 0.0
    score_mean = float(valid.mean()) if valid.size else 0.0

    st.markdown("""
    <div style='background:rgba(255,255,255,0.82);border-radius:14px;
         padding:20px 22px;box-shadow:0 2px 12px rgba(0,0,0,0.06);'>
    <div style='font-weight:700;font-size:15px;margin-bottom:14px;'>Score Summary</div>
    """, unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Min",  f"{score_min:.3f}")
    m2.metric("Max",  f"{score_max:.3f}")
    m3.metric("Mean", f"{score_mean:.3f}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── site inspection panel (Inspect Site Information — report §3.1.2.5) ─
    if run.candidates:
        from Wahhaj.SiteCandidate import SiteCandidate
        ranked_sites = SiteCandidate.rank_all(list(run.candidates))
        extractor    = st.session_state.get("extractor")

        # Site selector
        site_options = {
            f"#{c.rank} — Score {c.score:.4f} "
            f"({c.centroid.lat:.4f}°N, {c.centroid.lon:.4f}°E)"
            if c.centroid else
            f"#{c.rank} — Score {c.score:.4f}": c
            for c in ranked_sites
        }
        selected_label = st.selectbox(
            "Inspect site",
            options=list(site_options.keys()),
            key="heatmap_site_sel",
        )
        selected_site = site_options[selected_label]

        # Get layer value at this site's pixel
        def get_layer_val(layer_name: str, site) -> str:
            if extractor and layer_name in extractor.layers:
                row = site.attrs.get("pixel_row", 2)
                col = site.attrs.get("pixel_col", 2)
                try:
                    val = float(extractor.layers[layer_name].data[row, col])
                    return f"{round(val * 100, 1)}"
                except Exception:
                    return "—"
            return "—"

        st.markdown(
            f"""
            <div class="site-popup">
              <div class="site-popup-title">Site Details</div>
              <ul>
                <li>Suitability Score &nbsp;: <b>{round(selected_site.score * 10, 2)}/10</b></li>
                <li>Slope &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:
                    <b>{get_layer_val('slope', selected_site)}</b></li>
                <li>Elevation &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:
                    <b>{get_layer_val('elevation', selected_site)}</b></li>
                <li>Solar Radiation &nbsp;:
                    <b>{get_layer_val('ghi', selected_site)}</b></li>
                <li>Surface Temp &nbsp;&nbsp;&nbsp;&nbsp;:
                    <b>{get_layer_val('lst', selected_site)}</b></li>
                <li>Sunshine Hours &nbsp;&nbsp;:
                    <b>{get_layer_val('sunshine', selected_site)}</b></li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ── legend ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='font-size:12px;color:#666;'>
      <span style='background:#2ecc71;border-radius:4px;
            padding:2px 8px;color:white;margin-right:6px;'>●</span>Highly Suitable (≥0.7)
      <br><br>
      <span style='background:#f1c40f;border-radius:4px;
            padding:2px 8px;color:white;margin-right:6px;'>●</span>Suitable (0.5–0.7)
      <br><br>
      <span style='background:#e74c3c;border-radius:4px;
            padding:2px 8px;color:white;margin-right:6px;'>●</span>Low (&lt;0.5)
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── navigation ────────────────────────────────────────────────────────────────
_, btn_col = st.columns([4, 1])
with btn_col:
    if st.button("View Ranking →", type="primary", use_container_width=True):
        st.switch_page("pages/8_Ranked_Results.py")

back_col, _ = st.columns([1, 4])
with back_col:
    if st.button("← Back"):
        st.switch_page("pages/6_Run_Analysis.py")

st.markdown("</div>", unsafe_allow_html=True)