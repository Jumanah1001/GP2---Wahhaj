"""
pages/9_Add_New_User.py
========================
Admin Account Management.

Implementation pattern
----------------------
Follows the same design language as the rest of the WAHHAJ project:

  - Card CSS values match summary-card / result-panel from 5_Analysis.py:
      background:rgba(255,255,255,0.92), border-radius:22px,
      box-shadow:0 2px 12px rgba(0,0,0,0.06), border:1px solid rgba(220,220,220,0.6)
  - Static content (user table) uses the pure HTML block pattern from 5_Analysis.py
  - Interactive widget groups (Add New User form) use the CSS :has() approach:
      A zero-size .form-card-marker is injected first in col_right.
      [data-testid="column"]:has(.form-card-marker) targets the real Streamlit
      column element and applies the card style to it.
      This is the correct way — open/close <div> splits across st.markdown()
      calls do not work because Streamlit renders each call in its own wrapper.

Why :has() works here:
  Streamlit's [data-testid="column"] genuinely wraps all its children in the DOM.
  The CSS :has() selector finds the column containing the marker and applies
  the white card style to that real container element — not to a fake empty div.
"""
import streamlit as st
from html import escape

from ui_helpers import init_state, apply_global_style, render_bg, require_login, ui_icon

st.set_page_config(page_title="User Management", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# ── top bar ───────────────────────────────────────────────────────────────────
top_l, top_r = st.columns([9, 1])
with top_r:
    if st.button(":material/home:"):
        st.switch_page("pages/2_Home.py")

# ── Admin-only guard ──────────────────────────────────────────────────────────
user_role = st.session_state.get("user_role", "")
if user_role != "Admin":
    st.error("Access denied. This page requires Admin role.")
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


# ── Styles ────────────────────────────────────────────────────────────────────
# Card values match the project's card system (5_Analysis.py reference):
#   border-radius:22-24px, box-shadow:0 2px 12px rgba(0,0,0,0.06),
#   border:1px solid rgba(220,220,220,0.6), background:rgba(255,255,255,0.92)
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
.admin-sub { font-size:13px; color:#5E5B5B; margin-bottom:20px; }

/* ── User Management table card
   Uses the same card values as result-panel from 5_Analysis.py ── */
.admin-card {
    background:rgba(255,255,255,0.92);
    border-radius:22px;
    padding:0;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    overflow:hidden;
    border:1px solid rgba(220,220,220,0.6);
}

/* ── Table header ── */
.tbl-head {
    background:#f4f4f4; padding:10px 18px;
    font-size:11px; font-weight:700; color:#444;
    border-bottom:1px solid rgba(220,220,220,0.8);
    letter-spacing:0.04em; text-transform:uppercase;
    display:grid;
    grid-template-columns: 32px 44px 1fr 1.5fr 80px 100px 80px;
    align-items:center; gap:0;
    font-family:'Capriola',sans-serif;
}

/* ── Table data rows ── */
.tbl-data-row {
    padding:9px 0; border-bottom:1px solid rgba(240,240,240,0.9);
    font-size:13px; color:#222;
}
.tbl-data-row:hover { background:rgba(0,112,255,0.03); }

/* ── Status indicators ── */
.status-active   { color:#166534; font-weight:700; font-size:12px; }
.status-disabled { color:#991b1b; font-weight:700; font-size:12px; }

/* ── Form field labels ── */
.field-hint {
    font-family:'Capriola',sans-serif; font-size:12px;
    color:#444; margin-bottom:4px; font-weight:600;
}
.add-form-title {
    font-family:'Capriola',sans-serif; font-size:20px;
    font-weight:700; color:#1a1a1a; margin-bottom:18px;
}

/* ─────────────────────────────────────────────────────────────────────
   ADD NEW USER CARD — CSS :has() approach

   The Streamlit column [data-testid="column"] that contains
   .form-card-marker genuinely wraps all form widgets in the DOM.
   We apply the card style directly to that column via :has().

   Card values match the project's card system:
   same as .admin-card and 5_Analysis.py result-panel.

   This approach works. The broken open/close <div> across separate
   st.markdown() calls does NOT work — the browser auto-closes the
   <div> inside the first st.markdown element, creating a tiny empty
   white rectangle. :has() targets the real container instead.
   ─────────────────────────────────────────────────────────────────── */
.form-card-marker {
    display:block; height:0; width:0;
    overflow:hidden; visibility:hidden; position:absolute;
}

[data-testid="column"]:has(.form-card-marker) {
    background: rgba(255,255,255,0.92);
    border-radius: 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border: 1px solid rgba(220,220,220,0.6);
    padding: 24px 22px 20px 22px !important;
    position: relative;
    z-index: 2;
}

/* ── Text inputs ── */
div.stTextInput input {
    background:#F0EEEE !important; color:#1a1a1a !important;
    border:1px solid rgba(220,220,220,0.8) !important;
    border-radius:6px !important; font-size:14px !important;
    padding-left:12px !important; min-height:40px !important;
}
div.stTextInput input::placeholder { color:#999 !important; }

/* ── Buttons ── */
div.stButton > button,
div.stButton > button:focus {
    background:#0070FF !important; color:white !important; border:none !important;
    border-radius:14px !important;
    min-height:62px !important;
    height:auto !important;
    padding-top:18px !important;
    padding-bottom:18px !important;
    padding-left:32px !important;
    padding-right:32px !important;
    font-family:'Capriola',sans-serif !important; font-size:17px !important;
    font-weight:700 !important; letter-spacing:0.03em !important;
    box-shadow: 0 4px 16px rgba(0,112,255,0.38), 0 2px 6px rgba(0,0,0,0.10) !important;
    transition: background 0.18s ease, transform 0.12s ease !important;
    line-height:1.4 !important;
    white-space:normal !important;
}
div.stButton > button > div,
div.stButton > button p {
    font-weight:700 !important;
    font-size:17px !important;
    padding:0 !important; margin:0 !important;
}
div.stButton > button:hover {
    background:#005fe0 !important; color:white !important;
    box-shadow: 0 6px 22px rgba(0,112,255,0.50) !important;
    transform: translateY(-1px) !important;
}
div.stButton > button[kind="primary"] {
    background:#0070FF !important; color:white !important;
    border-radius:14px !important;
    min-height:62px !important;
    font-family:'Capriola',sans-serif !important;
    font-weight:700 !important;
    padding-top:18px !important;
    padding-bottom:18px !important;
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
        "<div class='admin-sub'>Add, view, and remove user accounts.<br>"
        "<small>Changes take effect immediately in the current session.</small></div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="admin-card">', unsafe_allow_html=True)

    # toolbar
    t1, _, t4 = st.columns([1.2, 1.2, 1.6])
    with t1:
        del_clicked = st.button(":material/delete: Delete selected", key="del_btn")
    with t4:
        st.markdown(
            f"<div style='font-family:Capriola,sans-serif;font-size:12px;"
            f"color:#555;padding:8px 0;text-align:right;'>"
            f"{len(User._user_registry)} user(s) in system</div>",
            unsafe_allow_html=True,
        )

    # table header
    st.markdown(
        "<div class='tbl-head'>"
        "<span>☐</span><span>#</span><span>Name</span>"
        "<span>Email</span><span>Role</span>"
        "<span>Created</span><span>Status</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # table rows
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

            st_class = "status-active"   if u["status"] == "Active" else "status-disabled"
            st_icon  = "● Active"        if u["status"] == "Active" else "● Disabled"

            with data_col:
                # Pure HTML row — matches the tbl-head grid columns exactly
                st.markdown(
                    f"<div class='tbl-data-row' style='"
                    f"display:grid;"
                    f"grid-template-columns:44px 1fr 1.5fr 80px 100px 80px;"
                    f"align-items:center;padding:9px 8px 9px 0;'>"
                    f"<span style='font-size:13px;color:#222;'><b>{escape(str(u['id']))}</b></span>"
                    f"<span style='font-size:13px;color:#1a1a1a;font-weight:600;'>{escape(u['name'])}</span>"
                    f"<span style='font-size:12px;color:#444;'>{escape(u['email'])}</span>"
                    f"<span style='font-size:12px;color:#333;'>{escape(u['role'])}</span>"
                    f"<span style='font-size:12px;color:#555;'>{escape(u['created'])}</span>"
                    f"<span class='{st_class}'>{st_icon}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # delete action
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
                st.success(f"Deleted {len(selected_ids)} user(s).")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # admin-card
    st.markdown("</div>", unsafe_allow_html=True)  # admin-wrap

# ═══════════════════════════════════════════════════════════════════════════
# RIGHT: Add New User form
#
# Card is applied via CSS :has(.form-card-marker) on the column element.
# .form-card-marker injected FIRST — triggers card style on col_right.
# All form widgets follow below it inside the same column.
# No open/close <div> split across st.markdown() calls.
# ═══════════════════════════════════════════════════════════════════════════
with col_right:
    # Marker FIRST — triggers :has() card CSS on this column
    st.markdown('<div class="form-card-marker"></div>', unsafe_allow_html=True)

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
            st.success(f"**{new_username.strip()}** added as {new_role}.")
            st.rerun()

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-family:Capriola,sans-serif;font-size:12px;"
        "color:#666;line-height:1.6;'>"
        "New users can log in immediately.<br>"
        "User data is stored in memory for this session.</div>",
        unsafe_allow_html=True,
    )