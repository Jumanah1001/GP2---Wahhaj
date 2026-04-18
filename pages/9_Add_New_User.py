"""
pages/9_Add_New_User.py
========================
Admin Account Management.

Root cause of the white-rectangle bug (fixed here)
---------------------------------------------------
The previous code used:
    st.markdown('<div class="add-card">')   # open tag
    st.text_input(...)                       # widget
    st.markdown('</div>')                   # close tag

Streamlit renders each st.markdown() call inside its own isolated
<div data-testid="stMarkdownContainer"> element. The browser immediately
auto-closes the <div class="add-card"> tag INSIDE that wrapper, so the
card background only applies to that single empty element — producing a
small white rectangle that appears above the actual form widgets, which
live in separate Streamlit elements outside it entirely.

Correct fix
-----------
Use CSS :has() selector on the Streamlit column container itself.

The col_right Streamlit column IS the correct container — it genuinely
wraps all the form widgets in the DOM. We inject a zero-height invisible
marker <div class="form-card-marker"> as the first element in col_right,
then use:

    [data-testid="column"]:has(.form-card-marker) {
        background: ...;  border-radius: ...;  box-shadow: ...;
    }

This styles the actual column element that contains the widgets — no
extra white shapes, no broken open/close divs, one proper card.

The card style matches .card-box used for Account and Status cards
on the Home page: same background, border-radius, shadow, border.
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

# ── Admin-only guard ──────────────────────────────────────────────────────────
user_role = st.session_state.get("user_role", "")
if user_role != "Admin":
    st.error("🚫 Access denied. This page requires Admin role.")
    st.stop()

from Wahhaj.User import User, UserRole

User.seed_default_users()


def _users_to_display() -> list:
    rows = []
    for i, u in enumerate(User._user_registry.values(), start=1):
        rows.append({
            "id":      i,
            "user_id": u.userId,
            "name":    u.name,
            "email":   u._email,
            "role":    u.role.value,
            "created": u.createdAt.strftime("%Y-%m-%d"),
            "status":  "Active" if u.is_active else "Disabled",
        })
    return rows


st.markdown("""
<style>
/* ── page wrapper ── */
.admin-wrap {
    position:relative; z-index:2; padding:24px 32px;
}
.admin-title {
    font-family:'Capriola',sans-serif; font-size:26px;
    font-weight:700; color:#1a1a1a; margin-bottom:4px;
}
.admin-sub { font-size:13px; color:#444; margin-bottom:20px; }

/* ── User Management table card ── */
.admin-card {
    background:rgba(255,255,255,0.92); border-radius:16px;
    padding:0; box-shadow:0 4px 20px rgba(0,0,0,0.06);
    overflow:hidden; border:1px solid #e4e4e4;
}

/* ── table header ── */
.tbl-head {
    background:#f4f4f4; padding:10px 18px;
    font-size:11px; font-weight:700; color:#444;
    border-bottom:1px solid #e0e0e0;
    letter-spacing:0.04em; text-transform:uppercase;
    display:grid;
    grid-template-columns: 32px 44px 1fr 1.5fr 80px 100px 80px;
    align-items:center;
    gap:0;
}

/* ── table data rows ── */
.tbl-data-row {
    padding:10px 0;
    border-bottom:1px solid #f0f0f0;
    font-size:13px; color:#222;
}
.tbl-data-row:hover { background:rgba(0,112,255,0.03); }

/* ── status badges ── */
.status-active   { color:#166534; font-weight:700; font-size:12px; }
.status-disabled { color:#991b1b; font-weight:700; font-size:12px; }

/* ── form field labels ── */
.field-hint {
    font-family:'Capriola',sans-serif; font-size:12px;
    color:#444; margin-bottom:4px; font-weight:600;
}
.add-form-title {
    font-family:'Capriola',sans-serif; font-size:20px;
    font-weight:700; color:#1a1a1a; margin-bottom:18px;
}

/* ─────────────────────────────────────────────────────────────────
   ADD NEW USER CARD — correct approach using CSS :has() selector
   
   The marker <div class="form-card-marker"> is injected as the first
   element inside col_right. The :has() selector then targets the
   Streamlit column container itself, which genuinely wraps all the
   form widgets in the DOM.

   This matches the .card-box style used for Account and Status on
   the Home page: same background, border-radius, shadow, border.
   ──────────────────────────────────────────────────────────────── */
.form-card-marker {
    display: block;
    height: 0;
    width: 0;
    overflow: hidden;
    visibility: hidden;
    position: absolute;
}

/* Card applied to the column that contains the marker */
[data-testid="column"]:has(.form-card-marker) {
    background: rgba(255,255,255,0.92);
    border-radius: 18px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    border: 1px solid rgba(220,220,220,0.7);
    padding: 24px 22px 20px 22px !important;
    position: relative;
    z-index: 2;
}

/* ── text inputs ── */
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

/* ── buttons ── */
div.stButton > button {
    background:#0070FF; color:white; border:none; border-radius:6px;
    min-height:44px; font-family:'Capriola',sans-serif; font-size:15px;
    box-shadow:3px 4px 4px rgba(0,0,0,0.14);
}
div.stButton > button:hover { background:#005fe0; color:white; }
div.stButton > button[kind="primary"] {
    background:#0070FF !important; color:white !important;
    border-radius:8px !important; font-size:15px !important;
    min-height:44px !important; font-family:'Capriola',sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1.5, 1], gap="large")

# ═══════════════════════════════════════════════════════════════════════════
# LEFT: User Management table
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
      <span>☐</span>
      <span>#</span>
      <span>Name</span>
      <span>Email</span>
      <span>Role</span>
      <span>Created</span>
      <span>Status</span>
    </div>""", unsafe_allow_html=True)

    users_list   = _users_to_display()
    selected_ids = []

    if not users_list:
        st.markdown(
            "<div style='padding:20px;text-align:center;color:#555;"
            "font-family:Capriola,sans-serif;font-size:14px;'>"
            "No users found.</div>",
            unsafe_allow_html=True,
        )
    else:
        for u in users_list:
            chk_col, data_col = st.columns([0.07, 0.93])

            with chk_col:
                checked = st.checkbox(
                    "", key=f"chk_{u['user_id']}",
                    label_visibility="collapsed",
                )
            if checked:
                selected_ids.append(u["user_id"])

            st_class = "status-active" if u["status"] == "Active" else "status-disabled"
            st_icon  = "● Active" if u["status"] == "Active" else "● Disabled"

            with data_col:
                st.markdown(
                    f"""
                    <div class="tbl-data-row" style="
                        display:grid;
                        grid-template-columns: 44px 1fr 1.5fr 80px 100px 80px;
                        align-items:center;
                        padding:9px 8px 9px 0;
                    ">
                      <span style="font-size:13px;color:#222;"><b>{u['id']}</b></span>
                      <span style="font-size:13px;color:#1a1a1a;font-weight:600;">{u['name']}</span>
                      <span style="font-size:12px;color:#444;">{u['email']}</span>
                      <span style="font-size:12px;color:#333;">{u['role']}</span>
                      <span style="font-size:12px;color:#555;">{u['created']}</span>
                      <span class="{st_class}">{st_icon}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    if del_clicked:
        if not selected_ids:
            st.warning("Select at least one user to delete.")
        else:
            current_user_id = st.session_state.get("user_id", "")
            if current_user_id in selected_ids:
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
#
# HOW THE CARD WORKS:
# The invisible .form-card-marker div is injected here as the very first
# element in col_right. The CSS rule:
#   [data-testid="column"]:has(.form-card-marker) { ...card styles... }
# targets the Streamlit column container itself — the element that
# genuinely contains all the widgets below it in the real DOM.
# No open/close div wrapping. No extra white rectangles.
# ═══════════════════════════════════════════════════════════════════════════
with col_right:
    # Marker injected FIRST — triggers the :has() card CSS on this column
    st.markdown('<div class="form-card-marker"></div>', unsafe_allow_html=True)

    # Form content — all sits inside the card-styled column
    st.markdown('<div class="add-form-title">Add New User</div>', unsafe_allow_html=True)

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

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    if st.button("Add User", type="primary",
                 use_container_width=True, key="add_user_btn"):
        errors = []
        if not new_username.strip():
            errors.append("Name is required.")
        if not new_email.strip():
            errors.append("Email is required.")
        elif "@" not in new_email:
            errors.append("Email must be a valid address.")
        if not new_password:
            errors.append("Password is required.")
        elif len(new_password) < 6:
            errors.append("Password must be at least 6 characters.")

        if new_email.strip():
            existing = User.find_by_email(new_email.strip())
            if existing is not None:
                errors.append(f"Email '{new_email.strip()}' is already registered.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            role     = UserRole.ADMIN if new_role == "Admin" else UserRole.ANALYST
            new_user = User(
                name            = new_username.strip(),
                email           = new_email.strip(),
                role            = role,
                hashed_password = new_password,
                is_active       = True,
            )
            User._user_registry[new_user.userId] = new_user
            st.success(f"✅ **{new_username.strip()}** added as {new_role}.")
            st.rerun()

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-family:Capriola,sans-serif;font-size:12px;"
        "color:#555;line-height:1.6;'>"
        "New users can log in immediately.<br>"
        "User data is stored in memory for this session.</div>",
        unsafe_allow_html=True,
    )