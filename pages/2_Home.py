import streamlit as st
from ui_helpers import init_state, apply_global_style, render_bg, show_logo

st.set_page_config(page_title="Home", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

username = st.session_state.get("username", "Ruba")
saved_results_count = 2
account_status = "Active"

st.markdown("""
<style>
.home-page {
    position: relative;
    z-index: 2;
    padding-top: 8px;
}

.page-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(34px, 3vw, 44px);
    color: #5A5959;
    text-align: center;
    margin-bottom: 8px;
    line-height: 1.1;
}

.page-subtitle {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #5E5B5B;
    text-align: center;
    margin-bottom: 18px;
}

.card-box {
    background: rgba(255,255,255,0.60);
    border-radius: 18px;
    backdrop-filter: blur(8px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.04);
    padding: 20px 22px;
    min-height: 175px;
}

.card-title {
    font-family: 'Capriola', sans-serif;
    font-size: 20px;
    color: #4f4f4f;
    margin-bottom: 14px;
}

.card-text {
    font-family: 'Capriola', sans-serif;
    font-size: 15px;
    color: #666666;
    line-height: 1.9;
}

.footer-note {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    color: #666666;
    text-align: center;
    margin-top: 28px;
    line-height: 1.6;
}

.saved-btn-wrap {
    margin-top: 18px;
    text-align: center;
}

a.small-inner-btn,
a.small-inner-btn:link,
a.small-inner-btn:visited,
a.small-inner-btn:hover,
a.small-inner-btn:active {
    display: inline-block;
    background: #0070FF;
    color: white !important;
    text-decoration: none !important;
    border-radius: 6px;
    padding: 10px 22px;
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    box-shadow: 4px 5px 4px rgba(0,0,0,0.16);
}

a.small-inner-btn:hover {
    background: #005fe0;
}

div.stButton > button {
    background: #0070FF;
    color: white;
    border: none;
    border-radius: 6px;
    min-height: 46px;
    font-family: 'Capriola', sans-serif;
    font-size: 16px;
    box-shadow: 4px 5px 4px rgba(0,0,0,0.16);
}

div.stButton > button:hover {
    background: #005fe0;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="home-page">', unsafe_allow_html=True)

# logo
_, logo_col, _ = st.columns([2.5, 1.0, 2.5])
with logo_col:
    show_logo(width=175)

# title
st.markdown('<div class="page-title">Welcome to Wahhaj</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Start your journey toward smarter solar site selection.</div>',
    unsafe_allow_html=True
)

# start analysis
_, start_col, _ = st.columns([2.8, 1.8, 2.8])
with start_col:
    if st.button("Start Analysis", use_container_width=True):
        st.switch_page("pages/3_Choose_Location.py")

st.write("")
st.write("")

# cards row
left_space, account_col, gap, saved_col, right_space = st.columns([0.9, 2.9, 0.35, 2.9, 0.9])

with account_col:
    st.markdown(
        f"""
        <div class="card-box">
            <div class="card-title">👤 Account Details</div>
            <div class="card-text">
                UserName: {username}<br>
                Account status: {account_status} ✅
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with saved_col:
    st.markdown(
        f"""
        <div class="card-box">
            <div class="card-title">📄 Saved Results</div>
            <div class="card-text">
                Saved analyses: {saved_results_count}
            </div>
            <div class="saved-btn-wrap">
                <a href="#" class="small-inner-btn">View Saved Results</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# footer
st.markdown(
    """
    <div class="footer-note">
        Danah Alhamdi - Walah Alshwair - Ruba Aletri - Jumanah Alharbi
        <br>
        © 2026 By PNU's CS Students
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("</div>", unsafe_allow_html=True)