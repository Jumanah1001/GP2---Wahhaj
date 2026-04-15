"""
10_Add_New_User.py — Admin Account Management + Add New User (matches design mockup)
"""
import streamlit as st
from ui_helpers import init_state, apply_global_style, render_bg

st.set_page_config(page_title="User Management", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

st.markdown("""
<style>
.admin-wrap { position:relative; z-index:2; padding:24px 32px; }
.admin-title { font-family:'Capriola',sans-serif; font-size:26px; font-weight:700; color:#1a1a1a; margin-bottom:4px; }
.admin-sub   { font-size:13px; color:#888; margin-bottom:20px; }
.admin-card  {
    background:rgba(255,255,255,0.82); border-radius:16px;
    padding:0; box-shadow:0 4px 20px rgba(0,0,0,0.06); overflow:hidden;
}
.admin-toolbar {
    display:flex; align-items:center; justify-content:space-between;
    padding:14px 20px; border-bottom:1px solid #f0f0f0;
}
.tbl-head {
    display:grid;
    grid-template-columns:36px 60px 120px 200px 130px 100px 36px;
    background:#f8f8f8; padding:10px 20px;
    font-size:12px; font-weight:600; color:#888;
    border-bottom:1px solid #eee;
}
.tbl-row {
    display:grid;
    grid-template-columns:36px 60px 120px 200px 130px 100px 36px;
    padding:10px 20px; font-size:13px; color:#333;
    border-bottom:1px solid #f8f8f8; align-items:center;
}
.tbl-row:hover { background:rgba(0,112,255,0.03); }
.status-active   { color:#1a9e52; font-weight:600; font-size:12px; }
.status-disabled { color:#e74c3c; font-weight:600; font-size:12px; }
.add-card {
    background:rgba(255,255,255,0.82); border-radius:16px;
    padding:32px 36px; box-shadow:0 4px 20px rgba(0,0,0,0.06);
}
.add-title { font-family:'Capriola',sans-serif; font-size:22px; font-weight:700; color:#1a1a1a; margin-bottom:24px; }
div.stTextInput input {
    background:#F0EEEE !important; border:none !important;
    border-radius:6px !important; font-size:14px !important;
}
div.stButton > button[kind="primary"] {
    background:#0070FF !important; color:white !important;
    border-radius:8px !important; font-size:15px !important;
    min-height:44px !important; padding:8px 40px !important;
    font-family:'Capriola',sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# Mock user data
USERS = [
    {"id":1,"name":"Eman",   "email":"Eman@gmail.com",   "last_login":"2025/12/01","status":"Active",   "selected":False},
    {"id":2,"name":"Walah",  "email":"Walah@gmail.com",  "last_login":"2025/11/02","status":"Active",   "selected":False},
    {"id":3,"name":"Jumanah","email":"Jumanah@gmail.com","last_login":"2025/12/21","status":"Active",   "selected":False},
    {"id":4,"name":"Danah",  "email":"Danah@gmail.com",  "last_login":"2025/12/06","status":"Active",   "selected":False},
    {"id":5,"name":"Ruba",   "email":"Ruba@gmail.com",   "last_login":"2025/12/30","status":"Active",   "selected":False},
    {"id":6,"name":"Raghad", "email":"Raghad@gmail.com", "last_login":"2025/12/12","status":"Disabled", "selected":False},
    {"id":7,"name":"Hala",   "email":"Hala@gmail.com",   "last_login":"2025/01/01","status":"Disabled", "selected":False},
]

if "users" not in st.session_state:
    st.session_state["users"] = USERS.copy()

col_left, col_right = st.columns([1.5, 1], gap="large")

# ── LEFT: User table ──────────────────────────────────────────
with col_left:
    st.markdown('<div class="admin-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="admin-title">Admin account Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="admin-sub">Manage user account, usernames and passwords<br><small>you can add, edit, delete user</small></div>', unsafe_allow_html=True)

    st.markdown('<div class="admin-card">', unsafe_allow_html=True)

    # toolbar buttons
    t1, t2, t3, t4 = st.columns([1,1,1,1.5])
    with t1: st.button("🗑 Delete")
    with t2: st.button("⚙ Filters")
    with t4:
        if st.button("＋ Add new user", type="primary", use_container_width=True):
            st.session_state["show_add_form"] = True

    # table header
    st.markdown("""
    <div class="tbl-head">
      <span>☐</span><span>ID</span><span>Name</span>
      <span>Email</span><span>Last Login</span><span>Status</span><span></span>
    </div>""", unsafe_allow_html=True)

    # table rows
    for u in st.session_state["users"]:
        st_class = "status-active" if u["status"] == "Active" else "status-disabled"
        st_icon  = "● Active" if u["status"] == "Active" else "● Disabled"
        st.markdown(f"""
        <div class="tbl-row">
          <span><input type="checkbox" {'checked' if u.get('selected') else ''}></span>
          <span>{u['id']}</span>
          <span>{u['name']}</span>
          <span>{u['email']}</span>
          <span>{u['last_login']}</span>
          <span class="{st_class}">{st_icon}</span>
          <span style="color:#aaa;cursor:pointer;">⋮</span>
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── RIGHT: Add New User form ──────────────────────────────────
with col_right:
    st.markdown('<div style="position:relative;z-index:2;padding:24px 0;">', unsafe_allow_html=True)
    st.markdown('<div class="add-card">', unsafe_allow_html=True)
    st.markdown('<div class="add-title">Add New User</div>', unsafe_allow_html=True)

    new_username = st.text_input("Username", placeholder="Enter username")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    new_email    = st.text_input("Email",    placeholder="Enter email")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    new_password = st.text_input("Password", placeholder="Enter password", type="password")
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    _, btn_col = st.columns([1.5, 1])
    with btn_col:
        if st.button("Add", type="primary", use_container_width=True):
            if new_username and new_email and new_password:
                new_id = max(u["id"] for u in st.session_state["users"]) + 1
                st.session_state["users"].append({
                    "id": new_id, "name": new_username, "email": new_email,
                    "last_login": "—", "status": "Active", "selected": False
                })
                st.success(f"✓ User '{new_username}' added successfully!")
                st.rerun()
            else:
                st.error("Please fill all fields.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
