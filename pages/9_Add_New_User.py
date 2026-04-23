import streamlit as st
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
        haystack = " ".join([
            user.name.lower(),
            user._email.lower(),
            user.role.value.lower(),
            ("active" if user.is_active else "inactive"),
            user.userId.lower(),
        ])
        if q in haystack:
            filtered.append(user)
    return filtered


def _status_badge(status: bool) -> str:
    if status:
        return '<span class="status-badge status-active">Active</span>'
    return '<span class="status-badge status-inactive">Inactive</span>'


def _role_badge(role: UserRole) -> str:
    badge_cls = "role-admin" if role == UserRole.ADMIN else "role-analyst"
    return f'<span class="role-badge {badge_cls}">{role.value}</span>'


def _styled_toggle(widget_key: str, label_off: str, label_on: str, default: bool = False, title: str = "") -> bool:
    """
    Horizontal st.radio rendered as a clean segmented control.
    Text color is forced black via a page-level <style> tag that
    beats Streamlit emotion CSS by targeting the element directly.
    Returns bool: False = label_off, True = label_on.
    """
    raw = st.session_state.get(widget_key)
    if raw is None:
        val = default
    elif isinstance(raw, bool):
        val = raw
    else:
        val = (str(raw) == label_on)

    selected = st.radio(
        label=title if title else f"{label_off} / {label_on}",
        options=[label_off, label_on],
        index=1 if val else 0,
        key=widget_key,
        horizontal=True,
    )

    return selected == label_on


_ensure_admin_page_state()
User.seed_default_users()

