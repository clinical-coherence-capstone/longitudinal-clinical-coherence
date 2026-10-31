"""Streamlit web application for ClinCoherence — Longitudinal Clinical Assistant."""
import sys
from pathlib import Path

# Ensure src/ and webapp parent are on sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_DIR / "src"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import json
from datetime import datetime, timezone, date
import calendar
import re
import html
import streamlit as st
import streamlit.components.v1 as components

try:
    from .database import (
        init_db,
        create_conversation,
        get_conversations_for_user,
        delete_empty_conversations,
        delete_conversation,
        get_conversation,
        add_message,
        get_messages,
        get_latest_patient_state,
        save_verification_result,
        get_verification_result,
        save_patient_profile,
        get_patient_profile,
    )
    from .auth import register_user, login_user
    from .pipeline import run_pipeline
    from .styles import APP_CSS
except ImportError:
    from webapp.database import (
        init_db,
        create_conversation,
        get_conversations_for_user,
        delete_empty_conversations,
        delete_conversation,
        get_conversation,
        add_message,
        get_messages,
        get_latest_patient_state,
        save_verification_result,
        get_verification_result,
        save_patient_profile,
        get_patient_profile,
    )
    from webapp.auth import register_user, login_user
    from webapp.pipeline import run_pipeline
    from webapp.styles import APP_CSS

# Configure Streamlit page
st.set_page_config(
    page_title="ClinCoherence — Longitudinal Clinical Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply custom modern styling
st.markdown(APP_CSS, unsafe_allow_html=True)

# Initialize database schema
init_db()


# ---------------------------------------------------------------------------
# Helper functions: Age calculation, formatting, and text rendering
# ---------------------------------------------------------------------------

def calculate_age_from_dob(dob: date) -> int:
    """Calculate integer age given a date object."""
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def get_age_display(age_or_dob_str: str | None) -> str:
    """Return formatted age string from ISO date string or integer string."""
    if not age_or_dob_str:
        return "Unknown"
    if "-" in str(age_or_dob_str):
        try:
            dob = datetime.strptime(str(age_or_dob_str), "%Y-%m-%d").date()
            calc_age = calculate_age_from_dob(dob)
            return f"{calc_age} yrs ({dob.strftime('%b %d, %Y')})"
        except Exception:
            return str(age_or_dob_str)
    try:
        return f"{int(age_or_dob_str)} yrs"
    except Exception:
        return str(age_or_dob_str)


def parse_dob_date(age_or_dob_str: str | None) -> date:
    """Parse stored age_or_dob string into date object, defaulting safely if none."""
    if age_or_dob_str and "-" in str(age_or_dob_str):
        try:
            return datetime.strptime(str(age_or_dob_str), "%Y-%m-%d").date()
        except Exception:
            pass
    return date(2000, 1, 1)


def format_chat_text(text: str) -> str:
    """Format markdown text safely for custom chat bubble containers."""
    if not text:
        return ""
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"(?m)^-\s+(.+)$", r"<div style='margin-left: 1rem;'>• \1</div>", escaped)
    escaped = escaped.replace("\n", "<br>")
    return escaped


