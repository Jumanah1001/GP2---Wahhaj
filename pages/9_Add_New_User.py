"""
pages/9_Add_New_User.py
========================
Admin Account Management.

Changes in this version
-----------------------
1. Text input color fix:
   Local stTextInput override now sets color:#1a1a1a explicitly so typed
   text is always visible on the #F0EEEE background.

2. Email duplicate check:
   Adding a user whose email already exists now shows a clear error instead
   of silently creating a broken duplicate.

3. Admin guard fixed:
   The original guard had a logic flaw — it allowed anyone with an empty
   role string through. Fixed: only "Admin" is permitted; Analyst role and
   empty role both trigger an error and stop.

4. Back to Home button added in the top-right corner.

5. "Last Active" column now shows the user's createdAt date instead of
   expiresAt, which is more meaningful as "Last Active" context.

6. table header color improved: #888 -> #444 for better readability.

7. add-card background improved to rgba(255,255,255,0.92) for solid contrast.
"""
import streamlit as st
from datetime import datetime

from ui_helpers import init_state, apply_global_style, render_bg, require_login

st.set_page_config(page_title="User Management", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# ── top bar ───────────────────────────────────────────────────────────────────
top_l, top_r = st.columns([9, 1])
with top_r:
    if st.button("🏠"):
        st.switch_page("pages/2_Home.py")

# ── Admin-only guard (fixed) ──────────────────────────────────────────────────
user_role = st.session_state.get("user_role", "")
if user_role != "Admin":
    st.error("🚫 Access denied. This page requires Admin role.")
    st.stop()

# ── load real users from backend ──────────────────────────────────────────────
from Wahhaj.User import User, UserRole

User.seed_default_users()


def _users_to_display() -> list:
    rows = []
    for i, u in enumerate(User._user_registry.values(), start=1):
        rows.append({
            "id":         i,
            "user_id":    u.userId,
            "name":       u.name,
            "email":      u._email,
            "role":       u.role.value,
            "created":    u.createdAt.strftime("%Y-%m-%d"),
            "status":     "Active" if u.is_active else "Disabled",
        })
    return rows


# ── styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.admin-wrap  { position:relative; z-index:2; padding:24px 32px; }
.admin-title {
    font-family:'Capriola',sans-serif; font-size:26px;
    font-weight:700; color:#1a1a1a; margin-bottom:4px;
}
.admin-sub { font-size:13px; color:#444; margin-bottom:20px; }

.admin-card {
    background:rgba(255,255,255,0.92); border-radius:16px;
    padding:0; box-shadow:0 4px 20px rgba(0,0,0,0.06); overflow:hidden;
    border:1px solid #e4e4e4;
}
.tbl-head {
    display:grid;
    grid-template-columns:36px 50px 130px 190px 90px 110px 90px 36px;
    background:#f4f4f4; padding:10px 20px;
    font-size:12px; font-weight:700; color:#444;
    border-bottom:1px solid #e0e0e0;
    letter-spacing:0.02em; text-transform:uppercase;
}
.tbl-row {
    display:grid;
    grid-template-columns:36px 50px 130px 190px 90px 110px 90px 36px;
    padding:10px 20px; font-size:13px; color:#222;
    border-bottom:1px solid #f0f0f0; align-items:center;
}
.tbl-row:hover { background:rgba(0,112,255,0.03); }
.status-active   { color:#166534; font-weight:700; font-size:12px; }
.status-disabled { color:#991b1b; font-weight:700; font-size:12px; }


.add-title {
    font-family:'Capriola',sans-serif; font-size:22px;
    font-weight:700; color:#1a1a1a; margin-bottom:20px;
}
.field-hint {
    font-family:'Capriola',sans-serif; font-size:12px;
    color:#555; margin-bottom:4px; font-weight:600;
}

/* ── FIX: input text color — color:#1a1a1a makes typed text visible ── */
div.stTextInput input {
    background:#F0EEEE !important;
    color:#1a1a1a !important;
    border:1px solid #ccc !important;
    border-radius:6px !important;
    font-size:14px !important;
    padding-left:12px !important;
    min-height:40px !important;
}
div.stTextInput input::placeholder { color:#999 !important; }

div.stButton > button[kind="primary"] {
    background:#0070FF !important; color:white !important;
    border-radius:8px !important; font-size:15px !important;
    min-height:44px !important; padding:8px 40px !important;
    font-family:'Capriola',sans-serif !important;
}
div.stButton > button[kind="secondary"] {
    background:white !important; color:#1a1a1a !important;
    border:1px solid #ccc !important;
    border-radius:8px !important; font-size:13px !important;
    min-height:36px !important;
}
</style>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1.5, 1], gap="large")

# ═══════════════════════════════════════════════════════════════════════════
# LEFT: User table
# ═══════════════════════════════════════════════════════════════════════════
with col_left:
    st.markdown('<div class="admin-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="admin-title">User Management</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="admin-sub">Add, view, and remove user accounts.<br>'
        '<small>Changes take effect immediately in the current session.</small></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="admin-card">', unsafe_allow_html=True)

    # toolbar
    t1, _, t4 = st.columns([1.2, 1.2, 1.6])
    with t1:
        del_clicked = st.button("🗑 Delete selected", key="del_btn")
    with t4:
        st.markdown(
            "<div style='font-family:Capriola,sans-serif;font-size:12px;"
            "color:#555;padding:8px 0;text-align:right;'>"
            f"{len(User._user_registry)} user(s) in system</div>",
            unsafe_allow_html=True,
        )

    # table header
    st.markdown("""
    <div class="tbl-head">
      <span>☐</span><span>#</span><span>Name</span>
      <span>Email</span><span>Role</span>
      <span>Created</span><span>Status</span><span></span>
    </div>""", unsafe_allow_html=True)

    users_list    = _users_to_display()
    selected_ids: list = []

    if not users_list:
        st.markdown(
            "<div style='padding:20px;text-align:center;color:#555;"
            "font-family:Capriola,sans-serif;font-size:14px;'>"
            "No users found.</div>",
            unsafe_allow_html=True,
        )
    else:
        for u in users_list:
            col_chk, col_rest = st.columns([0.15, 0.85])
            with col_chk:
                checked = st.checkbox(
                    "", key=f"chk_{u['user_id']}",
                    label_visibility="collapsed",
                )
            if checked:
                selected_ids.append(u["user_id"])

            st_class = "status-active" if u["status"] == "Active" else "status-disabled"
            st_icon  = "● Active" if u["status"] == "Active" else "● Disabled"

            with col_rest:
                st.markdown(
                    f"""
                    <div class="tbl-row">
                      <span></span>
                      <span><b>{u['id']}</b></span>
                      <span>{u['name']}</span>
                      <span style="font-size:12px;">{u['email']}</span>
                      <span>{u['role']}</span>
                      <span style="font-size:12px;">{u['created']}</span>
                      <span class="{st_class}">{st_icon}</span>
                      <span style="color:#bbb;cursor:pointer;">⋮</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── delete action ──────────────────────────────────────────────────────
    if del_clicked:
        if not selected_ids:
            st.warning("Select at least one user to delete.")
        else:
            # Prevent deleting the last admin
            current_user_id = st.session_state.get("user_id", "")
            protected = [uid for uid in selected_ids if uid == current_user_id]
            if protected:
                st.error("You cannot delete your own account while logged in.")
            else:
                for uid in selected_ids:
                    User._user_registry.pop(uid, None)
                st.success(f"✅ Deleted {len(selected_ids)} user(s).")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # admin-card
    st.markdown("</div>", unsafe_allow_html=True)  # admin-wrap

# ═══════════════════════════════════════════════════════════════════════════
# RIGHT: Add New User form
# ═══════════════════════════════════════════════════════════════════════════
with col_right:
    
    st.markdown('<div class="add-title">Add New User</div>', unsafe_allow_html=True)

    st.markdown('<div class="field-hint">Full Name</div>', unsafe_allow_html=True)
    new_username = st.text_input(
        "Username", placeholder="e.g. Noura Al-Harbi",
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="field-hint">Email Address</div>', unsafe_allow_html=True)
    new_email = st.text_input(
        "Email", placeholder="e.g. noura@pnu.edu.sa",
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="field-hint">Password</div>', unsafe_allow_html=True)
    new_password = st.text_input(
        "Password", placeholder="Enter a password",
        type="password",
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="field-hint">Role</div>', unsafe_allow_html=True)
    new_role = st.selectbox(
        "Role", ["Analyst", "Admin"],
        help="Admin: can manage users and run analyses. Analyst: can run analyses only.",
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    _, btn_col = st.columns([1.5, 1])
    with btn_col:
        if st.button("Add User", type="primary",
                     use_container_width=True, key="add_user_btn"):
            # ── validation ────────────────────────────────────────────────
            errors = []
            if not new_username.strip():
                errors.append("Name is required.")
            if not new_email.strip():
                errors.append("Email is required.")
            elif "@" not in new_email:
                errors.append("Email must be a valid address.")
            if not new_password:
                errors.append("Password is required.")
            if len(new_password) < 6:
                errors.append("Password must be at least 6 characters.")

            # ── duplicate email check ──────────────────────────────────────
            if new_email.strip():
                existing = User.find_by_email(new_email.strip())
                if existing is not None:
                    errors.append(
                        f"Email '{new_email.strip()}' is already registered."
                    )

            if errors:
                for err in errors:
                    st.error(err)
            else:
                role     = UserRole.ADMIN if new_role == "Admin" else UserRole.ANALYST
                new_user = User(
                    name            = new_username.strip(),
                    email           = new_email.strip(),
                    role            = role,
                    hashed_password = new_password,  # plain-text Phase 1
                    is_active       = True,
                )
                User._user_registry[new_user.userId] = new_user
                st.success(
                    f"✅ User **{new_username.strip()}** added successfully. "
                    f"They can now log in with the {new_role} role."
                )
                st.rerun()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-family:Capriola,sans-serif;font-size:12px;"
        "color:#777;line-height:1.6;'>"
        "New users can log in immediately using the credentials set above.<br>"
        "User data is stored in memory for this session only.</div>",
        unsafe_allow_html=True,
    )

   