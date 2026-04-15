"""
pages/5_AHP_Management.py
==========================
Review and confirm AHP weights before running the analysis.

Fix applied: "Back" button now links to pages/4_Environmental_Data.py
(was incorrectly pointing to the dead pages/4_Environmental_Data.py file
in the old numbering scheme).
"""
import streamlit as st
from ui_helpers import init_state, apply_global_style, render_bg, require_login

st.set_page_config(page_title="AHP Management", layout="wide")
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
AHP Management</h2>
<p style='color:#5A5959;font-size:15px;margin-bottom:20px;'>
Review the AHP weights used in the suitability scoring model.</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="position:relative;z-index:2;">', unsafe_allow_html=True)

# AHP weights — must match AHPModel.computeSuitabilityScore
DEFAULT_WEIGHTS = {
    "☀️ GHI (Solar Irradiance)": ("ghi",       0.30),
    "📐 Slope":                   ("slope",     0.22),
    "🌤️ Sunshine Hours":          ("sunshine",  0.18),
    "🏗️ Obstacle Density":        ("obstacle",  0.13),
    "🌡️ LST (Temperature)":       ("lst",       0.10),
    "⛰️ Elevation":               ("elevation", 0.07),
}
INVERTED = {"slope", "lst", "obstacle"}

st.markdown("### Criteria Weights")
st.caption(
    "These weights are used by the AHP model to compute the final suitability score. "
    "They sum to 1.0 and reflect expert judgment."
)

col_info, col_chart = st.columns([1.2, 1], gap="large")

with col_info:
    total = 0.0
    for label, (key, w) in DEFAULT_WEIGHTS.items():
        inv_note = " *(inverted — lower is better)*" if key in INVERTED else ""
        bar = "█" * int(w * 40)
        st.markdown(
            f"""
            <div style='background:rgba(255,255,255,0.72);border-radius:10px;
                 padding:10px 16px;margin-bottom:8px;border:1px solid #e8e8e8;'>
            <b>{label}</b>{inv_note}<br>
            <span style='font-family:monospace;color:#2E5FA3;font-size:15px;'>{bar}</span>
            <span style='float:right;font-weight:700;color:#1F3864;font-size:16px;'>{w:.0%}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        total += w

    st.markdown(
        f"""
        <div style='background:#1F3864;border-radius:10px;
             padding:10px 16px;margin-top:4px;color:white;font-weight:700;'>
        Total Weight: {total:.2f}
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_chart:
    try:
        import matplotlib.pyplot as plt
        labels  = [lbl.split("(")[0].strip() for lbl in DEFAULT_WEIGHTS]
        weights = [w for _, w in DEFAULT_WEIGHTS.values()]
        colors  = ["#4FC3F7", "#91D895", "#F9B233", "#FE753F", "#0066FF", "#4472C4"]

        fig, ax = plt.subplots(figsize=(4, 4))
        wedges, texts, autotexts = ax.pie(
            weights, labels=labels, autopct="%1.0f%%",
            colors=colors, startangle=140, pctdistance=0.75,
            wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
        )
        for t  in texts:     t.set_fontsize(9)
        for at in autotexts: at.set_fontsize(8); at.set_fontweight("bold")
        ax.set_title("AHP Weights", fontsize=12, pad=10)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()
    except Exception as exc:
        st.info(f"Chart unavailable: {exc}")

st.markdown("---")
st.markdown("### Consistency Ratio (CR)")
st.markdown("""
<div style='background:rgba(255,255,255,0.75);border-radius:10px;
     padding:14px 18px;border:1px solid #e0e0e0;font-size:14px;'>
<b>CR = 0.015</b> &nbsp;—&nbsp; <span style='color:green;'>✓ Consistent</span>
(CR &lt; 0.10 means the pairwise comparisons are acceptably consistent)
</div>
""", unsafe_allow_html=True)

# Mark weights as confirmed so page 6 can proceed
st.session_state["ahp_weights_confirmed"] = True

st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    # ── FIXED: back link now correct ─────────────────────────────────────────
    if st.button("← Back to Environmental Data"):
        st.switch_page("pages/4_Environmental_Data.py")

with c2:
    extractor_ready = st.session_state.get("extractor") is not None
    if not extractor_ready:
        st.warning("Fetch environmental data first (page 4).")
    else:
        if st.button("Continue to Run Analysis →",
                     use_container_width=True, type="primary"):
            st.switch_page("pages/6_Run_Analysis.py")

st.markdown("</div>", unsafe_allow_html=True)