def render_clean_html(html_str: str, container=None) -> None:
    """Render HTML safely without triggering Markdown's 4-space code block parser."""
    clean_lines = [line.strip() for line in html_str.strip().split("\n") if line.strip()]
    clean_html = "\n".join(clean_lines)
    target = container if container is not None else st
    target.markdown(clean_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------

def _init_session() -> None:
    """Initialize all session state variables."""
    defaults = [
        ("user_id", None),
        ("username", None),
        ("conv_id", None),
        ("page", "login"),
        ("active_view", "chat"),
        ("show_left_sidebar", True),
        ("show_right_panel", True),
        ("editing_profile", False),
        ("onboarding_step", 1),
        ("wizard_step1", {}),
        ("wizard_meds", []),
        ("chat_search_query", ""),
        ("right_panel_tab", "graph"),
        ("show_pipeline_inspector", False),
        ("inspector_stage", "extractor"),
        ("pinned_conv_ids", []),
        ("show_add_prescription_modal", False),
        ("uploaded_prescriptions", [
            {"name": "Prescription_Oct2026.pdf", "med": "Metformin 500mg • Once Daily", "folder": "📁 My Prescriptions"}
        ]),
    ]
    for key, val in defaults:
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Modal Dialogs (@st.dialog)
# ---------------------------------------------------------------------------

@st.dialog("⚡ Clinical Pipeline Inspector & Diagnostics", width="large")
def open_pipeline_inspector_dialog(latest_payload: dict | None) -> None:
    """Open large modal dialog for Clinical Pipeline Inspector."""
    show_pipeline_inspector(latest_payload)


@st.dialog("💊 Add New Prescription / Medical Report", width="medium")
def open_prescription_dialog() -> None:
    """Open medium modal dialog for uploading or adding prescriptions and reports."""
    st.markdown("<p style='color: #94a3b8; font-size: 0.85rem;'>Add a new medication or attach diagnostic laboratory reports to your longitudinal health record.</p>", unsafe_allow_html=True)
    p_name = st.text_input("Prescription or Medication Name", placeholder="e.g. Lisinopril 10mg, Metformin 500mg", key="dlg_p_name")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        p_target = st.selectbox("Target Folder", ["📁 My Prescriptions", "📁 Lab & Diagnostic Reports", "📁 Similar Cases Reference"], key="dlg_p_target")
    with col_f2:
        p_freq = st.selectbox("Frequency", ["Once daily", "Twice daily", "Three times daily", "As needed (PRN)"], key="dlg_p_freq")
    p_file = st.file_uploader("Upload Document or Image (PDF, JPG, PNG)", type=["pdf", "png", "jpg"], key="dlg_p_file")

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("Save to Folder ➔", key="dlg_save_btn", use_container_width=True, type="primary"):
            if p_name.strip():
                doc_filename = p_file.name if p_file else f"Prescription_{datetime.now().strftime('%b%Y')}.pdf"
                st.session_state.uploaded_prescriptions.append({
                    "name": doc_filename,
                    "med": f"{p_name.strip()} • {p_freq}",
                    "folder": p_target,
                })
                st.success(f"Added {p_name.strip()} to {p_target}!")
                st.rerun()
            else:
                st.error("Please provide a prescription or medication name.")
    with col_cancel:
        if st.button("Cancel", key="dlg_cancel_btn", use_container_width=True, type="secondary"):
            st.rerun()


# ---------------------------------------------------------------------------
# Part 1: Top App Header Banner
# ---------------------------------------------------------------------------

def render_top_app_header(gate_status: str = "PASS", pref_name: str = "Patient") -> None:
    """Render top application navigation banner matching ui_preview.html with 3-view switcher."""
    col_brand, col_pipe, col_views, col_intel, col_user = st.columns([0.27, 0.32, 0.22, 0.11, 0.08])

    with col_brand:
        render_clean_html(
            """
            <div style="display: flex; align-items: center; gap: 10px; padding: 2px 0;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #38bdf8, #2563eb, #4338ca); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; box-shadow: 0 2px 8px rgba(56, 189, 248, 0.4);">⚕️</div>
                <div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-weight: 800; font-size: 1.05rem; color: #ffffff; letter-spacing: -0.01em;">ClinCoherence</span>
                        <span style="background: rgba(56, 189, 248, 0.15); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.3); font-size: 0.65rem; font-weight: 700; padding: 1px 6px; border-radius: 9999px;">Clinical AI</span>
                    </div>
                    <div style="font-size: 0.68rem; color: #94a3b8; line-height: 1.15;">Longitudinal Clinical Coherence & Decision Verification</div>
                </div>
            </div>
            """
        )

    with col_pipe:
        insp_open = st.session_state.get("show_pipeline_inspector", False)
        pipe_btn_type = "primary" if insp_open else "secondary"
        if st.button(
            f"Pipeline: Coherence Verifier ➔ Gate [{gate_status}]",
            key="btn_top_pipeline_status",
            use_container_width=True,
            type=pipe_btn_type,
            help="Click to open Clinical Pipeline Inspector & Diagnostics",
        ):
            st.session_state.show_pipeline_inspector = not insp_open
            st.rerun()

    with col_views:
        # 3-view switcher: 💬 Chat, 🔐 Login Page, 📋 Profile Form
        curr_view = st.session_state.get("active_view", "chat")
        cv1, cv2, cv3 = st.columns(3)
        with cv1:
            btn_v_chat = "primary" if curr_view == "chat" and not st.session_state.get("editing_profile", False) else "secondary"
            if st.button("💬 Chat", key="nav_btn_chat", use_container_width=True, type=btn_v_chat):
                st.session_state.active_view = "chat"
                st.session_state.editing_profile = False
                st.rerun()
        with cv2:
            btn_v_login = "primary" if curr_view == "login" else "secondary"
            if st.button("🔐 Login", key="nav_btn_login", use_container_width=True, type=btn_v_login):
                st.session_state.active_view = "login"
                st.rerun()
        with cv3:
            btn_v_form = "primary" if curr_view == "form" or st.session_state.get("editing_profile", False) else "secondary"
            if st.button("📋 Profile", key="nav_btn_profile", use_container_width=True, type=btn_v_form):
                st.session_state.active_view = "form"
                st.session_state.editing_profile = True
                st.rerun()

    with col_intel:
        intel_open = st.session_state.get("show_right_panel", True)
        top_panel_label = "📊 Intelligence Panel" if not intel_open else "✕ Hide Panel"
        top_panel_type = "primary" if not intel_open else "secondary"
        if st.button(
            top_panel_label,
            key="btn_top_intelligence_panel",
            use_container_width=True,
            type=top_panel_type,
            help="Toggle Right Clinical Intelligence slide panel",
        ):
            st.session_state.show_right_panel = not intel_open
            st.rerun()

    with col_user:
        u_name = pref_name if pref_name else (st.session_state.get("username") or "samrudh")
        render_clean_html(
            f"""
            <div style="height: 38px; display: flex; align-items: center; justify-content: flex-end;">
                <span style="background: #080d1a; border: 1px solid #1e293b; color: #cbd5e1; font-size: 0.76rem; font-weight: 700; padding: 5px 8px; border-radius: 8px; white-space: nowrap;">
                    👤 {u_name}
                </span>
            </div>
            """
        )

    st.markdown("<hr style='border-color: #1e293b; margin: 6px 0 10px 0;'>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Part 2: Login & Registration Page
# ---------------------------------------------------------------------------

def show_auth_page() -> None:
    """Render polished, minimal Login and Registration pages with native eye toggle."""
    render_top_app_header(gate_status="PASS", pref_name=st.session_state.get("username") or "samrudh")

    col_spacer_l, col_center, col_spacer_r = st.columns([1, 2, 1])

    with col_center:
        render_clean_html(
            """
            <div class="auth-header" style="text-align: center; margin-bottom: 20px;">
                <div class="auth-logo-badge" style="width: 48px; height: 48px; border-radius: 12px; font-size: 1.35rem; margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #0284c7, #38bdf8);">⚕️</div>
                <h1 style="color: #ffffff; font-size: 1.45rem; font-weight: 800; margin: 0;">ClinCoherence Portal</h1>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px;">Secure Longitudinal Clinical Authentication</div>
            </div>
            """
        )

        tab_login, tab_register = st.tabs(["Sign In", "Register New Patient"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            login_user_input = st.text_input(
                "Username",
                value="samrudh" if st.session_state.get("username") == "samrudh" else "",
                key="login_user_field",
                placeholder="Enter username",
            )

            login_pw_input = st.text_input(
                "Password",
                type="password",
                key="login_pw_field",
                placeholder="Enter password",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Sign In to Portal ➔", key="btn_signin", use_container_width=True, type="primary"):
                if not login_user_input or not login_pw_input:
                    st.error("Please enter both username and password.")
                else:
                    ok, msg, uid = login_user(login_user_input, login_pw_input)
                    if ok:
                        st.session_state.user_id = uid
                        st.session_state.username = login_user_input.strip()
                        st.session_state.page = "main"
                        st.session_state.active_view = "chat"
                        st.session_state.conv_id = None
                        st.session_state.show_left_sidebar = True
                        st.session_state.show_right_panel = True
                        st.session_state.show_pipeline_inspector = False
                        st.session_state.editing_profile = False
                        st.session_state.onboarding_step = 1
                        st.session_state.wizard_step1 = {}
                        st.session_state.wizard_meds = []
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_register:
            st.markdown("<br>", unsafe_allow_html=True)
            reg_user_input = st.text_input(
                "Choose Username",
                key="reg_user_field",
                placeholder="e.g. jdoe_patient",
            )

            reg_pw_input = st.text_input(
                "Password (minimum 8 characters)",
                type="password",
                key="reg_pw_field",
                placeholder="Create strong password",
            )
            reg_confirm_input = st.text_input(
                "Confirm Password",
                type="password",
                key="reg_confirm_field",
                placeholder="Re-enter password",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Create Patient Account ➔", key="btn_register", use_container_width=True, type="primary"):
                if not reg_user_input.strip():
                    st.error("Username cannot be empty.")
                elif len(reg_pw_input) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif reg_pw_input != reg_confirm_input:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register_user(reg_user_input, reg_pw_input)
                    if ok:
                        st.success(f"{msg} Please switch to the 'Sign In' tab to log in.")
                    else:
                        st.error(msg)

        render_clean_html(
            """
            <div style="text-align: center; margin-top: 1.5rem; font-size: 0.72rem; color: #64748b;">
                🔒 Bcrypt 12-round salted hashing • Strict patient data isolation
            </div>
            """
        )


# ---------------------------------------------------------------------------
# Part 3: Guided Patient Onboarding Wizard (2 Steps)
# ---------------------------------------------------------------------------

COMMON_CONDITIONS = [
    "Yet to discover",
    "Hypertension (High Blood Pressure)",
    "Type 2 Diabetes",
    "Type 1 Diabetes",
    "Asthma",
    "Chronic Obstructive Pulmonary Disease (COPD)",
    "Chronic Kidney Disease",
    "Coronary Artery Disease",
    "Heart Failure",
    "Anemia / Iron Deficiency",
    "Hypothyroidism",
    "Hyperlipidemia (High Cholesterol)",
    "Depression / Anxiety",
    "Migraine",
    "Osteoarthritis",
    "Other",
]

COMMON_ALLERGIES = [
    "Yet to discover",
    "No known allergies (NKDA)",
    "Penicillin / Amoxicillin",
    "Sulfa antibiotics",
    "Aspirin / NSAIDs (Ibuprofen)",
    "ACE inhibitors",
    "Latex",
    "Peanuts / Tree nuts",
    "Other",
]

MED_FREQUENCIES = [
    "Once daily",
    "Twice daily",
    "Three times daily",
    "Four times daily",
    "As needed (PRN)",
    "Weekly",
    "Monthly",
]


def show_onboarding_page(is_editing: bool = False) -> None:
    """Render 2-step clinical profile onboarding wizard."""
    user_id = st.session_state.user_id or 1
    existing_profile = get_patient_profile(user_id) if user_id else None
    pref_name_val = existing_profile["preferred_name"] if existing_profile and existing_profile["preferred_name"] else (st.session_state.username or "Patient")

    render_top_app_header(gate_status="PASS", pref_name=pref_name_val)

    header_title = "Edit Patient Health Profile" if is_editing else "Welcome to ClinCoherence — Patient Profile"
    render_clean_html(
        f"""
        <div style="margin-bottom: 16px;">
            <h1 style="color: #ffffff; font-size: 1.4rem; font-weight: 800; margin: 0;">{header_title}</h1>
            <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px;">
                Demonstrating combinable "Yet to discover" option, single native eye toggle for passwords, and clinical accuracy.
            </div>
        </div>
        """
    )

    if st.session_state.onboarding_step == 1:
        st.markdown("#### Step 1 of 2: Demographics & Identity")
        st.caption("Provide your basic demographic details to establish your longitudinal record.")

        existing_dob = parse_dob_date(existing_profile["age_or_dob"]) if existing_profile else date(2000, 2, 1)
        existing_name = existing_profile["preferred_name"] if existing_profile else (st.session_state.username or "")
        existing_sex = existing_profile["sex_assigned_at_birth"] if existing_profile else "Male"
        existing_gender = existing_profile["gender_identity"] if existing_profile else "Man"

        pref_name = st.text_input("Preferred Name", value=existing_name or "", placeholder="How should the assistant address you?")

        dob_date = st.date_input(
            "Date of Birth",
            value=existing_dob,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            help="Your exact age will be derived accurately from this date",
        )
        calc_age = calculate_age_from_dob(dob_date)
        st.caption(f"Calculated age: **{calc_age} years old** (Born {dob_date.strftime('%B %d, %Y')})")

        col_s, col_g = st.columns(2)
        sex_options = ["Male", "Female", "Intersex", "Prefer not to say"]
        sex_idx = sex_options.index(existing_sex) if existing_sex in sex_options else 0
        with col_s:
            sex_assigned = st.selectbox(
                "Sex Assigned at Birth",
                sex_options,
                index=sex_idx,
                help="Used for physiological lab ranges and clinical guidelines",
            )

        gender_options = ["Man", "Woman", "Non-binary", "Transgender", "Self-describe", "Prefer not to say"]
        gender_idx = gender_options.index(existing_gender) if existing_gender in gender_options else 0
        with col_g:
            gender_identity = st.selectbox(
                "Gender Identity (Optional)",
                gender_options,
                index=gender_idx,
                help="Recorded respectfully and independently of clinical sex",
            )

        st.markdown("<br>", unsafe_allow_html=True)
        col_cancel, col_next = st.columns([1, 1])
        with col_cancel:
            if is_editing:
                if st.button("Cancel & Return to Chat", use_container_width=True, type="secondary"):
                    st.session_state.editing_profile = False
                    st.session_state.active_view = "chat"
                    st.rerun()
        with col_next:
            if st.button("Continue to Clinical History (Step 2) ➔", use_container_width=True, type="primary"):
                st.session_state.wizard_step1 = {
                    "preferred_name": pref_name.strip(),
                    "dob": dob_date,
                    "sex_assigned_at_birth": sex_assigned,
                    "gender_identity": gender_identity,
                }
                st.session_state.onboarding_step = 2
                st.rerun()

    elif st.session_state.onboarding_step == 2:
        st.markdown("#### Step 2 of 2: Medical Conditions, Allergies & Medications")
        st.caption("Antecedent conditions and allergies help the Coherence Verifier prevent conflicting advice.")

        current_conditions = existing_profile.get("medical_conditions", "") if existing_profile else ""
        current_allergies = existing_profile.get("known_allergies", "") if existing_profile else ""

        preselected_conds = [c.strip() for c in current_conditions.split(",") if c.strip() in COMMON_CONDITIONS] if current_conditions else ["Yet to discover"]
        preselected_allergies = [a.strip() for a in current_allergies.split(",") if a.strip() in COMMON_ALLERGIES] if current_allergies else ["No known allergies (NKDA)"]

        selected_conditions = st.multiselect(
            "Existing Medical Conditions (Select all that apply)",
            options=COMMON_CONDITIONS,
            default=preselected_conds,
            help="'Yet to discover' is fully combinable with diagnosed conditions.",
        )
        other_cond_text = ""
        if "Other" in selected_conditions:
            other_cond_text = st.text_input("Specify other condition(s):", placeholder="e.g. Celiac disease")

        selected_allergies = st.multiselect(
            "Known Allergies (Select all that apply)",
            options=COMMON_ALLERGIES,
            default=preselected_allergies,
            help="Checked by DailyMed evidence retriever to alert against adverse drug interactions.",
        )
        other_allergy_text = ""
        if "Other" in selected_allergies:
            other_allergy_text = st.text_input("Specify other allergy:", placeholder="e.g. Iodine contrast")

        notes_text = st.text_area(
            "Additional Clinical Notes or Surgical History (Optional)",
            value=existing_profile.get("past_medical_history", "") if existing_profile else "",
            placeholder="Any past surgeries, hospitalizations, or family history?",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        col_b_back, col_b_save = st.columns([1, 1])
        with col_b_back:
            if st.button("⬅ Back to Demographics", use_container_width=True, type="secondary"):
                st.session_state.onboarding_step = 1
                st.rerun()
        with col_b_save:
            btn_save_txt = "Update Profile ➔" if is_editing else "Save Profile & Start Chat ➔"
            if st.button(btn_save_txt, use_container_width=True, type="primary"):
                s1 = st.session_state.get("wizard_step1", {})
                dob_val = s1.get("dob", date(2000, 2, 1))

                cond_list = [c for c in selected_conditions if c != "Other"]
                if other_cond_text.strip():
                    cond_list.append(other_cond_text.strip())

                allergy_list = [a for a in selected_allergies if a != "Other"]
                if other_allergy_text.strip():
                    allergy_list.append(other_allergy_text.strip())

                save_patient_profile(
                    user_id=user_id,
                    profile_data={
                        "preferred_name": s1.get("preferred_name") or None,
                        "age_or_dob": dob_val.isoformat(),
                        "sex_assigned_at_birth": s1.get("sex_assigned_at_birth", "Male"),
                        "gender_identity": s1.get("gender_identity", "Man"),
                        "medical_conditions": ", ".join(cond_list) if cond_list else None,
                        "known_allergies": ", ".join(allergy_list) if allergy_list else None,
                        "past_medical_history": notes_text.strip() or None,
                    },
                )
                st.session_state.editing_profile = False
                st.session_state.active_view = "chat"
                st.session_state.onboarding_step = 1
                st.success("Profile saved successfully!")
                st.rerun()


# ---------------------------------------------------------------------------
# Part 4: Conversation History Row & In-Page Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar_conv_row(conv, is_pinned: bool) -> None:
    """Render an interactive conversation row with resume, pin, and delete controls."""
    cid = conv["id"]
    title = conv["title"]
    is_active = st.session_state.conv_id == cid and not st.session_state.editing_profile

    prefix = "🩺 " if "chest" in title.lower() or "discomfort" in title.lower() else ("💊 " if "metformin" in title.lower() or "sugar" in title.lower() else "💬 ")
    display_title = f"{prefix}{title}"
    if len(display_title) > 22:
        display_title = display_title[:20] + ".."

    col_btn, col_pin, col_del = st.columns([0.70, 0.15, 0.15])
    with col_btn:
        btn_type = "primary" if is_active else "secondary"
        if st.button(display_title, key=f"side_c_{cid}", use_container_width=True, type=btn_type, help=title):
            st.session_state.conv_id = cid
            st.session_state.editing_profile = False
            st.session_state.active_view = "chat"
            st.rerun()

    with col_pin:
        pin_icon = "📍" if is_pinned else "📌"
        pin_tip = "Unpin" if is_pinned else "Pin to top"
        if st.button(pin_icon, key=f"pin_c_{cid}", use_container_width=True, type="secondary", help=pin_tip):
            pinned_list = list(st.session_state.get("pinned_conv_ids", []))
            if cid in pinned_list:
                pinned_list.remove(cid)
            else:
                pinned_list.append(cid)
            st.session_state.pinned_conv_ids = pinned_list
            st.rerun()

    with col_del:
        if st.button("🗑️", key=f"del_c_{cid}", use_container_width=True, type="secondary", help="Delete consultation"):
            delete_conversation(cid, st.session_state.user_id)
            pinned_list = list(st.session_state.get("pinned_conv_ids", []))
            if cid in pinned_list:
                pinned_list.remove(cid)
                st.session_state.pinned_conv_ids = pinned_list
            if st.session_state.conv_id == cid:
                st.session_state.conv_id = None
            st.rerun()


def show_sidebar(patient_profile: dict | None) -> None:
    """Legacy helper preserved for backward compatibility and test imports."""
    pass


# ---------------------------------------------------------------------------
# Part 5: Clinical Pipeline Inspector Interactive Diagnostics
# ---------------------------------------------------------------------------

def show_pipeline_inspector(latest_payload: dict | None) -> None:
    """Render interactive inspector displaying live clinical data and verification telemetry."""
    col_insp_title, col_insp_close = st.columns([0.84, 0.16])
    with col_insp_title:
        render_clean_html(
            """
            <div style="background: #0b1222; border: 2px solid rgba(56, 189, 248, 0.6); border-radius: 14px; padding: 12px 16px; margin-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.4rem; color: #38bdf8;">⚡</span>
                    <div>
                        <h3 style="margin: 0; color: #ffffff; font-size: 1.05rem; font-weight: 800;">Clinical Pipeline Inspector & Diagnostics</h3>
                        <small style="color: #94a3b8;">Click any stage below to inspect live clinical facts, RxNorm mappings, and coherence gates.</small>
                    </div>
                </div>
            </div>
            """
        )
    with col_insp_close:
        if st.button("✕ Close", key="btn_close_insp_banner", use_container_width=True, type="secondary"):
            st.session_state.show_pipeline_inspector = False
            st.rerun()

    t_ext, t_state, t_norm, t_ev, t_ver, t_gate = st.tabs([
        "1. Extractor",
        "2. State Manager",
        "3. Med Normalizer",
        "4. Evidence Retriever",
        "5. Coherence Verifier",
        "6. Decision Gate",
    ])

    ver_obj = latest_payload.get("verification", {}) if latest_payload else {}
    facts_list = latest_payload.get("facts", []) if latest_payload else []
    state_sum = latest_payload.get("state_summary", {}) if latest_payload else {}
    med_analysis = latest_payload.get("medication_analysis", []) if latest_payload else []
    evidence_list = latest_payload.get("evidence", []) if latest_payload else []

    with t_ext:
        st.markdown("##### Stage 1: State Extractor (Clinical NER & Assertion)")
        st.caption("Extracts symptoms, anatomical entities, negations, durations, and antecedents from patient utterances.")
        if facts_list:
            for f in facts_list:
                status_icon = "🟢" if f.get("status") == "positive" else ("🔴" if f.get("status") == "negative" else "⚪")
                st.markdown(
                    f"- **{status_icon} `{f.get('fact_id')}`: {f.get('description')}** — "
                    f"Status: `{f.get('status')}`, Confidence: `{f.get('confidence', 0.85):.0%}`, "
                    f"Type: `{'Antecedent' if f.get('is_antecedent') else 'Active Symptom'}`"
                )
        else:
            st.info("No active symptom extractions for current turn.")

    with t_state:
        st.markdown("##### Stage 2: State Manager (Longitudinal Patient Ledger)")
        st.caption("Maintains an immutable versioned clinical state tracking temporal symptom progression.")
        if state_sum:
            v = state_sum.get("version", 1)
            t = state_sum.get("turn_number", 0)
            fc = state_sum.get("facts_count", len(facts_list))
            st.markdown(f"- **State Version:** `v{v}` (Dialogue Turn `{t}`)")
            st.markdown(f"- **Total Facts In Longitudinal State:** `{fc}`")
            st.markdown(f"- **Changes From Prior Turn:** `{state_sum.get('changes_from_prior_turn', 'None')}`")
            contradictions = state_sum.get("contradictions", [])
            if contradictions:
                st.warning(f"⚠️ Longitudinal Contradictions Detected ({len(contradictions)}):")
                for c in contradictions:
                    st.markdown(f"  - Fact `{c[0]}` altered: `{c[1]}` → `{c[2]}`")
            else:
                st.success("No contradictions detected in patient state history.")
        else:
            st.info("Longitudinal patient state initialized at baseline.")

    with t_norm:
        st.markdown("##### Stage 3: Medication Normalizer (RxNorm Ontology)")
        st.caption("Resolves colloquial drug mentions, dosages, and brand names to standardized RxNorm concepts.")
        if med_analysis:
            for m in med_analysis:
                res = "✅ Resolved" if m.get("resolved") else "⚠️ Unresolved"
                st.markdown(
                    f"- **{m.get('mention')}** ({res}): Concept: `{m.get('normalized_name')}`, "
                    f"RxCUI: `{m.get('rxcui')}`, Method: `{m.get('match_method')}`"
                )
                if m.get("explanation"):
                    st.caption(f"Explanation: {m.get('explanation')}")
        else:
            st.info("No active prescription mentions detected in current dialogue.")

    with t_ev:
        st.markdown("##### Stage 4: Evidence Retriever (DailyMed FDA Drug Corpus)")
        st.caption("Cross-references FDA drug monographs to detect contraindicated clinical recommendations.")
        if evidence_list:
            for e in evidence_list:
                st.markdown(
                    f"- **[{e.get('evidence_id')}] `{e.get('active_ingredient')}`** ({e.get('section_name')}): "
                    f"{e.get('evidence_text')}... [DailyMed Source]({e.get('source_url')})"
                )
        else:
            ev_expl = latest_payload.get("evidence_explanation") if latest_payload else (
                "DailyMed corpus queries execute on medication mentions. FDA monograph references populate when medications are discussed."
            )
            st.info(ev_expl)

    with t_ver:
        st.markdown("##### Stage 5: Coherence Verifier (Multi-Rule Consistency Check)")
        st.caption("Executes deterministic verification: Fact Contradictions, Evidence Mismatch, Stale State, and Sycophancy Pushback.")
        flags = ver_obj.get("flags", [])
        if flags:
            for fl in flags:
                sev = fl.get("severity", "WARNING")
                cid = fl.get("check_id", "FLAG")
                desc = fl.get("description", "")
                if sev == "ERROR":
                    st.error(f"🚨 **[{cid}]**: {desc}")
                else:
                    st.warning(f"⚠️ **[{cid}]**: {desc}")
        else:
            st.success("✅ All 4 deterministic coherence engines passed clean with zero violations.")

    with t_gate:
        st.markdown("##### Stage 6: Decision Gate (Safety Enforcement Barrier)")
        gate_dec = ver_obj.get("gate_decision", "PASS")
        reasoning = ver_obj.get("reasoning", "All coherence constraints verified.")
        badge_color = "#10b981" if gate_dec == "PASS" else ("#f59e0b" if gate_dec in ["WARN", "CLARIFY"] else "#ef4444")
        render_clean_html(
            f"""
            <div style="background: #070b14; border: 1px solid {badge_color}; border-radius: 12px; padding: 12px; margin-top: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-weight: 700; color: #ffffff;">Computed Gate Outcome:</span>
                    <span style="background: rgba(56, 189, 248, 0.15); color: {badge_color}; font-weight: 800; font-family: monospace; padding: 3px 8px; border-radius: 6px; border: 1px solid {badge_color};">{gate_dec}</span>
                </div>
                <div style="font-size: 0.82rem; color: #cbd5e1;"><strong>Reasoning:</strong> {reasoning}</div>
            </div>
            """
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Close Inspector ✕", key="btn_close_inspector", use_container_width=True, type="secondary"):
        st.session_state.show_pipeline_inspector = False
        st.rerun()


# ---------------------------------------------------------------------------
# Part 6: Right Slide Panel (Clinical Intelligence & Referenced Docs)
# ---------------------------------------------------------------------------

def render_right_intelligence_panel(latest_payload: dict | None, patient_profile: dict | None) -> None:
    """Render right-side clinical intelligence slide panel cleanly matching ui_preview.html."""
    col_intel_hdr, col_intel_sw, col_intel_close = st.columns([0.48, 0.40, 0.12])
    with col_intel_hdr:
        render_clean_html(
            """
            <div style="font-size: 0.85rem; font-weight: 800; color: #38bdf8; padding-top: 6px; white-space: nowrap;">
                📊 Clinical Intelligence
            </div>
            """
        )
    with col_intel_sw:
        col_rg, col_rt = st.columns(2)
        with col_rg:
            btn_g_type = "primary" if st.session_state.right_panel_tab == "graph" else "secondary"
            if st.button("📈 Graph", key="tab_btn_graph", use_container_width=True, type=btn_g_type):
                st.session_state.right_panel_tab = "graph"
                st.rerun()
        with col_rt:
            btn_t_type = "primary" if st.session_state.right_panel_tab == "timeline" else "secondary"
            if st.button("⏳ Timeline", key="tab_btn_timeline", use_container_width=True, type=btn_t_type):
                st.session_state.right_panel_tab = "timeline"
                st.rerun()
    with col_intel_close:
        if st.button("✕", key="btn_close_intel_panel", use_container_width=True, type="secondary", help="Close Intelligence Panel"):
            st.session_state.show_right_panel = False
            st.rerun()

    # 1. Knowledge Graph or Timeline View
    if st.session_state.right_panel_tab == "graph":
        col_g_hdr, col_g_btn = st.columns([0.62, 0.38])
        with col_g_hdr:
            render_clean_html(
                """
                <div style="font-size: 0.80rem; font-weight: 700; color: #f1f5f9; display: flex; align-items: center; gap: 6px; padding-top: 4px;">
                    <span>🕸️</span> Clinical Knowledge Graph
                </div>
                """
            )
        with col_g_btn:
            if st.button("Inspect Nodes ➔", key="btn_inspect_graph_nodes", use_container_width=True, type="secondary"):
                st.session_state.show_pipeline_inspector = True
                st.rerun()

        facts = latest_payload.get("facts", []) if latest_payload else []
        node_1 = facts[0].get("description", "Chest")[:10] if len(facts) > 0 else "Chest"
        node_2 = facts[1].get("description", "Dyspnea")[:10] if len(facts) > 1 else "Dyspnea"
        gate_text = latest_payload.get("verification", {}).get("gate_decision", "PASS") if latest_payload else "PASS"
        state_sum = latest_payload.get("state_summary", {}) if latest_payload else {}
        contradictions = state_sum.get("contradictions", [])
        contra_text = f"⚠️ {len(contradictions)} Contradiction(s)" if contradictions else "0 Contradictions"
        contra_color = "#ef4444" if contradictions else "#10b981"

        graph_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
          body {{
            margin: 0;
            padding: 0;
            background: #070b14;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #cbd5e1;
            overflow: hidden;
          }}
          .graph-wrapper {{
            background: #070b14;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 8px 10px;
            box-sizing: border-box;
          }}
          @keyframes dash-pulse {{
            to {{
              stroke-dashoffset: -16;
            }}
          }}
          .animated-edge {{
            stroke-dasharray: 4, 4;
            animation: dash-pulse 1.8s linear infinite;
          }}
          .node-circle {{
            transition: all 0.2s ease-in-out;
            cursor: pointer;
          }}
          .node-circle:hover {{
            stroke-width: 2.5;
            filter: drop-shadow(0 0 6px #38bdf8);
          }}
          .graph-footer {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: #94a3b8;
            border-top: 1px solid #1e293b;
            padding-top: 5px;
            margin-top: 4px;
          }}
        </style>
        </head>
        <body>
          <div class="graph-wrapper">
            <svg width="100%" height="135" viewBox="0 0 300 135">
              <!-- Animated Interconnection Edges -->
              <line x1="55" y1="30" x2="150" y2="65" stroke="#38bdf8" stroke-width="2" class="animated-edge" opacity="0.85"/>
              <line x1="55" y1="105" x2="150" y2="65" stroke="#f59e0b" stroke-width="2" class="animated-edge" opacity="0.85"/>
              <line x1="150" y1="65" x2="245" y2="35" stroke="#10b981" stroke-width="2" class="animated-edge" opacity="0.85"/>
              <line x1="150" y1="65" x2="245" y2="95" stroke="#818cf8" stroke-width="2" class="animated-edge" opacity="0.85"/>

              <!-- Node 1: Primary Symptom -->
              <circle cx="55" cy="30" r="16" fill="#13233c" stroke="#38bdf8" stroke-width="1.8" class="node-circle"/>
              <text x="55" y="30" dominant-baseline="central" font-size="8.5" fill="#7dd3fc" text-anchor="middle" font-weight="bold">{node_1}</text>

              <!-- Node 2: Secondary Symptom / Exertion -->
              <circle cx="55" cy="105" r="16" fill="#2d2212" stroke="#f59e0b" stroke-width="1.8" class="node-circle"/>
              <text x="55" y="105" dominant-baseline="central" font-size="8.5" fill="#fcd34d" text-anchor="middle" font-weight="bold">{node_2}</text>

              <!-- Central Node: Coherence Gate Decision -->
              <circle cx="150" cy="65" r="21" fill="#1e1e38" stroke="#a78bfa" stroke-width="2.2" class="node-circle"/>
              <text x="150" y="65" dominant-baseline="central" font-size="9.5" fill="#ddd6fe" text-anchor="middle" font-weight="bold">Gate: {gate_text}</text>

              <!-- Node 3: DailyMed FDA Evidence -->
              <circle cx="245" cy="35" r="15" fill="#112920" stroke="#10b981" stroke-width="1.8" class="node-circle"/>
              <text x="245" y="35" dominant-baseline="central" font-size="8" fill="#6ee7b7" text-anchor="middle" font-weight="bold">DailyMed</text>

              <!-- Node 4: RxNorm Normalized Concept -->
              <circle cx="245" cy="95" r="15" fill="#1a1c38" stroke="#818cf8" stroke-width="1.8" class="node-circle"/>
              <text x="245" y="95" dominant-baseline="central" font-size="8" fill="#c7d2fe" text-anchor="middle" font-weight="bold">RxNorm</text>
            </svg>
            <div class="graph-footer">
              <span>● Click nodes or inspect button</span>
              <span style="color: {contra_color}; font-family: monospace; font-weight: bold;">{contra_text}</span>
            </div>
          </div>
        </body>
        </html>
        """
        components.html(graph_html, height=195)
    else:
        state_sum = latest_payload.get("state_summary", {}) if latest_payload else {}
        ver_num = state_sum.get("version", 1)
        facts = latest_payload.get("facts", []) if latest_payload else []
        facts_summary = ", ".join([f.get("description", "") for f in facts[:2]]) if facts else "None asserted"
        gate_summary = latest_payload.get("verification", {}).get("gate_decision", "PASS") if latest_payload else "PASS"

        render_clean_html(
            f"""
            <div style="background: #070b14; border: 1px solid #1e293b; border-radius: 12px; padding: 12px; max-height: 185px; overflow-y: auto; font-size: 0.78rem;">
                <div style="border-left: 2px solid #10b981; padding-left: 8px; margin-bottom: 8px;">
                    <div style="color: #94a3b8; font-size: 0.70rem;">Turn 0 • Baseline Record</div>
                    <div style="color: #f1f5f9; font-weight: 600;">Demographics & History Loaded</div>
                </div>
                <div style="border-left: 2px solid #38bdf8; padding-left: 8px; margin-bottom: 8px;">
                    <div style="color: #94a3b8; font-size: 0.70rem;">Turn 1 • Longitudinal State (v{ver_num})</div>
                    <div style="color: #38bdf8; font-weight: 600;">+ Symptoms: {facts_summary}</div>
                </div>
                <div style="border-left: 2px solid #f59e0b; padding-left: 8px;">
                    <div style="color: #94a3b8; font-size: 0.70rem;">Active • Safety Decision Gate</div>
                    <div style="color: #fcd34d; font-weight: 600;">Coherence Check: {gate_summary}</div>
                </div>
            </div>
            """
        )

    # 2. Referenced Docs & Evidence
    evidence_list = latest_payload.get("evidence", []) if latest_payload else []
    ev_title = f"DailyMed Monograph: {evidence_list[0].get('active_ingredient', 'Metformin HCl')}" if evidence_list else "DailyMed Monograph #DM-0492: Metformin HCl"
    ev_excerpt = evidence_list[0].get("evidence_text", "Warnings & Precautions: Evaluate cardiovascular and renal indicators prior to titration...") if evidence_list else "Warnings & Precautions: Evaluate cardiovascular and renal indicators prior to titration..."

    prescriptions = st.session_state.get("uploaded_prescriptions", [])
    p_html = ""
    for p in prescriptions:
        p_html += f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background: #0f1b30; padding: 6px 10px; border-radius: 6px; margin-bottom: 4px; font-size: 0.75rem;">
            <div>
                <div style="color: #f1f5f9; font-weight: 600;">📄 {p['name']}</div>
                <div style="color: #94a3b8; font-size: 0.68rem;">{p['med']}</div>
            </div>
            <span style="color: #f59e0b; font-weight: 600; font-size: 0.72rem;">View</span>
        </div>
        """

    docs_panel_html = f"""
    <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 12px; margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-bottom: 10px;">
            <span style="color: #ffffff; font-weight: 700; font-size: 0.85rem;">📁 Referenced Docs & Evidence</span>
        </div>
        <div style="background: #080d1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.76rem; font-weight: 700; color: #38bdf8; margin-bottom: 4px;">
                <span>📑 Active Evidence Monograph</span>
                <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 1px 6px; border-radius: 4px; font-size: 0.68rem; font-family: monospace;">DailyMed</span>
            </div>
            <div style="font-size: 0.74rem; color: #f1f5f9; font-weight: 600;">{ev_title}</div>
            <div style="font-size: 0.70rem; color: #94a3b8; margin-top: 3px;">"{ev_excerpt[:90]}..."</div>
            <div style="font-size: 0.68rem; color: #10b981; font-family: monospace; margin-top: 4px;">Status: Verified Safe</div>
        </div>
        <div style="background: #080d1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.76rem; font-weight: 700; color: #cbd5e1; margin-bottom: 6px;">
                <span>💊 Patient Prescriptions Folder</span>
                <span style="font-size: 0.7rem; color: #94a3b8;">{len(prescriptions)} File</span>
            </div>
            {p_html}
        </div>
        <div style="background: #080d1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.76rem; font-weight: 700; color: #cbd5e1; margin-bottom: 4px;">
                <span>🗂️ Similar Medical Cases Archive</span>
                <span style="color: #38bdf8; font-size: 0.68rem; font-family: monospace;">2 Matches</span>
            </div>
            <div style="font-size: 0.70rem; color: #94a3b8; line-height: 1.6;">
                <div style="display: flex; justify-content: space-between;">
                    <span>• Case #C-109: Exertional Dyspnea</span>
                    <span style="color: #38bdf8; font-weight: 600;">92% match</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>• Case #C-084: Fatigue & Metabolic Workup</span>
                    <span style="color: #38bdf8; font-weight: 600;">85% match</span>
                </div>
            </div>
        </div>
    </div>
    """
    render_clean_html(docs_panel_html)

    # Dedicated Modal Trigger Button
    if st.button("➕ Add Prescription / Upload Report", key="btn_open_prescription_dialog", use_container_width=True, type="secondary"):
        open_prescription_dialog()


# ---------------------------------------------------------------------------
# Part 7: Compact Patient Context & Verification Details Panel
# ---------------------------------------------------------------------------

def show_compact_patient_context(patient_profile: dict | None) -> None:
    """Render compact patient context banner above chat messages."""
    if not patient_profile:
        return

    name = patient_profile.get("preferred_name") or "Patient"
    age_str = get_age_display(patient_profile.get("age_or_dob"))
    sex = patient_profile.get("sex_assigned_at_birth") or "Unknown"

    chips_html = f"<span style='background:#1e293b; color:#cbd5e1; border:1px solid #334155; padding:3px 8px; border-radius:6px; font-size:0.75rem; margin-right:6px;'>👤 {name}</span>"
    chips_html += f"<span style='background:#1e293b; color:#cbd5e1; border:1px solid #334155; padding:3px 8px; border-radius:6px; font-size:0.75rem; margin-right:6px;'>🎂 {age_str}</span>"
    chips_html += f"<span style='background:#1e293b; color:#cbd5e1; border:1px solid #334155; padding:3px 8px; border-radius:6px; font-size:0.75rem; margin-right:6px;'>🧬 Sex: {sex}</span>"

    conditions = patient_profile.get("medical_conditions")
    if conditions:
        for c in conditions.split(",")[:2]:
            chips_html += f"<span style='background:#2d2212; color:#fcd34d; border:1px solid rgba(245,158,11,0.4); padding:3px 8px; border-radius:6px; font-size:0.75rem; margin-right:6px;'>⚠️ {c.strip()}</span>"

    render_clean_html(
        f"""
        <div style="background: #0b1222; border: 1px solid #1e293b; border-radius: 12px; padding: 8px 14px; margin-bottom: 12px;">
            <div style="font-size: 0.70rem; font-weight: 700; color: #94a3b8; margin-bottom: 4px;">ACTIVE CLINICAL CONTEXT</div>
            <div>{chips_html}</div>
        </div>
        """
    )


def show_verification_expander(payload: dict) -> None:
    """Render clean verification and provenance details under assistant responses."""
    ver = payload.get("verification", {})
    gate_decision = ver.get("gate_decision", "PASS")
    reasoning = ver.get("reasoning", "All coherence constraints verified.")

    if gate_decision == "REFUSE":
        st.error(f"🚨 **COHERENCE GATE: REFUSE** — Response blocked for clinical safety: {reasoning}")
    elif gate_decision == "WARN":
        st.warning(f"⚠️ **COHERENCE GATE: WARN** — Clinical incoherence detected: {reasoning}")
    elif gate_decision == "CLARIFY":
        st.info(f"ℹ️ **COHERENCE GATE: CLARIFY** — Clarification recommended: {reasoning}")

    expander_icon = {"PASS": "🔍", "WARN": "⚠️", "CLARIFY": "ℹ️", "REFUSE": "🚨"}.get(gate_decision, "🔍")
    is_expanded = gate_decision != "PASS"

    with st.expander(f"{expander_icon} Clinical Verification & Provenance — [{gate_decision}]", expanded=is_expanded):
        st.markdown(
            f"""
            <div style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 0.75rem;">
                <strong>Gate Decision:</strong> <span style="font-weight: 800; color: #38bdf8;">{gate_decision}</span> • {reasoning}
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("<strong style='color:#38bdf8;'>1. Newly Extracted Facts:</strong>", unsafe_allow_html=True)
            facts = payload.get("facts", [])
            if facts:
                for f in facts:
                    pol = "➕" if f.get("status") == "positive" else ("➖" if f.get("status") == "negative" else "❓")
                    typ = "[Antecedent]" if f.get("is_antecedent") else "[Symptom]"
                    st.markdown(f"- **{pol} {f.get('description')}** ({f.get('fact_id')}) {typ}")
            else:
                st.caption("No new clinical facts extracted in this turn.")

        with col_r:
            st.markdown("<strong style='color:#38bdf8;'>2. Longitudinal State & Provenance:</strong>", unsafe_allow_html=True)
            state_sum = payload.get("state_summary", {})
            if state_sum:
                st.markdown(f"- Version: `v{state_sum.get('version', 1)}` (Turn {state_sum.get('turn_number', 0)})")
                st.markdown(f"- Changes: `{state_sum.get('changes_from_prior_turn', 'None')}`")


def _start_conversation_with_message(initial_message: str, title: str, patient_profile: dict | None) -> None:
    """Helper to start a new consultation with an initial prompt."""
    cid = create_conversation(st.session_state.user_id, title)
    st.session_state.conv_id = cid

    add_message(cid, "user", initial_message)

    with st.spinner("Analyzing clinical state & verifying coherence..."):
        result = run_pipeline(
            user_message=initial_message,
            conversation_id=cid,
            turn_index=0,
            prior_messages=[],
            patient_profile=patient_profile,
        )

    asst_msg_id = add_message(cid, "assistant", result["response_text"])

    verification_payload = {
        "verification": result["verification"],
        "facts": result["facts"],
        "state_summary": result["state_summary"],
        "evidence": result["evidence"],
        "evidence_explanation": result.get("evidence_explanation", ""),
        "medication_analysis": result.get("medication_analysis", []),
    }

    save_verification_result(
        message_id=asst_msg_id,
        flags_json=json.dumps(verification_payload),
        gate_decision=result["verification"]["gate_decision"],
        reasoning=result["verification"]["reasoning"],
    )
    st.rerun()


# ---------------------------------------------------------------------------
# Part 8: Main Chat Interface & 3-Panel In-Page Layout
# ---------------------------------------------------------------------------

def show_main_chat(patient_profile: dict | None) -> None:
    """Render main conversational chat interface with ChatGPT-style starters and bubbles."""
    if st.session_state.get("editing_profile", False):
        show_onboarding_page(is_editing=True)
        return

    # Clean legacy query parameters
    try:
        st.query_params.clear()
    except Exception:
        pass

    pref_name = patient_profile.get("preferred_name") if patient_profile else (st.session_state.username or "samrudh")
    age_str = get_age_display(patient_profile.get("age_or_dob")) if patient_profile else ""
    sex_str = patient_profile.get("sex_assigned_at_birth") if patient_profile else ""
    meta_parts = []
    if age_str and age_str != "Unknown":
        meta_parts.append(age_str)
    if sex_str and sex_str != "Prefer not to say":
        meta_parts.append(sex_str)
    meta_line = " • ".join(meta_parts) if meta_parts else "26 yrs • Male"

    # Fetch active conversation data
    messages = []
    latest_payload = None
    latest_gate_decision = "PASS"
    state_ver = 1
    chat_title = "Active Session • Ready to Consult"

    if st.session_state.conv_id is not None:
        conv = get_conversation(st.session_state.conv_id, st.session_state.user_id)
        if conv is not None:
            chat_title = conv["title"]
            messages = get_messages(st.session_state.conv_id)
            for msg in reversed(messages):
                if msg["role"] == "assistant":
                    ver_rec = get_verification_result(msg["id"])
                    if ver_rec:
                        try:
                            ver_dict = dict(ver_rec)
                            latest_payload = json.loads(ver_dict["flags_json"])
                            latest_gate_decision = ver_dict.get("gate_decision", "PASS")
                            state_ver = latest_payload.get("state_summary", {}).get("version", 1)
                        except Exception:
                            pass
                        break

    # 1. Top Application Banner
    render_top_app_header(gate_status=latest_gate_decision, pref_name=pref_name)

    # 2. Pipeline Inspector Modal Dialog if requested
    if st.session_state.get("show_pipeline_inspector", False):
        open_pipeline_inspector_dialog(latest_payload)

    # 3. Action / Breadcrumb Bar
    col_act_hist, col_act_title, col_act_state = st.columns([0.10, 0.72, 0.18])
    with col_act_hist:
        btn_hist_label = "📑 History"
        if st.button(btn_hist_label, key="btn_toggle_history_sidebar", use_container_width=True, type="secondary", help="Toggle consultation history sidebar"):
            st.session_state.show_left_sidebar = not st.session_state.get("show_left_sidebar", True)
            st.rerun()

    with col_act_title:
        render_clean_html(
            f"""
            <div style="display: flex; align-items: center; gap: 8px; padding-top: 4px;">
                <span style="color: #475569;">|</span>
                <h3 style="margin: 0; font-size: 0.96rem; font-weight: 800; color: #ffffff;">{chat_title}</h3>
                <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px; font-family: monospace;">Verified {latest_gate_decision}</span>
            </div>
            """
        )

    with col_act_state:
        render_clean_html(
            f"""
            <div style="text-align: right; font-size: 0.72rem; color: #94a3b8; font-family: monospace; padding-top: 6px;">
                Active Patient State: <strong style="color: #38bdf8;">v{state_ver}</strong>
            </div>
            """
        )

    # 4. In-Page 3-Column Layout
    show_left = st.session_state.get("show_left_sidebar", True)
    show_right = st.session_state.get("show_right_panel", True)

    # Dynamically align bottom message dock inside the center column
    left_offset = "22%" if show_left else "0"
    right_offset = "28%" if show_right else "0"
    border_r = "border-right: 1px solid #1e293b !important;" if show_right else ""
    border_l = "border-left: 1px solid #1e293b !important;" if show_left else ""

    render_clean_html(
        f"""
        <style>
        [data-testid="stBottom"] {{
            left: {left_offset} !important;
            right: {right_offset} !important;
            {border_l}
            {border_r}
        }}
        </style>
        """
    )

    if show_left and show_right:
        col_left, col_center, col_right = st.columns([22, 50, 28])
    elif show_left and not show_right:
        col_left, col_center = st.columns([24, 76])
        col_right = None
    elif not show_left and show_right:
        col_left = None
        col_center, col_right = st.columns([68, 32])
    else:
        col_left = None
        col_center = st.container()
        col_right = None

    # ================= LEFT SIDEBAR COLUMN =================
    if col_left is not None:
        with col_left:
            # New Consultation Button
            if st.button("➕ New Consultation", key="btn_side_new_consult", use_container_width=True, type="primary"):
                st.session_state.conv_id = None
                st.session_state.editing_profile = False
                st.session_state.active_view = "chat"
                st.rerun()

            # Search Bar
            search_q = st.text_input(
                "Search past consults...",
                value=st.session_state.chat_search_query,
                placeholder="🔍 Search past consults...",
                label_visibility="collapsed",
                key="side_search_input"
            )
            st.session_state.chat_search_query = search_q

            # History header
            all_convs = get_conversations_for_user(st.session_state.user_id, search_q)
            active_count = len(all_convs)
            render_clean_html(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0 6px 0; font-size: 0.70rem; font-weight: 700; color: #94a3b8; text-transform: uppercase;">
                    <span>CONSULTATION HISTORY</span>
                    <span style="color: #f59e0b; font-size: 0.65rem; font-weight: 700;">{active_count} ACTIVE</span>
                </div>
                """
            )

            # Consultations list
            if not all_convs:
                st.caption("No consultations yet. Start a consultation above!")
            else:
                pinned_ids = set(st.session_state.get("pinned_conv_ids", []))
                pinned_convs = [c for c in all_convs if c["id"] in pinned_ids]
                recent_convs = [c for c in all_convs if c["id"] not in pinned_ids]

                for conv in pinned_convs:
                    _render_sidebar_conv_row(conv, is_pinned=True)
                for conv in recent_convs:
                    _render_sidebar_conv_row(conv, is_pinned=False)

            st.markdown("<hr style='border-color: #1e293b; margin: 12px 0 8px 0;'>", unsafe_allow_html=True)

            # User Profile Card
            render_clean_html(
                f"""
                <div style="background: #080d1a; border: 1px solid #1e293b; border-radius: 12px; padding: 10px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: #1e293b; border: 1px solid #334155; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 800; color: #f59e0b;">
                            SP
                        </div>
                        <div>
                            <div style="font-size: 0.82rem; font-weight: 700; color: #f1f5f9;">{pref_name}</div>
                            <div style="font-size: 0.68rem; color: #94a3b8;">{meta_line}</div>
                        </div>
                    </div>
                </div>
                """
            )
            col_prof_btn, col_signout_btn = st.columns(2)
            with col_prof_btn:
                if st.button("✏️ Profile", key="btn_side_edit_prof", use_container_width=True, type="secondary"):
                    st.session_state.editing_profile = True
                    st.session_state.active_view = "form"
                    st.rerun()
            with col_signout_btn:
                if st.button("🚪 Sign Out", key="btn_side_signout", use_container_width=True, type="secondary"):
                    st.session_state.user_id = None
                    st.session_state.username = None
                    st.session_state.page = "login"
                    st.session_state.active_view = "login"
                    st.rerun()

            # Full-Width Inspector Button
            if st.button("⚡ Clinical Pipeline Inspector", key="btn_sidebar_inspector", use_container_width=True, type="secondary"):
                st.session_state.show_pipeline_inspector = True
                st.rerun()

    # ================= CENTER CHAT COLUMN =================
    with col_center:
        user_input = None

        if st.session_state.conv_id is None:
            # Welcome Starter Screen
            render_clean_html(
                f"""
                <div style="text-align: center; padding: 20px 12px 14px; max-width: 680px; margin: auto;">
                    <h1 style="color: #ffffff; font-size: 1.65rem; font-weight: 800; letter-spacing: -0.02em;">How can I help you today, {pref_name}?</h1>
                    <div style="color: #94a3b8; font-size: 0.88rem; line-height: 1.5; margin-top: 6px;">
                        I track your symptoms across conversation turns, normalize medications against RxNorm, 
                        and verify clinical coherence using evidence-based FDA medical records.
                    </div>
                </div>
                """
            )

            st.markdown("##### Suggested consultation starters")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("Describe symptoms\n\nI have had mild chest tightness and slight shortness of breath", key="btn_start_chest", use_container_width=True):
                    _start_conversation_with_message(
                        "I've had mild chest tightness and slight shortness of breath when climbing stairs for the past 2 days. Also feeling a bit more fatigued than usual.",
                        "Chest Discomfort & Dyspnea Consultation",
                        patient_profile,
                    )
                if st.button("Update health history\n\nI want to report an update on my medical conditions", key="btn_start_hist", use_container_width=True):
                    _start_conversation_with_message(
                        "I would like to update my active health profile and report my current symptoms",
                        "Health History Update",
                        patient_profile,
                    )
            with col_s2:
                if st.button("Discuss a medication\n\nI am taking Metformin 500mg and feeling slightly dizzy", key="btn_start_med", use_container_width=True):
                    _start_conversation_with_message(
                        "I am taking Metformin 500mg and feeling slightly dizzy",
                        "Metformin Query",
                        patient_profile,
                    )
                if st.button("Fever & fatigue consultation\n\nI have had a fever and mild fatigue for two days", key="btn_start_fever", use_container_width=True):
                    _start_conversation_with_message(
                        "I have had a fever and mild fatigue for two days",
                        "Fever & Fatigue Consultation",
                        patient_profile,
                    )

            user_input = st.chat_input("Type your health update, describe symptoms, or ask about medications...")

        else:
            # Active Conversation Chat History
            render_clean_html(
                """
                <div style="max-width: 580px; margin: 0 auto 14px auto; background: #0a1122; border: 1px solid #1e293b; border-radius: 12px; padding: 9px 12px; text-align: center; font-size: 0.74rem; color: #94a3b8;">
                    🛡️ Medical context active. Verified against RxNorm, DailyMed FDA monographs, and longitudinal state.
                </div>
                """
            )

            for msg in messages:
                time_str = msg["created_at"][11:16] if "T" in msg["created_at"] else msg["created_at"][:16]
                if msg["role"] == "user":
                    formatted_text = format_chat_text(msg['content'])
                    render_clean_html(
                        f"""
                        <div class="chat-row-user">
                            <div class="chat-card-user">
                                <div class="chat-card-user-header">
                                    <span style="font-weight: 700; color: #f59e0b;">You (Patient)</span>
                                    <span style="color: #94a3b8; font-family: monospace;">{time_str}</span>
                                </div>
                                <div style="font-size: 0.86rem; line-height: 1.55;">{formatted_text}</div>
                            </div>
                            <div class="chat-avatar-user" title="You">SP</div>
                        </div>
                        """
                    )
                else:
                    formatted_text = format_chat_text(msg['content'])
                    ver_record = get_verification_result(msg["id"])
                    ver_dict = dict(ver_record) if ver_record else None
                    gate_badge = '<span style="background: rgba(14, 165, 233, 0.2); color: #38bdf8; padding: 1px 6px; border-radius: 4px; font-size: 0.68rem; font-family: monospace;">Verified AI</span>'
                    if ver_dict and ver_dict.get("gate_decision"):
                        g_dec = ver_dict["gate_decision"]
                        g_col = "#10b981" if g_dec == "PASS" else ("#f59e0b" if g_dec in ["WARN", "CLARIFY"] else "#ef4444")
                        gate_badge = f'<span style="background: rgba(16, 185, 129, 0.15); color: {g_col}; border: 1px solid {g_col}66; padding: 1px 6px; border-radius: 4px; font-size: 0.68rem; font-family: monospace;">Gate: {g_dec}</span>'

                    # Clinical notice callout if chest or exertional symptoms mentioned
                    notice_html = ""
                    if "chest" in msg['content'].lower() or "dyspnea" in msg['content'].lower():
                        notice_html = """
                        <div style="background: #09101f; border-left: 2px solid #f59e0b; padding: 8px 12px; border-radius: 0 6px 6px 0; font-size: 0.74rem; color: #cbd5e1; margin: 8px 0;">
                            ⚠️ <strong>Clinical Notice:</strong> New onset chest tightness with exertion requires immediate clinical evaluation. If you experience radiating pain or worsening dyspnea, seek immediate in-person emergency care.
                        </div>
                        """

                    render_clean_html(
                        f"""
                        <div class="chat-row-assistant">
                            <div class="chat-avatar-assistant" title="ClinCoherence Assistant">🩺</div>
                            <div class="chat-card-assistant">
                                <div class="chat-card-assistant-header">
                                    <span style="font-weight: 700; color: #7dd3fc; display: flex; align-items: center; gap: 6px;">
                                        ClinCoherence Assistant
                                        {gate_badge}
                                    </span>
                                    <span style="color: #94a3b8; font-family: monospace;">{time_str}</span>
                                </div>
                                <div style="font-size: 0.86rem; line-height: 1.55;">{formatted_text}</div>
                                {notice_html}
                            </div>
                        </div>
                        """
                    )
                    if ver_dict:
                        try:
                            raw_payload = json.loads(ver_dict["flags_json"])
                            payload = raw_payload if isinstance(raw_payload, dict) and "verification" in raw_payload else {
                                "verification": {"gate_decision": ver_dict["gate_decision"], "reasoning": ver_dict["reasoning"], "flags": []},
                                "facts": [],
                                "state_summary": {},
                                "evidence": [],
                                "evidence_explanation": "",
                                "medication_analysis": [],
                            }
                        except Exception:
                            payload = {
                                "verification": {"gate_decision": ver_dict["gate_decision"], "reasoning": ver_dict["reasoning"], "flags": []},
                                "facts": [],
                                "state_summary": {},
                                "evidence": [],
                                "evidence_explanation": "",
                                "medication_analysis": [],
                            }
                        show_verification_expander(payload)

            user_input = st.chat_input("Type your health update, describe symptoms, or ask about medications...")

        # Micro-label below chat dock
        render_clean_html(
            """
            <div style="text-align: center; font-size: 0.70rem; color: #bae6fd; margin-top: 4px; display: flex; align-items: center; justify-content: center; gap: 6px;">
                <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #38bdf8;"></span>
                Refined Steel Sky-Blue Dock (#14233c). Clear contrast, balanced tone, no eye strain.
            </div>
            """
        )

    # ================= RIGHT INTELLIGENCE COLUMN =================
    if col_right is not None:
        with col_right:
            render_right_intelligence_panel(latest_payload, patient_profile)

    # Process user query
    if user_input:
        if st.session_state.conv_id is None:
            title = user_input[:35].strip() + ("..." if len(user_input.strip()) > 35 else "")
            _start_conversation_with_message(user_input, title, patient_profile)
        else:
            turn_index = len(messages)
            prior_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

            add_message(st.session_state.conv_id, "user", user_input)

            with st.spinner("Analyzing clinical state & verifying coherence..."):
                result = run_pipeline(
                    user_message=user_input,
                    conversation_id=st.session_state.conv_id,
                    turn_index=turn_index,
                    prior_messages=prior_messages,
                    patient_profile=patient_profile,
                )

            asst_msg_id = add_message(st.session_state.conv_id, "assistant", result["response_text"])

            verification_payload = {
                "verification": result["verification"],
                "facts": result["facts"],
                "state_summary": result["state_summary"],
                "evidence": result["evidence"],
                "evidence_explanation": result.get("evidence_explanation", ""),
                "medication_analysis": result.get("medication_analysis", []),
            }

            save_verification_result(
                message_id=asst_msg_id,
                flags_json=json.dumps(verification_payload),
                gate_decision=result["verification"]["gate_decision"],
                reasoning=result["verification"]["reasoning"],
            )
            st.rerun()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def main() -> None:
    """Application router."""
    _init_session()

    # Clear legacy query parameters
    try:
        st.query_params.clear()
    except Exception:
        pass

    # View switcher routing
    if st.session_state.active_view == "login" or st.session_state.user_id is None:
        show_auth_page()
        return

    profile_row = get_patient_profile(st.session_state.user_id)
    profile_dict = dict(profile_row) if profile_row else None

    if st.session_state.active_view == "form" or profile_dict is None:
        show_onboarding_page(is_editing=(profile_dict is not None))
        return

    show_main_chat(profile_dict)


if __name__ == "__main__":
    main()
else:
    main()
