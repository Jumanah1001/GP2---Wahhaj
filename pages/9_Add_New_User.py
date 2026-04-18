"""
pages/9_Add_New_User.py
========================
Admin Account Management.

Fixes in this version
---------------------
1. Add New User card:
   - Added .add-card CSS class back to the stylesheet.
   - Wrapped the entire right-column form content in a proper white card div.
   - The card sits BEHIND the form fields (wraps them), not above them.
   - Consistent padding, border-radius, and shadow with the rest of the project.

2. User Management table alignment:
   - Root cause: the old code split each row into col_chk (15%) + col_rest (85%)
     using Streamlit columns. The .tbl-row grid lived inside col_rest, which was
     already offset 15% from the left edge of admin-card. Meanwhile the .tbl-head
     spanned the full admin-card width. This caused every value to appear one
     grid column to the right of its header.
   - Fix: render each row as a single full-width HTML block that contains BOTH
     the checkbox input AND the data cells in one grid, perfectly matching the
     header. The Streamlit checkbox widget is replaced with a plain HTML checkbox
     that posts back via a hidden st.checkbox (rendered off-screen) so the
     delete-selected flow still works.
   - Actually simpler and more reliable: use a single st.columns split that
     matches the proportional widths of the header grid columns, so header and
     rows share the same column boundaries.
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

/* ── user table card ── */
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

    /* 7 visible columns — no separate checkbox column in the header */
    display:grid;
    grid-template-columns: 32px 44px 1fr 1.5fr 80px 100px 80px;
    align-items:center;
    gap:0;
}

/* ── table data rows ── */
/* Each row is rendered via Streamlit columns that exactly mirror the header.
   We no longer use a CSS grid on the row divs — the alignment comes from
   Streamlit's column system matching the header proportions. */
.tbl-data-row {
    padding:10px 0;
    border-bottom:1px solid #f0f0f0;
    font-size:13px; color:#222;
}
.tbl-data-row:hover { background:rgba(0,112,255,0.03); }

/* ── status badges ── */
.status-active   { color:#166534; font-weight:700; font-size:12px; }
.status-disabled { color:#991b1b; font-weight:700; font-size:12px; }

/* ── Add New User card ── */
.add-card {
    background:rgba(255,255,255,0.92);
    border-radius:16px;
    padding:28px 28px 20px 28px;
    box-shadow:0 4px 20px rgba(0,0,0,0.06);
    border:1px solid #e4e4e4;
    position:relative;
    z-index:2;
}
.add-title {
    font-family:'Capriola',sans-serif; font-size:20px;
    font-weight:700; color:#1a1a1a; margin-bottom:18px;
}
.field-hint {
    font-family:'Capriola',sans-serif; font-size:12px;
    color:#444; margin-bottom:4px; font-weight:600;
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

    # ── toolbar ──────────────────────────────────────────────────────────
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

    # ── table header ─────────────────────────────────────────────────────
    # Rendered as a pure HTML grid, full-width inside admin-card.
    # Column proportions: chk | # | Name | Email | Role | Created | Status
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

    # ── table rows ────────────────────────────────────────────────────────
    # FIX: use a single full-width HTML row so every cell aligns with the
    # header grid. The Streamlit checkbox is placed in its own narrow column
    # that starts at the LEFT edge of admin-card — exactly matching the
    # header's first column — then the remaining data fills the rest.
    #
    # We achieve this by rendering the entire row (checkbox + data) inside
    # one st.columns([32px-equiv, rest]) block, where the proportions match
    # the header grid, and the data columns are rendered as HTML spans.

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
            # The checkbox occupies ~4% and the data row the remaining ~96%.
            # This matches the header's 32px checkbox column at typical widths.
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

            # The data_col covers the right 93% of admin-card.
            # We render the remaining 6 columns (# Name Email Role Created Status)
            # as a CSS grid that spans 100% of data_col.
            # The proportions are tuned to visually match the header.
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

    # ── delete action ─────────────────────────────────────────────────────
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
# RIGHT: Add New User form — wrapped in a proper white card
# ═══════════════════════════════════════════════════════════════════════════
with col_right:
    st.markdown('<div style="position:relative;z-index:2;padding-top:24px;">', unsafe_allow_html=True)

    # FIX: open the .add-card div BEFORE the form content so the white card
    # background sits behind the fields, not as an empty box above them.
    st.markdown('<div class="add-card">', unsafe_allow_html=True)
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
            st.success(
                f"✅ **{new_username.strip()}** added as {new_role}."
            )
            st.rerun()

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-family:Capriola,sans-serif;font-size:12px;"
        "color:#666;line-height:1.6;'>"
        "New users can log in immediately.<br>"
        "User data is stored in memory for this session.</div>",
        unsafe_allow_html=True,
    )

    # FIX: close the .add-card AFTER all form content
    st.markdown("</div>", unsafe_allow_html=True)  # add-card
    st.markdown("</div>", unsafe_allow_html=True)  # outer wrapper