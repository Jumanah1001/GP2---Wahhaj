import streamlit as st
from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    login_user,
    show_logo,
    render_footer,
)

st.set_page_config(page_title="Login", layout="wide")
init_state()
apply_global_style()
render_bg()

st.markdown("""
<style>
.login-page {
    position: relative;
    z-index: 2;
    padding-top: 0px;
}

.logo-wrap {
    text-align: center;
    margin-top: -10px;
    margin-bottom: 18px;
}

.login-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(40px, 3.4vw, 54px);
    color: #5A5959;
    line-height: 1;
    margin-bottom: 8px;
}

.login-subtitle {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #5E5B5B;
    margin-bottom: 20px;
}

.field-label {
    font-family: 'Capriola', sans-serif;
    font-size: 18px;
    color: #333333;
    margin-bottom: 8px;
    margin-top: 8px;
}

div[data-testid="stForm"] {
    background: rgba(255,255,255,0.68) !important;
    border: none !important;
    border-radius: 22px !important;
    padding: 26px 28px 20px 28px !important;
    box-shadow: 0 10px 28px rgba(0,0,0,0.04) !important;
    backdrop-filter: blur(10px);
}

div[data-testid="stTextInput"] input {
    background: #F0EEEE !important;
    color: #6f6f6f !important;
    border: none !important;
    border-radius: 6px !important;
    min-height: 40px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 13px !important;
    padding-left: 14px !important;
    box-shadow: none !important;
}

div[data-testid="stTextInput"] label {
    display: none !important;
}

div[data-testid="stFormSubmitButton"] button {
    background: #0070FF !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    min-height: 44px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 16px !important;
    box-shadow: 4px 5px 4px rgba(0,0,0,0.16) !important;
}

div[data-testid="stFormSubmitButton"] button:hover {
    background: #005fe0 !important;
    color: white !important;
}

.sun-wrap-fixed {
    position: relative;
    width: 270px;
    height: 270px;
    margin: 70px auto 0 auto;
}

.sun-glow {
    position: absolute;
    width: 175px;
    height: 175px;
    left: 47px;
    top: 47px;
    background: #FFA800;
    filter: blur(56px);
    border-radius: 50%;
    opacity: 0.58;
}

.sun-core {
    position: absolute;
    width: 185px;
    height: 185px;
    left: 42px;
    top: 42px;
    border-radius: 50%;
    background: linear-gradient(38.87deg, #EE9D3E 37.22%, rgba(236, 161, 74, 0) 78.02%), #FFE600;
    box-shadow: inset 0 1px 16px rgba(255,255,255,0.77);
}

.ray {
    position: absolute;
    width: 16px;
    height: 56px;
    border-radius: 16px;
    background: linear-gradient(180deg, #FFE66A 0%, #F0B64A 100%);
    box-shadow: inset 0 2px 8px rgba(255,255,255,0.35);
}

.ray.r1 { left: 127px; top: 0px; }
.ray.r2 { right: 28px; top: 35px; transform: rotate(45deg); }
.ray.r3 { right: 0px; top: 107px; transform: rotate(90deg); }
.ray.r4 { right: 28px; bottom: 35px; transform: rotate(135deg); }
.ray.r5 { left: 127px; bottom: 0px; }
.ray.r6 { left: 28px; bottom: 35px; transform: rotate(-135deg); }
.ray.r7 { left: 0px; top: 107px; transform: rotate(90deg); }
.ray.r8 { left: 28px; top: 35px; transform: rotate(-45deg); }

@media (max-width: 900px) {
    .sun-wrap-fixed { display: none; }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="login-page">', unsafe_allow_html=True)

# logo
_, logo_col, _ = st.columns([2.6, 0.8, 2.6])
with logo_col:
    st.markdown('<div class="logo-wrap">', unsafe_allow_html=True)
    show_logo(width=145)
    st.markdown('</div>', unsafe_allow_html=True)

left, right = st.columns([1.12, 0.88], gap="large")

with left:
    with st.form("login_form", clear_on_submit=False):
        st.markdown('<div class="login-title">Login</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">to start your solar site analysis</div>', unsafe_allow_html=True)

        st.markdown('<div class="field-label">Email</div>', unsafe_allow_html=True)
        email = st.text_input("Email", placeholder="username@gmail.com", label_visibility="collapsed")

        st.write("")

        st.markdown('<div class="field-label">Password</div>', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")

        st.write("")
        submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            if login_user(email, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = email
                st.switch_page("pages/2_Home.py")
            else:
                st.error("Please enter email and password.")

with right:
    st.markdown(
        """
        <div class="sun-wrap-fixed">
            <div class="sun-glow"></div>
            <div class="ray r1"></div>
            <div class="ray r2"></div>
            <div class="ray r3"></div>
            <div class="ray r4"></div>
            <div class="ray r5"></div>
            <div class="ray r6"></div>
            <div class="ray r7"></div>
            <div class="ray r8"></div>
            <div class="sun-core"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

render_footer()

st.markdown("</div>", unsafe_allow_html=True)