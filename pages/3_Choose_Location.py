import streamlit as st
from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
)

st.set_page_config(page_title="Choose Location", layout="wide")
init_state()
apply_global_style()
render_bg()

# ---------- session state ----------
if "selected_location" not in st.session_state:
    st.session_state["selected_location"] = {
        "location_name": "",
        "latitude": None,
        "longitude": None,
    }

if "location_search_input" not in st.session_state:
    st.session_state["location_search_input"] = ""

if "location_saved" not in st.session_state:
    st.session_state["location_saved"] = False

# ---------- page style ----------
st.markdown("""
<style>
.location-page {
    position: relative;
    z-index: 2;
    padding-top: 10px;
}

.page-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(34px, 3vw, 44px);
    color: #5A5959;
    line-height: 1;
    margin-bottom: 6px;
    text-align: center;
}

.page-subtitle {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #5E5B5B;
    margin-bottom: 14px;
    text-align: center;
}

.search-label {
    font-family: 'Capriola', sans-serif;
    font-size: 18px;
    color: #333333;
    margin-bottom: 8px;
}

.map-box {
    width: 100%;
    height: 320px;
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(79,195,247,0.18), rgba(249,178,51,0.18));
    display: flex;
    align-items: center;
    justify-content: center;
    color: #5A5959;
    font-family: 'Capriola', sans-serif;
    font-size: 22px;
    text-align: center;
    padding: 20px;
    box-sizing: border-box;
}

.selected-note {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #5A5959;
    margin-top: 10px;
    text-align: center;
}

div[data-testid="stTextInput"] input {
    background: #F0EEEE !important;
    color: #6f6f6f !important;
    border: none !important;
    border-radius: 6px !important;
    min-height: 40px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 13px !important;
    padding-left: 12px !important;
    box-shadow: none !important;
}

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
""", unsafe_allow_html=True)

# Home button
render_top_home_button("pages/2_Home.py")

# title
st.markdown('<div class="page-title">Choose Location</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">select the target site before uploading the UAV image</div>',
    unsafe_allow_html=True
)

left, center, right = st.columns([1.2, 8.2, 1.2])

with center:
    # search
    st.markdown('<div class="search-label">Search Location</div>', unsafe_allow_html=True)
    location_name = st.text_input(
        "Search Location",
        value=st.session_state["location_search_input"],
        placeholder="e.g. Rumah",
        label_visibility="collapsed"
    )

    # إذا تغير النص بعد الحفظ تصير الحالة unsaved
    if location_name != st.session_state["location_search_input"]:
        st.session_state["location_search_input"] = location_name
        st.session_state["location_saved"] = False

    st.write("")

    # map
    st.markdown(
        """
        <div class="map-box">
            Interactive map will appear here.
            <br><br>
            This same map will later display the suitability heatmap
            and site details after analysis.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    # buttons
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("Save Location", use_container_width=True):
            if not location_name.strip():
                st.warning("Please enter a location first.")
            else:
                st.session_state["selected_location"] = {
                    "location_name": location_name.strip(),
                    "latitude": 24.7136,
                    "longitude": 46.6753,
                }
                st.session_state["location_saved"] = True
                st.success("Location saved successfully.")

    with c2:
        if st.button("Clear", use_container_width=True):
            st.session_state["location_search_input"] = ""
            st.session_state["selected_location"] = {
                "location_name": "",
                "latitude": None,
                "longitude": None,
            }
            st.session_state["location_saved"] = False
            st.rerun()
#--------------Note!: after confirm the code for the ,ap you have to turn on this 3 liens---------------
    with c3:
        if st.button("Next", use_container_width=True):
            #if not st.session_state["location_saved"]:
            #   st.warning("Please save a valid location first.")
            #else:
                st.switch_page("pages/4_Upload_Image.py")

    selected_name = st.session_state["selected_location"]["location_name"] or "No location selected yet"
    saved_state = "Saved" if st.session_state["location_saved"] else "Not saved"
    st.markdown(
        f'<div class="selected-note">Selected location: {selected_name} · Status: {saved_state}</div>',
        unsafe_allow_html=True
    )

render_footer()