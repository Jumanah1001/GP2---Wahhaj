import streamlit as st
from html import escape

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
)

from Wahhaj.User import User, UserRole


st.set_page_config(page_title="Add New User", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

if st.session_state.get("user_role", "") != "Admin":
    st.switch_page("pages/2_Home.py")


# ─────────────────────────────────────────────────────────────
# State + helpers
# ─────────────────────────────────────────────────────────────
def _ensure_admin_page_state() -> None:
    defaults = {
        "add_user_search": "",
        "show_edit_panel": False,
        "edit_user_id": None,
        "edit_name": "",
        "edit_email": "",
        "edit_role": "Analyst",
        "edit_status": "Active",
        "user_feedback": None,
        "user_feedback_type": "success",
        "inp_role": "Analyst",
        "inp_status": "Active",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _current_admin() -> User | None:
    email = st.session_state.get("user_email", "").strip().lower()

    if email:
        found = User.find_by_email(email)
        if found:
            return found

    for user in User._user_registry.values():
        if user.role == UserRole.ADMIN:
            return user

    return None


def _set_feedback(message: str, kind: str = "success") -> None:
    st.session_state["user_feedback"] = message
    st.session_state["user_feedback_type"] = kind


def _clear_feedback() -> None:
    st.session_state["user_feedback"] = None
    st.session_state["user_feedback_type"] = "success"


def _open_edit_panel(user: User) -> None:
    st.session_state["show_edit_panel"] = True
    st.session_state["edit_user_id"] = user.userId
    st.session_state["edit_name"] = user.name
    st.session_state["edit_email"] = user._email
    st.session_state["edit_role"] = "Admin" if user.role == UserRole.ADMIN else "Analyst"
    st.session_state["edit_status"] = "Active" if user.is_active else "Inactive"


def _close_edit_panel() -> None:
    st.session_state["show_edit_panel"] = False
    st.session_state["edit_user_id"] = None


def _matching_users(users: list[User], query: str) -> list[User]:
    q = query.strip().lower()

    if not q:
        return users

    filtered = []

    for user in users:
        haystack = " ".join(
            [
                user.name.lower(),
                user._email.lower(),
                user.role.value.lower(),
                "active" if user.is_active else "inactive",
                user.userId.lower(),
            ]
        )

        if q in haystack:
            filtered.append(user)

    return filtered


def _status_badge(status: bool) -> str:
    if status:
        return '<span class="status-badge status-active">Active</span>'
    return '<span class="status-badge status-inactive">Inactive</span>'


def _role_badge(role: UserRole) -> str:
    badge_cls = "role-admin" if role == UserRole.ADMIN else "role-analyst"
    return f'<span class="role-badge {badge_cls}">{escape(role.value)}</span>'


def _choice_radio(widget_key: str, options: list[str], default: str, title: str) -> str:
    current = st.session_state.get(widget_key, default)

    if current not in options:
        current = default

    return st.radio(
        label=title,
        options=options,
        index=options.index(current),
        key=widget_key,
        horizontal=True,
    )


def _sync_created_user_to_db(new_user: User, raw_password: str) -> None:
    """
    Keeps the same DB-sync behaviour from the existing page:
    new users are persisted when the database connection is available,
    and the UI continues to work through the local registry if DB secrets are absent.
    """
    try:
        from Wahhaj.db_connection import get_db

        with get_db() as cur:
            cur.execute(
                """INSERT INTO users (user_id, name, email, role, pwd_hash, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (email) DO UPDATE SET
                       name = EXCLUDED.name,
                       role = EXCLUDED.role,
                       pwd_hash = EXCLUDED.pwd_hash,
                       is_active = EXCLUDED.is_active""",
                (
                    new_user.userId,
                    new_user.name,
                    new_user._email,
                    new_user.role.value,
                    raw_password,
                    new_user.is_active,
                ),
            )
    except Exception as exc:
        st.warning(f"DB sync warning: {exc}")


_ensure_admin_page_state()
User.seed_default_users()


# ─────────────────────────────────────────────────────────────
# Page CSS
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Base page */
.page-shell {
    position: relative;
    z-index: 2;
}

.main .block-container {
    max-width: 1280px;
    padding-top: 0.65rem;
    padding-bottom: 1.2rem;
}

/* Top nav */
.nav-area {
    margin-bottom: 14px;
}

div[class*="st-key-nav_home"] button,
div[class*="st-key-nav_logout"] button {
    min-height: 44px !important;
    border-radius: 13px !important;
    font-size: 13px !important;
    font-weight: 800 !important;
    box-shadow: 0 8px 18px rgba(0,112,255,0.16) !important;
}

/* Header */
.page-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(32px, 2.7vw, 42px);
    color: #303149;
    text-align: center;
    margin-top: 4px;
    margin-bottom: 8px;
    line-height: 1.05;
}

.page-subtitle {
    font-family: 'Capriola', sans-serif;
    font-size: 15px;
    color: #5E5B5B;
    text-align: center;
    margin-bottom: 20px;
}

/* Main width */
.admin-content {
    width: min(1060px, 82vw);
    margin-left: auto;
    margin-right: auto;
}

/* Cards */
div[class*="st-key-new_user_card"],
div[class*="st-key-existing_users_card"] {
    background: rgba(255,255,255,0.78) !important;
    border: 1px solid rgba(220,226,235,0.95) !important;
    border-radius: 22px !important;
    box-shadow: 0 10px 26px rgba(15,23,42,0.05) !important;
    backdrop-filter: blur(12px) !important;
    padding: 20px 24px 22px 24px !important;
}

div[class*="st-key-new_user_card"] {
    margin-bottom: 20px !important;
}

/* Keep the cards compact and centered even with Streamlit wide layout */
div[class*="st-key-new_user_card"],
div[class*="st-key-existing_users_card"] {
    width: min(1060px, 82vw) !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

.card-title {
    font-family: 'Capriola', sans-serif;
    font-size: 20px;
    font-weight: 800;
    color: #303149;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(0,0,0,0.08);
}

/* Form labels */
.field-label {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    font-weight: 800;
    color: #4d4d4d;
    margin-top: 0;
    margin-bottom: 6px;
}

.field-row-space {
    height: 7px;
}

.control-row-label {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #6a6a76;
    margin-bottom: 6px;
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background: #FAFAFA !important;
    color: #3a3a3a !important;
    border: 1px solid rgba(0,0,0,0.22) !important;
    border-radius: 11px !important;
    min-height: 44px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 13px !important;
    padding-left: 13px !important;
    padding-top: 7px !important;
    box-shadow: none !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    resize: none !important;
    line-height: 1.5 !important;
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(0,112,255,0.52) !important;
    background: #FFFFFF !important;
    box-shadow: 0 0 0 3px rgba(0,112,255,0.08) !important;
}

div[data-testid="stTextInput"] label,
div[data-testid="stTextArea"] label {
    display: none !important;
}

/* Password inputs should not look huge */
div[data-testid="stTextInput"] input {
    min-height: 44px !important;
}

/* Radio */
[data-testid="stRadio"] > label {
    font-family: 'Capriola', sans-serif !important;
    font-size: 13px !important;
    color: #1d1d24 !important;
    font-weight: 800 !important;
    margin-bottom: 4px !important;
}

[data-testid="stRadio"] label p {
    color: #1c1c1c !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;
}

[data-testid="stRadio"] label {
    color: #1c1c1c !important;
}

/* Generic buttons */
div.stButton > button {
    background: #0070FF !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    min-height: 42px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 13px !important;
    font-weight: 800 !important;
    box-shadow: 0 8px 18px rgba(0,112,255,0.18) !important;
    width: 100% !important;
}

div.stButton > button:hover {
    background: #005fe0 !important;
    color: white !important;
    transform: translateY(-1px);
}

div[class*="st-key-btn_clear"] button {
    background: #0070FF !important;
}

div[class*="st-key-btn_create"] button {
    background: #0070FF !important;
}

/* Feedback */
.feedback-banner {
    border-radius: 14px;
    padding: 14px 18px;
    margin: 0 auto 18px auto;
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
}

.feedback-success {
    background: rgba(80,200,120,0.12);
    border: 1px solid rgba(80,160,100,0.30);
    color: #2c7a4b;
}

.feedback-error {
    background: rgba(255,90,90,0.10);
    border: 1px solid rgba(210,70,70,0.24);
    color: #b42318;
}

/* Existing users header area */
.users-top-row {
    margin-bottom: 18px;
}

.search-wrap {
    padding-top: 2px;
}

/* Stat chips */
.stat-chip {
    background: rgba(248,250,253,0.95) !important;
    border: 1px solid #D7E1EF !important;
    border-radius: 14px !important;
    padding: 9px 12px !important;
    min-height: 54px !important;
    display: flex !important;
    align-items: center !important;
}

.stat-meta {
    font-family: 'Capriola', sans-serif;
    line-height: 1.2;
}

.stat-label {
    color: #75829B;
    font-size: 12px;
    font-weight: 800;
}

.stat-value {
    color: #303149;
    font-size: 19px;
    font-weight: 900;
    margin-top: 5px;
}

/* Table-like user list without broken vertical blocks */
.user-table-header {
    display: grid;
    grid-template-columns: 1.1fr 2.15fr 0.95fr 0.95fr 1.05fr 2.9fr;
    gap: 10px;
    background: rgba(245,247,251,0.92);
    border: 1px solid rgba(215,225,239,0.95);
    border-radius: 13px;
    padding: 10px 13px;
    margin-top: 8px;
    margin-bottom: 10px;
}

.user-table-header span {
    font-family: 'Capriola', sans-serif;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #495166;
}

div[class*="st-key-user_row_"] {
    background: rgba(255,255,255,0.72) !important;
    border: 1px solid rgba(226,233,243,0.95) !important;
    border-radius: 14px !important;
    padding: 8px 13px !important;
    margin-bottom: 8px !important;
    box-shadow: 0 4px 12px rgba(15,23,42,0.025) !important;
}

.user-cell {
    min-height: 34px;
    display: flex;
    align-items: center;
    font-family: 'Capriola', sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: #3f4658;
    line-height: 1.35;
    overflow-wrap: anywhere;
}

.user-cell.muted {
    color: #778198;
    font-size: 12px;
}

/* Badges */
.role-badge,
.status-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    font-family: 'Capriola', sans-serif;
    font-size: 11px;
    font-weight: 800;
    padding: 5px 10px;
    white-space: nowrap;
}

.role-admin {
    background: rgba(255,152,0,0.14);
    color: #e67817;
    border: 1px solid rgba(255,152,0,0.32);
}

.role-analyst {
    background: rgba(0,112,255,0.10);
    color: #0070FF;
    border: 1px solid rgba(0,112,255,0.24);
}

.status-active {
    background: rgba(66,200,122,0.12);
    color: #23935b;
    border: 1px solid rgba(66,200,122,0.28);
}

.status-inactive {
    background: rgba(120,120,120,0.10);
    color: #767676;
    border: 1px solid rgba(120,120,120,0.20);
}

/* Row action buttons */
div[class*="st-key-tbl_edit_"] button,
div[class*="st-key-tbl_toggle_"] button,
div[class*="st-key-tbl_delete_"] button {
    min-height: 34px !important;
    border-radius: 11px !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    box-shadow: none !important;
    padding: 6px 8px !important;
}

div[class*="st-key-tbl_edit_"] button {
    background: #EAF3FF !important;
    color: #0070FF !important;
    border: 1px solid rgba(0,112,255,0.28) !important;
}

div[class*="st-key-tbl_toggle_"] button {
    background: #F5F8FD !important;
    color: #303949 !important;
    border: 1px solid #D4DFEE !important;
}

div[class*="st-key-tbl_delete_"] button {
    background: #FFF1EC !important;
    color: #D94E18 !important;
    border: 1px solid rgba(217,78,24,0.24) !important;
}

div[class*="st-key-tbl_edit_"] button:hover {
    background: #DDEEFF !important;
}

div[class*="st-key-tbl_toggle_"] button:hover {
    background: #ECF2FA !important;
}

div[class*="st-key-tbl_delete_"] button:hover {
    background: #FFE5DB !important;
}

/* Edit panel */
.edit-panel-box {
    background: rgba(255,255,255,0.62);
    border: 1px solid rgba(215,225,239,0.95);
    border-radius: 20px;
    padding: 16px 18px 12px 18px;
    margin-bottom: 20px;
}

.edit-panel-title {
    font-family: 'Capriola', sans-serif;
    font-size: 18px;
    font-weight: 800;
    color: #303149;
    margin-bottom: 14px;
}

.empty-state {
    text-align: center;
    padding: 34px 0 20px 0;
    font-family: 'Capriola', sans-serif;
    color: #8a92a4;
    font-size: 14px;
}

.footer-space {
    height: 7px;
}

/* Responsive */
@media (max-width: 980px) {
    .admin-content {
        width: min(100%, 94vw);
    }

    div[class*="st-key-new_user_card"],
    div[class*="st-key-existing_users_card"] {
        padding: 22px 18px 24px 18px !important;
    }

    .user-table-header {
        display: none;
    }

    .user-cell {
        min-height: 34px;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="page-shell">', unsafe_allow_html=True)

nav_left, nav_home_col, nav_logout_col = st.columns([8.4, 1.2, 1.2], gap="small")

with nav_home_col:
    if st.button("Home", use_container_width=True, key="nav_home"):
        st.switch_page("pages/2_Home.py")

with nav_logout_col:
    if st.button("Logout", use_container_width=True, key="nav_logout"):
        for key in ["logged_in", "username", "user_email", "user_role"]:
            st.session_state.pop(key, None)
        st.switch_page("pages/1_Login.py")

st.markdown('<div class="page-title">Add New User</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Create and manage analyst accounts for the WAHHAJ platform</div>',
    unsafe_allow_html=True,
)

status_change_msg = st.session_state.pop("status_change_msg", None)

if status_change_msg:
    st.markdown(
        f"""
        <div style="
            max-width: 680px;
            margin: 0 auto 18px auto;
            background: rgba(0,112,255,0.08);
            border: 1px solid rgba(0,112,255,0.25);
            border-radius: 13px;
            padding: 12px 20px;
            font-family: 'Capriola', sans-serif;
            font-size: 14px;
            color: #0050bb;
            text-align: center;
        ">💡 {status_change_msg}</div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="admin-content">', unsafe_allow_html=True)

feedback_message = st.session_state.get("user_feedback")
feedback_kind = st.session_state.get("user_feedback_type", "success")

if feedback_message:
    feedback_cls = "feedback-success" if feedback_kind == "success" else "feedback-error"
    st.markdown(
        f'<div class="feedback-banner {feedback_cls}">{feedback_message}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# New User Details — wide horizontal card
# ─────────────────────────────────────────────────────────────
with st.container(key="new_user_card"):
    st.markdown('<div class="card-title">New User Details</div>', unsafe_allow_html=True)

    name_col, username_col = st.columns(2, gap="large")

    with name_col:
        st.markdown('<div class="field-label">Full Name</div>', unsafe_allow_html=True)
        new_name = st.text_area(
            "Full Name",
            label_visibility="collapsed",
            key="inp_name",
            height=44,
        )

    with username_col:
        st.markdown('<div class="field-label">Username</div>', unsafe_allow_html=True)
        new_username = st.text_area(
            "Username",
            label_visibility="collapsed",
            key="inp_username",
            height=44,
        )

    st.markdown('<div class="field-row-space"></div>', unsafe_allow_html=True)

    st.markdown('<div class="field-label">Email Address</div>', unsafe_allow_html=True)
    new_email = st.text_area(
        "Email Address",
        label_visibility="collapsed",
        key="inp_email",
        height=44,
    )

    st.markdown('<div class="field-row-space"></div>', unsafe_allow_html=True)

    pw_col, pw2_col = st.columns(2, gap="large")

    with pw_col:
        st.markdown('<div class="field-label">Password</div>', unsafe_allow_html=True)
        new_password = st.text_input(
            "Password",
            type="password",
            label_visibility="collapsed",
            key="inp_pw",
        )

    with pw2_col:
        st.markdown('<div class="field-label">Confirm Password</div>', unsafe_allow_html=True)
        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            label_visibility="collapsed",
            key="inp_pw2",
        )

    st.markdown('<div class="field-row-space"></div>', unsafe_allow_html=True)

    role_col, status_col = st.columns(2, gap="large")

    with role_col:
        role_choice = _choice_radio(
            widget_key="inp_role",
            options=["Analyst", "Admin"],
            default="Analyst",
            title="Role",
        )

    with status_col:
        account_status = _choice_radio(
            widget_key="inp_status",
            options=["Active", "Inactive"],
            default="Active",
            title="Account Status",
        )

    st.markdown('<div class="field-row-space"></div>', unsafe_allow_html=True)

    btn_left, btn_right = st.columns(2, gap="large")

    with btn_left:
        clear_clicked = st.button("Clear", use_container_width=True, key="btn_clear")

    with btn_right:
        create_clicked = st.button("Create User", use_container_width=True, key="btn_create")


if clear_clicked:
    for key in ["inp_name", "inp_username", "inp_email", "inp_pw", "inp_pw2"]:
        st.session_state[key] = ""

    st.session_state["inp_role"] = "Analyst"
    st.session_state["inp_status"] = "Active"
    _clear_feedback()
    st.rerun()


if create_clicked:
    _clear_feedback()
    email_candidate = new_email.strip().lower()

    if not new_name.strip():
        _set_feedback("Please enter the user's full name.", "error")
    elif not new_username.strip():
        _set_feedback("Please enter a username.", "error")
    elif not email_candidate or "@" not in email_candidate:
        _set_feedback("Please enter a valid email address.", "error")
    elif len(new_password) < 8:
        _set_feedback("Password must be at least 8 characters long.", "error")
    elif new_password != confirm_password:
        _set_feedback("Passwords do not match. Please try again.", "error")
    elif User.find_by_email(email_candidate):
        _set_feedback("A user with this email already exists.", "error")
    else:
        try:
            role = UserRole.ADMIN if role_choice == "Admin" else UserRole.ANALYST
            is_active = account_status == "Active"

            new_user = User(
                name=new_name.strip(),
                email=email_candidate,
                role=role,
                hashed_password=new_password,
                is_active=is_active,
            )

            admin_user = _current_admin()

            if admin_user and admin_user.role == UserRole.ADMIN:
                admin_user.addUser(new_user)
            else:
                User._user_registry[new_user.userId] = new_user

            _sync_created_user_to_db(new_user, new_password)

            _set_feedback(
                f"<strong>{escape(new_name.strip())}</strong> created successfully as "
                f"<strong>{escape(role_choice)}</strong> with status <strong>{escape(account_status)}</strong>."
            )

            for key in ["inp_name", "inp_username", "inp_email", "inp_pw", "inp_pw2"]:
                st.session_state[key] = ""

            st.session_state["inp_role"] = "Analyst"
            st.session_state["inp_status"] = "Active"
            st.rerun()

        except Exception as exc:
            _set_feedback(f"Could not create user: {exc}", "error")
            st.rerun()


# ─────────────────────────────────────────────────────────────
# Existing Users — wide management card
# ─────────────────────────────────────────────────────────────
all_users = list(User._user_registry.values())
visible_users = _matching_users(all_users, st.session_state.get("add_user_search", ""))

total_users = len(all_users)
active_users = sum(1 for user in all_users if user.is_active)
admin_count = sum(1 for user in all_users if user.role == UserRole.ADMIN)

with st.container(key="existing_users_card"):
    st.markdown('<div class="card-title">Existing Users</div>', unsafe_allow_html=True)

    if st.session_state.get("show_edit_panel") and st.session_state.get("edit_user_id"):
        st.markdown('<div class="edit-panel-box">', unsafe_allow_html=True)
        st.markdown('<div class="edit-panel-title">Edit User</div>', unsafe_allow_html=True)

        edit_name_col, edit_email_col = st.columns(2, gap="large")

        with edit_name_col:
            st.markdown('<div class="field-label">Full Name</div>', unsafe_allow_html=True)
            st.text_area("Edit Full Name", key="edit_name", label_visibility="collapsed", height=54)

        with edit_email_col:
            st.markdown('<div class="field-label">Email Address</div>', unsafe_allow_html=True)
            st.text_area("Edit Email", key="edit_email", label_visibility="collapsed", height=54)

        edit_role_col, edit_status_col = st.columns(2, gap="large")

        with edit_role_col:
            edited_role = _choice_radio(
                widget_key="edit_role",
                options=["Analyst", "Admin"],
                default="Analyst",
                title="Role",
            )

        with edit_status_col:
            edited_status = _choice_radio(
                widget_key="edit_status",
                options=["Active", "Inactive"],
                default="Active",
                title="Account Status",
            )

        save_col, cancel_col = st.columns(2, gap="large")

        with save_col:
            save_edit = st.button("Save Changes", use_container_width=True, key="save_edit_btn")

        with cancel_col:
            cancel_edit = st.button("Cancel", use_container_width=True, key="cancel_edit_btn")

        st.markdown("</div>", unsafe_allow_html=True)

        if save_edit:
            edit_user_id = st.session_state.get("edit_user_id")
            target = User._user_registry.get(edit_user_id)
            normalized_email = st.session_state.get("edit_email", "").strip().lower()

            if not target:
                _set_feedback("The selected user could not be found.", "error")
            elif not st.session_state.get("edit_name", "").strip():
                _set_feedback("Please enter a valid name.", "error")
            elif not normalized_email or "@" not in normalized_email:
                _set_feedback("Please enter a valid email address.", "error")
            else:
                duplicate = None

                for existing in User._user_registry.values():
                    if existing.userId != target.userId and existing._email == normalized_email:
                        duplicate = existing
                        break

                if duplicate:
                    _set_feedback("Another user already uses this email address.", "error")
                else:
                    target.name = st.session_state["edit_name"].strip()
                    target._email = normalized_email
                    target.role = UserRole.ADMIN if edited_role == "Admin" else UserRole.ANALYST
                    target.is_active = edited_status == "Active"
                    _set_feedback(f"Changes saved for <strong>{escape(target.name)}</strong>.")
                    _close_edit_panel()

            st.rerun()

        if cancel_edit:
            _close_edit_panel()
            st.rerun()

    search_col, stats_col = st.columns([1.25, 1.35], gap="large")

    with search_col:
        st.markdown('<div class="search-wrap">', unsafe_allow_html=True)
        st.text_input("Search users", key="add_user_search", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with stats_col:
        s1, s2, s3 = st.columns(3, gap="small")

        with s1:
            st.markdown(
                f"""
                <div class="stat-chip">
                    <div class="stat-meta">
                        <div class="stat-label">Total Users</div>
                        <div class="stat-value">{total_users}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with s2:
            st.markdown(
                f"""
                <div class="stat-chip">
                    <div class="stat-meta">
                        <div class="stat-label">Active</div>
                        <div class="stat-value">{active_users}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with s3:
            st.markdown(
                f"""
                <div class="stat-chip">
                    <div class="stat-meta">
                        <div class="stat-label">Admins</div>
                        <div class="stat-value">{admin_count}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="user-table-header">
            <span>Name</span>
            <span>Email</span>
            <span>Role</span>
            <span>Status</span>
            <span>User ID</span>
            <span>Actions</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not visible_users:
        st.markdown(
            '<div class="empty-state">No users match your search. Try a different name, email, or role.</div>',
            unsafe_allow_html=True,
        )

    else:
        for user in visible_users:
            short_id = f"{str(user.userId)[:8]}..."

            with st.container(key=f"user_row_{user.userId}"):
                c1, c2, c3, c4, c5, c6 = st.columns(
                    [1.15, 2.2, 1.0, 1.0, 1.2, 2.65],
                    gap="small",
                )

                with c1:
                    st.markdown(
                        f'<div class="user-cell">{escape(user.name)}</div>',
                        unsafe_allow_html=True,
                    )

                with c2:
                    st.markdown(
                        f'<div class="user-cell">{escape(user._email)}</div>',
                        unsafe_allow_html=True,
                    )

                with c3:
                    st.markdown(
                        f'<div class="user-cell">{_role_badge(user.role)}</div>',
                        unsafe_allow_html=True,
                    )

                with c4:
                    st.markdown(
                        f'<div class="user-cell">{_status_badge(user.is_active)}</div>',
                        unsafe_allow_html=True,
                    )

                with c5:
                    st.markdown(
                        f'<div class="user-cell muted">{escape(short_id)}</div>',
                        unsafe_allow_html=True,
                    )

                with c6:
                    action_cols = st.columns([1.0, 1.3, 1.0], gap="small")

                    with action_cols[0]:
                        if st.button("Edit", key=f"tbl_edit_{user.userId}", use_container_width=True):
                            _open_edit_panel(user)
                            st.rerun()

                    with action_cols[1]:
                        toggle_label = "Deactivate" if user.is_active else "Activate"

                        if st.button(toggle_label, key=f"tbl_toggle_{user.userId}", use_container_width=True):
                            user.is_active = not user.is_active
                            state_word = "activated" if user.is_active else "deactivated"
                            _set_feedback(f"<strong>{escape(user.name)}</strong> was {state_word}.")
                            st.rerun()

                    with action_cols[2]:
                        if st.button("Delete", key=f"tbl_delete_{user.userId}", use_container_width=True):
                            admin_user = _current_admin()

                            try:
                                if admin_user and admin_user.role == UserRole.ADMIN:
                                    admin_user.removeUser(user.userId)
                                else:
                                    User._user_registry.pop(user.userId, None)

                                _set_feedback(f"<strong>{escape(user.name)}</strong> was deleted.")

                                if st.session_state.get("edit_user_id") == user.userId:
                                    _close_edit_panel()

                            except Exception as exc:
                                _set_feedback(f"Could not delete user: {exc}", "error")

                            st.rerun()


st.markdown('<div class="footer-space"></div>', unsafe_allow_html=True)
render_footer()

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