st.markdown("""
<style>
/* ── Radio label text: always black, readable ── */
[data-testid="stRadio"] label p {
    color: #1c1c1c !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 16px !important;
    font-weight: 600 !important;
}
[data-testid="stRadio"] label {
    color: #1c1c1c !important;
}
/* ── Radio field title: "Role" / "Account Status" ── */
[data-testid="stRadio"] > label {
    font-family: 'Capriola', sans-serif !important;
    font-size: 18px !important;
    color: #4d4d4d !important;
    font-weight: 400 !important;
    margin-bottom: 4px !important;
}
/* ── Toggle status badge ── */
.toggle-status-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    color: #555567;
    margin-top: 4px;
    margin-bottom: 8px;
    padding: 6px 12px;
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 8px;
}
.tsb-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
    display: inline-block;
}
.tsb-dot-blue  { background: #0070FF; }
.tsb-dot-green { background: #23935b; }
.tsb-dot-grey  { background: #aaaabc; }

.page-shell { position: relative; z-index: 2; }

.main .block-container {
    max-width: 1440px;
    padding-top: 0.8rem;
    padding-bottom: 1.6rem;
}

.page-top-space { height: 10px; }
.top-nav-wrap { margin-bottom: 18px; }

.top-nav-wrap div.stButton > button {
    min-height: 44px;
    border-radius: 12px;
    font-size: 16px;
    box-shadow: 0 8px 16px rgba(0,112,255,0.14);
}

.page-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(34px, 3vw, 46px);
    color: #303149;
    text-align: center;
    margin-bottom: 8px;
    line-height: 1.1;
}

.page-subtitle {
    font-family: 'Capriola', sans-serif;
    font-size: 16px;
    color: #5E5B5B;
    text-align: center;
    margin-bottom: 36px;
}

section.main div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.76) !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: 22px !important;
    box-shadow: 0 10px 28px rgba(0,0,0,0.04) !important;
    backdrop-filter: blur(8px) !important;
    padding: 14px 28px 24px 28px !important;
    overflow: hidden !important;
}

section.main div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: transparent !important;
}

.section-title {
    font-family: 'Capriola', sans-serif;
    font-size: 18px;
    color: #313149;
    margin-top: 8px;
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(0,0,0,0.08);
}

.field-label {
    font-family: 'Capriola', sans-serif;
    font-size: 18px;
    color: #4d4d4d;
    margin-top: 6px;
    margin-bottom: 6px;
}

.field-help {
    font-family: 'Capriola', sans-serif;
    font-size: 11px;
    color: #9a9a9a;
    margin-top: 6px;
    margin-bottom: 6px;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background: #FAFAFA !important;
    color: #3a3a3a !important;
    border: 1px solid rgba(0,0,0,0.13) !important;
    border-radius: 10px !important;
    min-height: 72px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 14px !important;
    padding-left: 16px !important;
    padding-top: 14px !important;
    box-shadow: none !important;
    transition: border-color 0.15s ease !important;
    resize: none !important;
    line-height: 1.6 !important;
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(0,112,255,0.4) !important;
    background: #FFFFFF !important;
    box-shadow: 0 0 0 3px rgba(0,112,255,0.07) !important;
}

div[data-testid="stTextInput"] label,
div[data-testid="stTextArea"] label { display: none !important; }

div.stButton > button {
    background: #0070FF;
    color: white;
    border: none;
    border-radius: 10px;
    min-height: 48px;
    font-family: 'Capriola', sans-serif;
    font-size: 15px;
    box-shadow: 0 8px 18px rgba(0,112,255,0.18);
    width: 100%;
}

div.stButton > button:hover { background: #005fe0; color: white; }

.feedback-banner {
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 14px;
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

.search-wrap { padding-top: 4px; }

.stat-chip {
    background: rgba(255,255,255,0.86);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 14px;
    padding: 10px 14px;
    min-height: 66px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.stat-meta { font-family: 'Capriola', sans-serif; line-height: 1.2; }
.stat-label { color: #7a7a7a; font-size: 12px; }
.stat-value { color: #303149; font-size: 24px; margin-top: 4px; }

.table-head, .table-cell { font-family: 'Capriola', sans-serif; }

.table-head {
    color: #4a4a5a;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    background: rgba(245,245,250,0.95);
    border-top: 1px solid rgba(0,0,0,0.09);
    border-bottom: 1px solid rgba(0,0,0,0.09);
    padding: 12px 10px 13px 10px;
}

.table-cell {
    color: #454545;
    font-size: 14px;
    padding: 12px 10px;
    border-bottom: 1px solid rgba(0,0,0,0.04);
    line-height: 1.4;
}

.table-first { border-left: 1px solid rgba(0,0,0,0.08) !important; }
.table-last  { border-right: 1px solid rgba(0,0,0,0.08) !important; }

.action-btn-wrap div.stButton > button,
.stApp .action-btn-wrap div.stButton > button {
    background: rgba(235,235,240,0.95) !important;
    color: #555567 !important;
    border: 1px solid rgba(0,0,0,0.10) !important;
    box-shadow: none !important;
    font-size: 13px !important;
    min-height: 34px !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}

.action-btn-wrap div.stButton > button:hover,
.stApp .action-btn-wrap div.stButton > button:hover {
    background: rgba(218,218,226,0.98) !important;
    color: #303149 !important;
    border-color: rgba(0,0,0,0.16) !important;
    box-shadow: none !important;
}

.role-badge, .status-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    font-family: 'Capriola', sans-serif;
    font-size: 12px;
    padding: 5px 12px;
    white-space: nowrap;
}

.role-admin   { background: rgba(255,152,0,0.14);   color: #e67817; border: 1px solid rgba(255,152,0,0.32); }
.role-analyst { background: rgba(0,112,255,0.10);   color: #0070FF; border: 1px solid rgba(0,112,255,0.24); }
.status-active   { background: rgba(66,200,122,0.12);  color: #23935b; border: 1px solid rgba(66,200,122,0.28); }
.status-inactive { background: rgba(120,120,120,0.10); color: #767676; border: 1px solid rgba(120,120,120,0.20); }

.empty-state {
    text-align: center;
    padding: 26px 0 6px 0;
    font-family: 'Capriola', sans-serif;
    color: #9d9d9d;
    font-size: 14px;
}

.edit-panel-box {
    background: rgba(255,255,255,0.56);
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 18px;
    padding: 20px 18px 10px 18px;
    margin-bottom: 14px;
}

.edit-panel-title {
    font-family: 'Capriola', sans-serif;
    font-size: 16px;
    color: #303149;
    margin-bottom: 12px;
}

.small-note {
    font-family: 'Capriola', sans-serif;
    font-size: 12px;
    color: #8b8b8b;
    margin-top: 4px;
}

.footer-space { height: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-shell">', unsafe_allow_html=True)
st.markdown('<div class="page-top-space"></div>', unsafe_allow_html=True)

left_nav, nav1, nav2 = st.columns([9.6, 1.2, 1.2])
with nav1:
    if st.button("Home", use_container_width=True, key="nav_home"):
        st.switch_page("pages/2_Home.py")
with nav2:
    if st.button("Logout", use_container_width=True, key="nav_logout"):
        for key in ["logged_in", "username", "user_email", "user_role"]:
            st.session_state.pop(key, None)
        st.switch_page("pages/1_Login.py")

st.markdown('<div class="page-title">Add New User</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Create and manage analyst accounts for the WAHHAJ platform</div>',
    unsafe_allow_html=True,
)

# ── Account status change notification (top of page) ──────────────────
status_change_msg = st.session_state.pop("status_change_msg", None)
if status_change_msg:
    st.markdown(
        f'''<div style="
            max-width: 600px;
            margin: 0 auto 18px auto;
            background: rgba(0,112,255,0.08);
            border: 1px solid rgba(0,112,255,0.25);
            border-radius: 12px;
            padding: 12px 20px;
            font-family: 'Capriola', sans-serif;
            font-size: 14px;
            color: #0050bb;
            text-align: center;
        ">💡 {status_change_msg}</div>''',
        unsafe_allow_html=True,
    )

page_left, center, page_right = st.columns([1.8, 6.4, 1.8])

with center:
    feedback_message = st.session_state.get("user_feedback")
    feedback_kind = st.session_state.get("user_feedback_type", "success")
    if feedback_message:
        feedback_cls = "feedback-success" if feedback_kind == "success" else "feedback-error"
        st.markdown(
            f'<div class="feedback-banner {feedback_cls}">{feedback_message}</div>',
            unsafe_allow_html=True,
        )

    panel_left, panel_gap, panel_right = st.columns([1, 0.12, 1.6])

    with panel_left:
        with st.container(border=True):
            st.markdown('<div class="section-title">New User Details</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2, gap="large")
            with col1:
                st.markdown('<div class="field-label">Full Name</div>', unsafe_allow_html=True)
                new_name = st.text_area("Full Name", label_visibility="collapsed", key="inp_name", height=60)
            with col2:
                st.markdown('<div class="field-label">Username</div>', unsafe_allow_html=True)
                new_username = st.text_area("Username", label_visibility="collapsed", key="inp_username", height=60)

            st.markdown('<div class="field-label">Email Address</div>', unsafe_allow_html=True)
            new_email = st.text_area("Email", label_visibility="collapsed", key="inp_email", height=60)

            st.markdown('<div class="field-label">Password</div>', unsafe_allow_html=True)
            new_password = st.text_input("Password", type="password", label_visibility="collapsed", key="inp_pw")


            st.markdown('<div class="field-label">Confirm Password</div>', unsafe_allow_html=True)
            confirm_password = st.text_input("Confirm Password", type="password", label_visibility="collapsed", key="inp_pw2")


            # ── Role ───────────────────
            role_is_admin = _styled_toggle("inp_role", "Analyst", "Admin", default=False, title="Role")
            role_choice = "Admin" if role_is_admin else "Analyst"


            # ── Account Status ───────────────────
            status_is_active = _styled_toggle("inp_status", "Active", "Inactive", default=True, title="Account Status")
            account_status = "Active" if status_is_active else "Inactive"


            st.write("")

            b1, b2 = st.columns(2, gap="large")
            with b1:
                clear_clicked = st.button("Clear", use_container_width=True, key="btn_clear")
            with b2:
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
                role = UserRole.ADMIN if role_is_admin else UserRole.ANALYST
                new_user = User(
                    name=new_name.strip(),
                    email=email_candidate,
                    role=role,
                    hashed_password=new_password,
                    is_active=status_is_active,
                )
                admin_user = _current_admin()
                if admin_user and admin_user.role == UserRole.ADMIN:
                    admin_user.addUser(new_user)
                else:
                    User._user_registry[new_user.userId] = new_user

                _set_feedback(
                    f"<strong>{new_name.strip()}</strong> created successfully as "
                    f"<strong>{role_choice}</strong> with status <strong>{account_status}</strong>."
                )

                for key in ["inp_name", "inp_username", "inp_email", "inp_pw", "inp_pw2"]:
                    st.session_state[key] = ""
                st.session_state["inp_role"] = "Analyst"
                st.session_state["inp_status"] = "Active"
                st.rerun()
            except Exception as exc:
                _set_feedback(f"Could not create user: {exc}", "error")
                st.rerun()

    with panel_gap:
        st.write("")

    with panel_right:
        all_users = list(User._user_registry.values())
        visible_users = _matching_users(all_users, st.session_state.get("add_user_search", ""))
        total_users = len(all_users)
        active_users = sum(1 for user in all_users if user.is_active)
        admin_count = sum(1 for user in all_users if user.role == UserRole.ADMIN)

        with st.container(border=True):
            st.markdown('<div class="section-title">Existing Users</div>', unsafe_allow_html=True)

            if st.session_state.get("show_edit_panel") and st.session_state.get("edit_user_id"):
                st.markdown('<div class="edit-panel-box">', unsafe_allow_html=True)
                st.markdown('<div class="edit-panel-title">Edit User</div>', unsafe_allow_html=True)

                e1, e2 = st.columns(2, gap="large")
                with e1:
                    st.markdown('<div class="field-label">Full Name</div>', unsafe_allow_html=True)
                    st.text_area("Edit Full Name", key="edit_name", label_visibility="collapsed", height=60)
                with e2:
                    st.markdown('<div class="field-label">Email Address</div>', unsafe_allow_html=True)
                    st.text_area("Edit Email", key="edit_email", label_visibility="collapsed", height=60)

                e3, e4 = st.columns(2, gap="large")
                with e3:
                    st.markdown('<div class="field-label">Role</div>', unsafe_allow_html=True)
                    _styled_toggle("edit_role", "Analyst", "Admin", default=False, title="Role")
                with e4:
                    st.markdown('<div class="field-label">Account Status</div>', unsafe_allow_html=True)
                    _styled_toggle("edit_status", "Active", "Inactive", default=True, title="Account Status")

                save_col, cancel_col = st.columns(2, gap="large")
                with save_col:
                    save_edit = st.button("Save Changes", use_container_width=True, key="save_edit_btn")
                with cancel_col:
                    cancel_edit = st.button("Cancel", use_container_width=True, key="cancel_edit_btn")

                st.markdown('</div>', unsafe_allow_html=True)

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
                            target.role = UserRole.ADMIN if st.session_state["edit_role"] == "Admin" else UserRole.ANALYST
                            target.is_active = (st.session_state["edit_status"] == "Active")
                            _set_feedback(f"Changes saved for <strong>{target.name}</strong>.")
                            _close_edit_panel()
                    st.rerun()

                if cancel_edit:
                    _close_edit_panel()
                    st.rerun()

            utility_left, utility_gap, utility_right = st.columns([4.6, 0.4, 5.0])
            with utility_left:
                st.markdown('<div class="search-wrap">', unsafe_allow_html=True)
                st.text_input("Search users", key="add_user_search", label_visibility="collapsed")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("""
<style>
.stApp .action-btn-wrap div.stButton > button {
    background: rgba(235,235,240,0.95) !important;
    color: #555567 !important;
    border: 1px solid rgba(0,0,0,0.10) !important;
    box-shadow: none !important;
    font-size: 13px !important;
    min-height: 34px !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stApp .action-btn-wrap div.stButton > button:hover {
    background: rgba(218,218,226,0.98) !important;
    color: #303149 !important;
    border-color: rgba(0,0,0,0.16) !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

            with utility_right:
                s1, s2, s3 = st.columns(3, gap="small")
                with s1:
                    st.markdown(
                        f'<div class="stat-chip"><div class="stat-meta"><div class="stat-label">Total Users</div><div class="stat-value">{total_users}</div></div></div>',
                        unsafe_allow_html=True,
                    )
                with s2:
                    st.markdown(
                        f'<div class="stat-chip"><div class="stat-meta"><div class="stat-label">Active</div><div class="stat-value">{active_users}</div></div></div>',
                        unsafe_allow_html=True,
                    )
                with s3:
                    st.markdown(
                        f'<div class="stat-chip"><div class="stat-meta"><div class="stat-label">Admins</div><div class="stat-value">{admin_count}</div></div></div>',
                        unsafe_allow_html=True,
                    )

            st.write("")

            if not visible_users:
                st.markdown('<div class="empty-state">No users match your search. Try a different name, email, or role.</div>', unsafe_allow_html=True)
            else:
                widths = [1.5, 2.2, 1.0, 1.0, 1.2, 6.1]
                h1, h2, h3, h4, h5, h6 = st.columns(widths)
                header_cols = [h1, h2, h3, h4, h5, h6]
                headers = ["Name", "Email", "Role", "Status", "User ID", "Actions"]
                for i, (header, col) in enumerate(zip(headers, header_cols)):
                    extra = " table-first" if i == 0 else (" table-last" if i == len(headers) - 1 else "")
                    with col:
                        st.markdown(f'<div class="table-head{extra}">{header}</div>', unsafe_allow_html=True)

                for user in visible_users:
                    c1, c2, c3, c4, c5, c6 = st.columns(widths)
                    short_id = f"{str(user.userId)[:8]}..."

                    with c1:
                        st.markdown(f'<div class="table-cell table-first">{user.name}</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="table-cell">{user._email}</div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown(f'<div class="table-cell">{_role_badge(user.role)}</div>', unsafe_allow_html=True)
                    with c4:
                        st.markdown(f'<div class="table-cell">{_status_badge(user.is_active)}</div>', unsafe_allow_html=True)
                    with c5:
                        st.markdown(f'<div class="table-cell" style="color:#8c8c8c;">{short_id}</div>', unsafe_allow_html=True)
                    with c6:
                        st.markdown('<div class="table-cell table-last action-btn-wrap">', unsafe_allow_html=True)
                        action_cols = st.columns([1.0, 1.4, 1.0], gap="small")
                        with action_cols[0]:
                            if st.button("Edit", key=f"tbl_edit_{user.userId}", use_container_width=True):
                                _open_edit_panel(user)
                                st.rerun()
                        with action_cols[1]:
                            toggle_label = "Deactivate" if user.is_active else "Activate"
                            if st.button(toggle_label, key=f"tbl_toggle_{user.userId}", use_container_width=True):
                                user.is_active = not user.is_active
                                state_word = "activated" if user.is_active else "deactivated"
                                _set_feedback(f"<strong>{user.name}</strong> was {state_word}.")
                                st.rerun()
                        with action_cols[2]:
                            if st.button("Delete", key=f"tbl_delete_{user.userId}", use_container_width=True):
                                admin_user = _current_admin()
                                try:
                                    if admin_user and admin_user.role == UserRole.ADMIN:
                                        admin_user.removeUser(user.userId)
                                    else:
                                        User._user_registry.pop(user.userId, None)
                                    _set_feedback(f"<strong>{user.name}</strong> was deleted.")
                                    if st.session_state.get("edit_user_id") == user.userId:
                                        _close_edit_panel()
                                except Exception as exc:
                                    _set_feedback(f"Could not delete user: {exc}", "error")
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="footer-space"></div>', unsafe_allow_html=True)
    render_footer()

st.markdown('</div>', unsafe_allow_html=True)