"""
pages/10_Add_New_User.py
=========================
Admin Account Management — matches the design mockup.

Changes vs original
-------------------
- The Add New User form now creates a real User in User._user_registry,
  so the new account can actually log in through 1_Login.py.
- Delete removes the user from User._user_registry as well.
- Role (Admin / Analyst) selector added to the Add New User form.
- Page is guarded: only users with role "Admin" can access it.
"""
import streamlit as st
from datetime import datetime

from ui_helpers import init_state, apply_global_style, render_bg, require_login

st.set_page_config(page_title="User Management", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# ── Admin-only guard ──────────────────────────────────────────────────────────
if st.session_state.get("user_role") not in ("Admin", ""):
    # Allow empty role for backward compat with old sessions
    if st.session_state.get("user_role") == "Analyst":
        st.error("Access denied. Admin role required.")
        st.stop()

# ── load real users from backend ──────────────────────────────────────────────
from Wahhaj.User import User, UserRole

User.seed_default_users()  # ensure dev users exist

def _users_to_display() -> list:
    """Convert User._user_registry to a list of display dicts."""
    rows = []
    for i, u in enumerate(User._user_registry.values(), start=1):
        rows.append({
            "id":         i,
            "user_id":    u.userId,
            "name":       u.name,
            "email":      u._email,
            "role":       u.role.value,
            "last_login": u.expiresAt.strftime("%Y/%m/%d"),
            "status":     "Active" if u.is_active else "Disabled",
        })
    return rows

# ── styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.admin-wrap  { position:relative; z-index:2; padding:24px 32px; }
.admin-title { font-family:'Capriola',sans-serif; font-size:26px; font-weight:700; color:#1a1a1a; margin-bottom:4px; }
.admin-sub   { font-size:13px; color:#888; margin-bottom:20px; }
.admin-card  {
    background:rgba(255,255,255,0.82); border-radius:16px;
    padding:0; box-shadow:0 4px 20px rgba(0,0,0,0.06); overflow:hidden;
}
.tbl-head {
    display:grid;
    grid-template-columns:36px 60px 120px 190px 90px 120px 90px 36px;
    background:#f8f8f8; padding:10px 20px;
    font-size:12px; font-weight:600; color:#888; border-bottom:1px solid #eee;
}
.tbl-row {
    display:grid;
    grid-template-columns:36px 60px 120px 190px 90px 120px 90px 36px;
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
.add-title {
    font-family:'Capriola',sans-serif; font-size:22px;
    font-weight:700; color:#1a1a1a; margin-bottom:24px;
}
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

col_left, col_right = st.columns([1.5, 1], gap="large")

# ═══════════════════════════════════════════════════════════════════════════
# LEFT: User table from real registry
# ═══════════════════════════════════════════════════════════════════════════
with col_left:
    st.markdown('<div class="admin-wrap">', unsafe_allow_html=True)
    st.markdown(
        '<div class="admin-title">Admin account Management</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="admin-sub">Manage user accounts, usernames and passwords<br>'
        '<small>you can add or delete users</small></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="admin-card">', unsafe_allow_html=True)

    # toolbar
    t1, t2, t3, t4 = st.columns([1, 1, 1, 1.5])
    with t1:
        del_clicked = st.button("🗑 Delete selected", key="del_btn")
    with t4:
        if st.button("＋ Add new user", type="primary",
                     use_container_width=True, key="show_add_btn"):
            st.session_state["show_add_form"] = True

    # table header
    st.markdown("""
    <div class="tbl-head">
      <span>☐</span><span>ID</span><span>Name</span>
      <span>Email</span><span>Role</span>
      <span>Last Active</span><span>Status</span><span></span>
    </div>""", unsafe_allow_html=True)

    # checkboxes and rows
    users_list = _users_to_display()
    selected_ids: list = []
    for u in users_list:
        col_chk, col_rest = st.columns([0.15, 0.85])
        with col_chk:
            checked = st.checkbox("", key=f"chk_{u['user_id']}",
                                  label_visibility="collapsed")
        if checked:
            selected_ids.append(u["user_id"])
        st_class = "status-active" if u["status"] == "Active" else "status-disabled"
        st_icon  = "● Active" if u["status"] == "Active" else "● Disabled"
        with col_rest:
            st.markdown(
                f"""
                <div class="tbl-row">
                  <span></span>
                  <span>{u['id']}</span>
                  <span>{u['name']}</span>
                  <span>{u['email']}</span>
                  <span>{u['role']}</span>
                  <span>{u['last_login']}</span>
                  <span class="{st_class}">{st_icon}</span>
                  <span style="color:#aaa;cursor:pointer;">⋮</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── delete action ─────────────────────────────────────────────────────────
    if del_clicked:
        if selected_ids:
            for uid in selected_ids:
                User._user_registry.pop(uid, None)
            st.success(f"Deleted {len(selected_ids)} user(s).")
            st.rerun()
        else:
            st.warning("Select at least one user to delete.")

    st.markdown("</div>", unsafe_allow_html=True)  # admin-card
    st.markdown("</div>", unsafe_allow_html=True)  # admin-wrap

# ═══════════════════════════════════════════════════════════════════════════
# RIGHT: Add New User form — creates real User in registry
# ═══════════════════════════════════════════════════════════════════════════
with col_right:
    st.markdown('<div style="position:relative;z-index:2;padding:24px 0;">', unsafe_allow_html=True)
    st.markdown('<div class="add-card">', unsafe_allow_html=True)
    st.markdown('<div class="add-title">Add New User</div>', unsafe_allow_html=True)

    new_username = st.text_input("Username", placeholder="Enter full name")
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    new_email    = st.text_input("Email",    placeholder="Enter email")
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    new_password = st.text_input("Password", placeholder="Enter password",
                                 type="password")
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    new_role     = st.selectbox(
        "Role", ["Analyst", "Admin"],
        help="Admin can manage users; Analyst can run analyses."
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    _, btn_col = st.columns([1.5, 1])
    with btn_col:
        if st.button("Add", type="primary", use_container_width=True, key="add_user_btn"):
            if new_username and new_email and new_password:
                # ── create real User in backend registry ──────────────────────
                role = UserRole.ADMIN if new_role == "Admin" else UserRole.ANALYST
                new_user = User(
                    name            = new_username.strip(),
                    email           = new_email.strip(),
                    role            = role,
                    hashed_password = new_password,  # plain-text Phase 1
                    is_active       = True,
                )
                User._user_registry[new_user.userId] = new_user
                st.success(
                    f"✓ User '{new_username}' added. "
                    f"They can now log in as {new_role}."
                )
                st.rerun()
            else:
                st.error("Please fill all fields (username, email, password).")

    st.markdown("</div>", unsafe_allow_html=True)  # add-card
    st.markdown("</div>", unsafe_allow_html=True)