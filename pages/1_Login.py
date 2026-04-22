"""
pages/1_Login.py
================
Login page — authenticates against User backend and routes to 2_Home.py.
"""
import streamlit as st
from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    login_user,
    render_footer,
    show_logo,
)

st.set_page_config(page_title="Login", layout="wide")
init_state()
apply_global_style()
render_bg()

# If already logged in, skip straight to home
if st.session_state.get("logged_in"):
    st.switch_page("pages/2_Home.py")

st.markdown("""
<style>
.login-page { position:relative; z-index:2; margin-top:18px; }

.login-title {
    font-family:'Capriola',sans-serif;
    font-size:clamp(58px,5vw,72px); color:#5A5959; line-height:1; margin-bottom:10px;
}
.login-subtitle {
    font-family:'Capriola',sans-serif; font-size:15px; color:#5E5B5B; margin-bottom:34px;
}
.field-label {
    font-family:'Capriola',sans-serif;
    font-size:clamp(22px,1.9vw,26px); color:#333333; margin-bottom:8px; margin-top:10px;
}
.top-home-btn { width:84px; margin-left:auto; }
.top-home-btn div.stButton > button { min-height:44px; font-size:20px; border-radius:12px; box-shadow:none; }

div[data-testid="stForm"] {
    background:rgba(255,255,255,0.68) !important; border:none !important;
    border-radius:24px !important; padding:46px 42px 34px 42px !important;
    box-shadow:0 10px 34px rgba(0,0,0,0.04) !important; backdrop-filter:blur(10px);
}
div[data-testid="stTextInput"] input {
    background:#F0EEEE !important; color:#6f6f6f !important;
    border:none !important; border-radius:4px !important; min-height:44px !important;
    font-family:'Capriola',sans-serif !important; font-size:13px !important;
    padding-left:14px !important; box-shadow:none !important;
}
div[data-testid="stTextInput"] label { display:none !important; }

div[data-testid="stFormSubmitButton"] button,
div[data-testid="stFormSubmitButton"] button:focus {
    background:#0070FF !important; color:white !important; border:none !important;
    border-radius:14px !important;
    min-height:62px !important;
    height:auto !important;
    padding-top:18px !important;
    padding-bottom:18px !important;
    padding-left:32px !important;
    padding-right:32px !important;
    font-family:'Capriola',sans-serif !important;
    font-size:18px !important;
    font-weight:700 !important; letter-spacing:0.03em !important;
    box-shadow: 0 4px 18px rgba(0,112,255,0.42), 0 2px 6px rgba(0,0,0,0.10) !important;
    width:100% !important;
    transition: background 0.18s ease, transform 0.12s ease, box-shadow 0.18s ease !important;
    line-height:1.4 !important;
}
div[data-testid="stFormSubmitButton"] button > div,
div[data-testid="stFormSubmitButton"] button p {
    font-weight:700 !important;
    font-size:18px !important;
    padding:0 !important; margin:0 !important;
}
div[data-testid="stFormSubmitButton"] button:hover {
    background:#005fe0 !important; color:white !important;
    box-shadow: 0 6px 24px rgba(0,112,255,0.52) !important;
    transform: translateY(-1px) !important;
}

.sun-wrap-fixed { position:relative; width:390px; height:390px; margin:120px auto 0 auto; }
.sun-glow {
    position:absolute; width:240px; height:240px; left:75px; top:75px;
    background:#FFA800; filter:blur(72px); border-radius:50%; opacity:0.58;
}
.sun-core {
    position:absolute; width:250px; height:250px; left:70px; top:70px;
    border-radius:50%;
    background:linear-gradient(38.87deg,#EE9D3E 37.22%,rgba(236,161,74,0) 78.02%),#FFE600;
    box-shadow:inset 0 1px 16px rgba(255,255,255,0.77);
}
.ray {
    position:absolute; width:22px; height:78px; border-radius:16px;
    background:linear-gradient(180deg,#FFE66A 0%,#F0B64A 100%);
    box-shadow:inset 0 2px 8px rgba(255,255,255,0.35);
}
.ray.r1{left:184px;top:0px} .ray.r2{right:42px;top:48px;transform:rotate(45deg)}
.ray.r3{right:0px;top:156px;transform:rotate(90deg)} .ray.r4{right:42px;bottom:48px;transform:rotate(135deg)}
.ray.r5{left:184px;bottom:0px} .ray.r6{left:42px;bottom:48px;transform:rotate(-135deg)}
.ray.r7{left:0px;top:156px;transform:rotate(90deg)} .ray.r8{left:42px;top:48px;transform:rotate(-45deg)}
@media(max-width:900px){.sun-wrap-fixed{display:none}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="login-page">', unsafe_allow_html=True)

top_left, top_mid, top_right = st.columns([8, 2, 1])
with top_right:
    st.markdown('<div class="top-home-btn">', unsafe_allow_html=True)
    if st.button("⌂", use_container_width=True):
        st.switch_page("streamlit_app.py")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")
left, right = st.columns([1.22, 0.88], gap="large")

with left:
    with st.form("login_form", clear_on_submit=False):
        st.markdown('<div class="login-title">Login</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="login-subtitle">to start your solar site analysis</div>',
            unsafe_allow_html=True
        )

        st.markdown('<div class="field-label">Email</div>', unsafe_allow_html=True)
        email = st.text_input(
            "Email", placeholder="username@gmail.com", label_visibility="collapsed"
        )

        st.write("")

        st.markdown('<div class="field-label">Password</div>', unsafe_allow_html=True)
        password = st.text_input(
            "Password", type="password", placeholder="Password",
            label_visibility="collapsed"
        )

        st.write("")
        st.write("")

        submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            # ── Case 1: empty fields ──────────────────────────────────────
            if not email.strip() or not password:
                st.error("Please enter your email and password.")

            # ── Case 2: real backend authentication ───────────────────────
            # login_user() calls User.find_by_email() then user.login(),
            # and writes all session state on success.
            elif login_user(email, password):
                # ✅ Correct flow: Login → Home → Choose Location → Upload…
                st.switch_page("pages/2_Home.py")

            # ── Case 3: wrong credentials ─────────────────────────────────
            else:
                st.error("Incorrect email or password. Please try again.")

with right:
    st.markdown(
        """
        <div class="sun-wrap-fixed">
            <div class="sun-glow"></div>
            <div class="ray r1"></div><div class="ray r2"></div>
            <div class="ray r3"></div><div class="ray r4"></div>
            <div class="ray r5"></div><div class="ray r6"></div>
            <div class="ray r7"></div><div class="ray r8"></div>
            <div class="sun-core"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)
render_footer()