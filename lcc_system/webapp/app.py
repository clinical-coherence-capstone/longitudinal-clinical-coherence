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

try:
    from .database import (
        init_db,
        create_conversation,
        get_conversations_for_user,
        delete_empty_conversations,
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
    initial_sidebar_state="expanded",
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
    """Return a human-readable age string from stored age_or_dob."""
    if not age_or_dob_str:
        return "Unknown"
    clean = age_or_dob_str.strip()
    # Try parsing as ISO date (YYYY-MM-DD)
    try:
        dt = datetime.strptime(clean[:10], "%Y-%m-%d").date()
        age = calculate_age_from_dob(dt)
        return f"{age} yrs ({dt.strftime('%b %d, %Y')})"
    except Exception:
        if clean.isdigit():
            return f"{clean} yrs"
        return clean


def parse_dob_date(age_or_dob_str: str | None) -> date:
    """Attempt to parse stored string into date; default to 1990-01-01."""
    if age_or_dob_str:
        try:
            return datetime.strptime(age_or_dob_str.strip()[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    return date(1990, 1, 1)


def format_chat_text(text: str) -> str:
    """Safely format chat text for HTML rendering while preserving line breaks and emphasis."""
    escaped = html.escape(text)
    # Bold **text**
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
    # Italic *(text)* or *text*
    escaped = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', escaped)
    # Line breaks
    escaped = escaped.replace('\n', '<br>')
    return escaped


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
        ("editing_profile", False),
        ("onboarding_step", 1),
        ("wizard_step1", {}),
        ("wizard_meds", []),
        ("chat_search_query", ""),
        ("chk_show_login_pw", False),
        ("chk_show_reg_pw", False),
    ]
    for key, val in defaults:
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Part 1: Login & Registration
# ---------------------------------------------------------------------------

def show_auth_page() -> None:
    """Render polished, minimal Login and Registration pages."""
    col_spacer_l, col_center, col_spacer_r = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            """
            <div class="auth-header">
                <div class="auth-logo-badge">🩺</div>
                <h1 class="auth-title">ClinCoherence</h1>
                <div class="auth-subtitle">Longitudinal Clinical Assistant</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            login_user_input = st.text_input(
                "Username or Email",
                key="login_user_field",
                placeholder="Enter your username",
            )

            show_login_pw = st.session_state.get("chk_show_login_pw", False)
            login_pw_input = st.text_input(
                "Password",
                type="default" if show_login_pw else "password",
                key="login_pw_field",
                placeholder="Enter your password",
            )
            st.checkbox("Show password", key="chk_show_login_pw")

            if st.button("Sign In ➔", key="btn_signin", use_container_width=True, type="primary"):
                if not login_user_input or not login_pw_input:
                    st.error("Please enter both username and password.")
                else:
                    ok, msg, uid = login_user(login_user_input, login_pw_input)
                    if ok:
                        st.session_state.user_id = uid
                        st.session_state.username = login_user_input.strip()
                        st.session_state.page = "main"
                        st.session_state.conv_id = None
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
                placeholder="e.g. janesmith",
            )

            show_reg_pw = st.session_state.get("chk_show_reg_pw", False)
            reg_pw_input = st.text_input(
                "Password (minimum 8 characters)",
                type="default" if show_reg_pw else "password",
                key="reg_pw_field",
                placeholder="Create a secure password",
            )
            reg_confirm_input = st.text_input(
                "Confirm Password",
                type="default" if show_reg_pw else "password",
                key="reg_confirm_field",
                placeholder="Re-enter your password",
            )
            st.checkbox("Show password", key="chk_show_reg_pw")

            if st.button("Create Account ➔", key="btn_register", use_container_width=True, type="primary"):
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

        st.markdown(
            """
            <div style="text-align: center; margin-top: 2rem; font-size: 0.75rem; color: #94a3b8;">
                🔒 Secure bcrypt password hashing • Isolated patient chat history • Research Prototype
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Part 2: Guided Patient Onboarding Wizard (2 Steps)
# ---------------------------------------------------------------------------

COMMON_CONDITIONS = [
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
    "No known allergies (NKDA)",
    "Penicillin / Amoxicillin",
    "Sulfa antibiotics",
    "Aspirin / NSAIDs (Ibuprofen)",
    "ACE inhibitors",
    "Latex",
    "Peanuts / Tree nuts",
    "Shellfish",
    "Other",
]

MED_FREQUENCIES = [
    "Once daily",
    "Once daily in the morning",
    "Once daily at bedtime",
    "Twice daily",
    "Three times daily",
    "Four times daily",
    "Every other day",
    "Weekly",
    "As needed (PRN)",
]


def show_onboarding_page(is_editing: bool = False) -> None:
    """Render guided, attractive 2-step patient profile wizard."""
    user_id = st.session_state.user_id
    existing_prof = get_patient_profile(user_id) if user_id else None

    # Load initial wizard state if not populated or if editing
    if not st.session_state.wizard_step1:
        if existing_prof:
            st.session_state.wizard_step1 = {
                "preferred_name": existing_prof["preferred_name"] or "",
                "dob": parse_dob_date(existing_prof["age_or_dob"]),
                "sex_assigned_at_birth": existing_prof["sex_assigned_at_birth"] or "Prefer not to say",
                "gender_identity": existing_prof["gender_identity"] or "Prefer not to say",
            }
        else:
            st.session_state.wizard_step1 = {
                "preferred_name": st.session_state.username or "",
                "dob": date(1990, 1, 1),
                "sex_assigned_at_birth": "Prefer not to say",
                "gender_identity": "Prefer not to say",
            }

    step = st.session_state.onboarding_step

    # Wizard Header & Progress Bar
    header_title = "Edit Patient Profile" if is_editing else "Patient Profile Setup"
    st.markdown(f"### 📋 {header_title}")
    st.caption("Complete your baseline clinical information to contextualize longitudinal coherence tracking.")

    # Progress Indicator
    s1_class = "wizard-step-completed" if step > 1 else ("wizard-step-active" if step == 1 else "wizard-step-inactive")
    s2_class = "wizard-step-active" if step == 2 else "wizard-step-inactive"
    div_class = "wizard-divider completed" if step > 1 else "wizard-divider"

    st.markdown(
        f"""
        <div class="wizard-progress-bar">
            <div class="wizard-step {s1_class}">
                <div class="wizard-step-circle">1</div>
                <span>Step 1: Basic Information</span>
            </div>
            <div class="{div_class}"></div>
            <div class="wizard-step {s2_class}">
                <div class="wizard-step-circle">2</div>
                <span>Step 2: Medical Information</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # STEP 1: Basic Information
    # -----------------------------------------------------------------------
    if step == 1:
        st.markdown("#### Step 1: Basic Information")
        st.caption("Tell us how you would like to be addressed and your core demographic information.")

        col_a, col_b = st.columns(2)

        with col_a:
            pref_name_val = st.text_input(
                "Preferred Name *",
                value=st.session_state.wizard_step1.get("preferred_name", ""),
                help="The name our clinical assistant will use to address you conversationally.",
            )

            # User-friendly Date of Birth selector with instant year navigation
            today = date.today()
            saved_dob = st.session_state.wizard_step1.get("dob") or date(1990, 1, 1)
            if saved_dob > today:
                saved_dob = today

            st.markdown(
                '<label style="font-size:0.875rem; font-weight:600; color:#334155;">Date of Birth *</label>',
                unsafe_allow_html=True,
            )
            col_y, col_m, col_d = st.columns([1.2, 1.4, 1.0])

            # Year: Current year down to 1900
            year_list = list(range(today.year, 1899, -1))
            default_year = saved_dob.year if saved_dob.year in year_list else 1990
            sel_year = col_y.selectbox(
                "Year",
                options=year_list,
                index=year_list.index(default_year),
                key="wizard_dob_year",
            )

            # Month: Capped at current month if current year selected
            month_names = [
                (1, "01 - Jan"), (2, "02 - Feb"), (3, "03 - Mar"), (4, "04 - Apr"),
                (5, "05 - May"), (6, "06 - Jun"), (7, "07 - Jul"), (8, "08 - Aug"),
                (9, "09 - Sep"), (10, "10 - Oct"), (11, "11 - Nov"), (12, "12 - Dec")
            ]
            if sel_year == today.year:
                available_months = month_names[:today.month]
            else:
                available_months = month_names

            month_nums = [m[0] for m in available_months]
            default_m_idx = month_nums.index(saved_dob.month) if saved_dob.month in month_nums else 0
            sel_month_tuple = col_m.selectbox(
                "Month",
                options=available_months,
                index=default_m_idx,
                format_func=lambda x: x[1],
                key="wizard_dob_month",
            )
            sel_month = sel_month_tuple[0]

            # Day: Accurate days in month capped at today if current year and month
            max_days_in_month = calendar.monthrange(sel_year, sel_month)[1]
            if sel_year == today.year and sel_month == today.month:
                max_days = today.day
            else:
                max_days = max_days_in_month

            day_list = list(range(1, max_days + 1))
            default_day = saved_dob.day if saved_dob.day in day_list else (max_days if saved_dob.day > max_days else 1)
            sel_day = col_d.selectbox(
                "Day",
                options=day_list,
                index=day_list.index(default_day),
                key="wizard_dob_day",
            )

            dob_val = date(sel_year, sel_month, sel_day)
            computed_age = calculate_age_from_dob(dob_val)
            st.info(f"🎂 **Calculated Age:** {computed_age} years old ({dob_val.strftime('%b %d, %Y')})")

        with col_b:
            # Sex assigned at birth: Male, Female, Intersex, Prefer not to say
            sex_options = ["Male", "Female", "Intersex", "Prefer not to say"]
            saved_sex = st.session_state.wizard_step1.get("sex_assigned_at_birth", "Prefer not to say")
            sex_idx = sex_options.index(saved_sex) if saved_sex in sex_options else 3
            sex_assigned_val = st.selectbox(
                "Sex Assigned at Birth (optional)",
                options=sex_options,
                index=sex_idx,
                help="Biological sex assigned at birth on official medical records. Used for physiological reference baselines.",
            )

            # Gender identity: Woman, Man, Non-binary, Self-describe, Prefer not to say (Optional)
            gender_options = ["Woman", "Man", "Non-binary", "Self-describe", "Prefer not to say"]
            saved_gender = st.session_state.wizard_step1.get("gender_identity", "Prefer not to say")
            if saved_gender in gender_options:
                gender_idx = gender_options.index(saved_gender)
            elif saved_gender and saved_gender not in ["", "Prefer not to say"]:
                gender_idx = gender_options.index("Self-describe")
            else:
                gender_idx = gender_options.index("Prefer not to say")

            gender_identity_val = st.selectbox(
                "Gender Identity (optional)",
                options=gender_options,
                index=gender_idx,
                help="Optional. Your current gender identity. Used for respectful and personalized communication.",
            )

            self_describe_val = ""
            if gender_identity_val == "Self-describe":
                self_describe_val = st.text_input(
                    "Please specify your gender identity",
                    value=saved_gender if saved_gender not in gender_options else "",
                    placeholder="Enter gender identity",
                )

        st.markdown("<br>", unsafe_allow_html=True)
        nav_cols = st.columns([1.5, 1.5, 3])

        with nav_cols[0]:
            if st.button("Continue to Step 2 ➔", type="primary", use_container_width=True):
                if not pref_name_val.strip():
                    st.error("Please enter a Preferred Name.")
                else:
                    final_gender = None
                    if gender_identity_val == "Self-describe":
                        final_gender = self_describe_val.strip() if self_describe_val.strip() else "Self-describe"
                    elif gender_identity_val != "Prefer not to say":
                        final_gender = gender_identity_val

                    st.session_state.wizard_step1 = {
                        "preferred_name": pref_name_val.strip(),
                        "dob": dob_val,
                        "sex_assigned_at_birth": sex_assigned_val if sex_assigned_val != "Prefer not to say" else None,
                        "gender_identity": final_gender,
                    }
                    st.session_state.onboarding_step = 2
                    st.rerun()

        with nav_cols[1]:
            if is_editing and st.button("Cancel & Return", use_container_width=True):
                st.session_state.editing_profile = False
                st.session_state.onboarding_step = 1
                st.session_state.wizard_step1 = {}
                st.session_state.wizard_meds = []
                st.rerun()

    # -----------------------------------------------------------------------
    # STEP 2: Medical Information
    # -----------------------------------------------------------------------
    elif step == 2:
        st.markdown("#### Step 2: Medical Information")
        st.caption("Provide baseline medical conditions, allergies, and active medications. All fields are optional.")

        # Prepopulate step 2 defaults from profile if wizard_meds is empty
        if not st.session_state.wizard_meds and existing_prof and existing_prof["current_medications"]:
            med_items = [m.strip() for m in existing_prof["current_medications"].split(",") if m.strip()]
            st.session_state.wizard_meds = [{"desc": m} for m in med_items]

        col_med_l, col_med_r = st.columns(2)

        with col_med_l:
            st.markdown("##### Existing Medical Conditions")
            saved_conds = existing_prof["medical_conditions"] if existing_prof and existing_prof["medical_conditions"] else ""
            default_selected_conds = [c for c in COMMON_CONDITIONS if c in saved_conds]
            selected_conditions = st.multiselect(
                "Select all conditions that apply",
                options=COMMON_CONDITIONS,
                default=default_selected_conds,
                help="Select known antecedent conditions. These help verify medication safety.",
            )

            other_cond_text = ""
            if "Other" in selected_conditions:
                other_cond_text = st.text_input("Specify other medical condition(s)", placeholder="e.g. Celiac disease, Glaucoma")

        with col_med_r:
            st.markdown("##### Known Allergies")
            saved_allergies = existing_prof["known_allergies"] if existing_prof and existing_prof["known_allergies"] else ""
            default_selected_allergies = [a for a in COMMON_ALLERGIES if a in saved_allergies]
            selected_allergies = st.multiselect(
                "Select known allergies",
                options=COMMON_ALLERGIES,
                default=default_selected_allergies,
                help="Documenting drug and substance allergies prevents contraindicated recommendations.",
            )

            other_allergy_text = ""
            if "Other" in selected_allergies:
                other_allergy_text = st.text_input("Specify other allergy / allergies", placeholder="e.g. Codeine, Eggs")

        st.markdown("---")
        st.markdown("##### Current Medications")
        st.caption("Add medications you are actively taking with their strength and frequency.")

        # Interactive medication adder
        med_c1, med_c2, med_c3, med_c4 = st.columns([3, 2, 3, 2])
        with med_c1:
            new_med_name = st.text_input("Medication Name", placeholder="e.g. Metformin", key="input_new_med_name")
        with med_c2:
            new_med_strength = st.text_input("Strength / Dose", placeholder="e.g. 500 mg", key="input_new_med_strength")
        with med_c3:
            new_med_freq = st.selectbox("Frequency", options=MED_FREQUENCIES, key="input_new_med_freq")
        with med_c4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Add Medication", use_container_width=True):
                if new_med_name.strip():
                    item_desc = new_med_name.strip()
                    if new_med_strength.strip():
                        item_desc += f" {new_med_strength.strip()}"
                    if new_med_freq:
                        item_desc += f" ({new_med_freq})"
                    st.session_state.wizard_meds.append({"desc": item_desc})
                    st.rerun()

        # Display added medications list
        if st.session_state.wizard_meds:
            st.markdown("**Active Medications List:**")
            for idx, med_obj in enumerate(st.session_state.wizard_meds):
                med_display = med_obj.get("desc") or med_obj.get("name") or "Medication"
                mc_pill, mc_del = st.columns([6, 1])
                with mc_pill:
                    st.markdown(
                        f"""
                        <div class="med-item-pill">
                            <span>💊 <strong>{med_display}</strong></span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with mc_del:
                    if st.button("Remove", key=f"del_med_{idx}", use_container_width=True):
                        st.session_state.wizard_meds.pop(idx)
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### Relevant Medical History")
        default_history = existing_prof["medical_history"] if existing_prof and existing_prof["medical_history"] else ""
        history_text = st.text_area(
            "Past surgeries, hospitalizations, or family medical history (optional)",
            value=default_history,
            placeholder="e.g. Appendectomy in 2018, family history of cardiovascular disease...",
            height=100,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        btn_nav = st.columns([1.5, 2, 2.5, 1.5])

        with btn_nav[0]:
            if st.button("⬅ Back to Step 1", use_container_width=True):
                st.session_state.onboarding_step = 1
                st.rerun()

        with btn_nav[1]:
            if not is_editing and st.button("Skip Optional & Finish", use_container_width=True):
                step1 = st.session_state.wizard_step1
                dob_str = step1["dob"].isoformat() if "dob" in step1 else None
                save_patient_profile(
                    user_id=st.session_state.user_id,
                    profile_data={
                        "preferred_name": step1["preferred_name"],
                        "age_or_dob": dob_str,
                        "sex_assigned_at_birth": step1.get("sex_assigned_at_birth"),
                        "gender_identity": step1.get("gender_identity"),
                        "medical_conditions": None,
                        "known_allergies": None,
                        "current_medications": None,
                        "medical_history": None,
                    },
                )
                st.session_state.editing_profile = False
                st.session_state.onboarding_step = 1
                st.session_state.wizard_step1 = {}
                st.session_state.wizard_meds = []
                st.rerun()

        with btn_nav[2]:
            save_btn_label = "Save Changes & Return ➔" if is_editing else "Save Profile & Start ➔"
            if st.button(save_btn_label, type="primary", use_container_width=True):
                step1 = st.session_state.wizard_step1
                dob_str = step1["dob"].isoformat() if "dob" in step1 else None

                # Compile conditions
                conds_list = [c for c in selected_conditions if c != "Other"]
                if other_cond_text.strip():
                    conds_list.append(other_cond_text.strip())
                final_conds = ", ".join(conds_list) if conds_list else None

                # Compile allergies
                allergies_list = [a for a in selected_allergies if a != "Other"]
                if other_allergy_text.strip():
                    allergies_list.append(other_allergy_text.strip())
                final_allergies = ", ".join(allergies_list) if allergies_list else None

                # Compile medications
                med_list = [m.get("desc") or m.get("name") for m in st.session_state.wizard_meds if (m.get("desc") or m.get("name"))]
                final_meds = ", ".join(med_list) if med_list else None

                save_patient_profile(
                    user_id=st.session_state.user_id,
                    profile_data={
                        "preferred_name": step1["preferred_name"],
                        "age_or_dob": dob_str,
                        "sex_assigned_at_birth": step1.get("sex_assigned_at_birth"),
                        "gender_identity": step1.get("gender_identity"),
                        "medical_conditions": final_conds,
                        "known_allergies": final_allergies,
                        "current_medications": final_meds,
                        "medical_history": history_text.strip() if history_text.strip() else None,
                    },
                )
                st.session_state.editing_profile = False
                st.session_state.onboarding_step = 1
                st.session_state.wizard_step1 = {}
                st.session_state.wizard_meds = []
                st.rerun()

        with btn_nav[3]:
            if is_editing and st.button("Cancel", use_container_width=True):
                st.session_state.editing_profile = False
                st.session_state.onboarding_step = 1
                st.session_state.wizard_step1 = {}
                st.session_state.wizard_meds = []
                st.rerun()


# ---------------------------------------------------------------------------
# Part 3: Sidebar Navigation with Search & Controls
# ---------------------------------------------------------------------------

def show_sidebar(patient_profile: dict | None) -> None:
    """Render left sidebar with brand logo, search, conversation history, and user controls."""
    # Automatically clean up any empty conversations to avoid clutter
    if st.session_state.user_id:
        delete_empty_conversations(st.session_state.user_id)

    # Brand logo & title
    st.sidebar.markdown(
        """
        <div class="brand-container">
            <div class="brand-logo">🩺</div>
            <div>
                <div class="brand-text-title">ClinCoherence</div>
                <div class="brand-text-sub">Longitudinal Clinical Assistant</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Prominent New Chat Button (switches to welcome screen without inserting empty DB records)
    if st.sidebar.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.conv_id = None
        st.session_state.editing_profile = False
        st.rerun()

    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    # Search conversations (searches both conversation titles and message content)
    search_q = st.sidebar.text_input(
        "Search conversations",
        value=st.session_state.chat_search_query,
        placeholder="🔍 Search past chats...",
        label_visibility="collapsed",
    )
    st.session_state.chat_search_query = search_q

    st.sidebar.caption("CONVERSATION HISTORY")

    convs = get_conversations_for_user(st.session_state.user_id, search_q)

    if not convs:
        if search_q.strip():
            st.sidebar.caption("No matching conversations found.")
        else:
            st.sidebar.caption("No conversations yet. Start a new chat above!")
    else:
        for conv in convs:
            updated_date = conv["updated_at"][:10]
            label = f"{conv['title']} • {updated_date}"
            is_active = st.session_state.conv_id == conv["id"] and not st.session_state.editing_profile
            btn_label = f"👉 {label}" if is_active else label
            if st.sidebar.button(
                btn_label, key=f"side_conv_{conv['id']}", use_container_width=True
            ):
                st.session_state.conv_id = conv["id"]
                st.session_state.editing_profile = False
                st.rerun()

    st.sidebar.markdown("---")

    # Profile Card
    pref_name = patient_profile.get("preferred_name") if patient_profile else st.session_state.username
    age_str = get_age_display(patient_profile.get("age_or_dob")) if patient_profile else ""
    sex_str = patient_profile.get("sex_assigned_at_birth") if patient_profile else None

    meta_parts = []
    if age_str and age_str != "Unknown":
        meta_parts.append(age_str)
    if sex_str and sex_str != "Prefer not to say":
        meta_parts.append(sex_str)
    meta_line = " • ".join(meta_parts) if meta_parts else "Profile Active"

    st.sidebar.markdown(
        f"""
        <div class="sidebar-profile-card">
            <div class="sidebar-profile-name">👤 {pref_name}</div>
            <div class="sidebar-profile-meta">{meta_line}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_btn_edit, col_btn_out = st.sidebar.columns(2)
    with col_btn_edit:
        if st.button("✏️ Edit Profile", use_container_width=True):
            st.session_state.wizard_step1 = {}
            st.session_state.wizard_meds = []
            st.session_state.editing_profile = True
            st.session_state.onboarding_step = 1
            st.rerun()
    with col_btn_out:
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.conv_id = None
            st.session_state.editing_profile = False
            st.session_state.onboarding_step = 1
            st.session_state.wizard_step1 = {}
            st.session_state.wizard_meds = []
            st.session_state.page = "login"
            st.rerun()


# ---------------------------------------------------------------------------
# Part 4 & 5: Compact Patient Context & Verification Details Panel
# ---------------------------------------------------------------------------

def show_compact_patient_context(patient_profile: dict | None) -> None:
    """Render an unobtrusive, compact patient context summary banner."""
    if not patient_profile:
        return

    pref_name = patient_profile.get("preferred_name", "Patient")
    age_disp = get_age_display(patient_profile.get("age_or_dob"))
    sex = patient_profile.get("sex_assigned_at_birth")
    gender = patient_profile.get("gender_identity")

    demo_parts = [f"👤 {pref_name}"]
    if age_disp and age_disp != "Unknown":
        demo_parts.append(age_disp)
    if sex and sex != "Prefer not to say":
        demo_parts.append(f"Sex: {sex}")
    if gender and gender != "Prefer not to say":
        demo_parts.append(f"Gender: {gender}")

    chips_html = [f'<span class="context-chip chip-demographic">{" • ".join(demo_parts)}</span>']

    conds = patient_profile.get("medical_conditions")
    if conds:
        for c in conds.split(",")[:3]:
            chips_html.append(f'<span class="context-chip chip-condition">📋 {c.strip()}</span>')

    allergies = patient_profile.get("known_allergies")
    if allergies:
        for a in allergies.split(",")[:2]:
            chips_html.append(f'<span class="context-chip chip-allergy">⚠️ Allergy: {a.strip()}</span>')

    meds = patient_profile.get("current_medications")
    if meds:
        for m in meds.split(",")[:3]:
            chips_html.append(f'<span class="context-chip chip-med">💊 {m.strip()}</span>')

    chips_str = "".join(chips_html)

    st.markdown(
        f"""
        <div class="context-banner">
            <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; letter-spacing: 0.04em; margin-bottom: 0.25rem;">
                ACTIVE PATIENT BASELINE CONTEXT
            </div>
            <div>{chips_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_verification_expander(payload: dict) -> None:
    """Render clean verification and provenance details under assistant responses."""
    ver = payload.get("verification", {})
    gate_decision = ver.get("gate_decision", "PASS")
    reasoning = ver.get("reasoning", "No coherence issues detected.")

    badge_map = {
        "PASS": ("gate-pass", "✅ PASS"),
        "WARN": ("gate-warn", "⚠️ WARN"),
        "CLARIFY": ("gate-clarify", "ℹ️ CLARIFY"),
        "REFUSE": ("gate-refuse", "🚨 REFUSE"),
    }
    badge_class, badge_label = badge_map.get(gate_decision, ("gate-pass", f"✅ {gate_decision}"))

    # Highlight non-PASS gate decisions with prominent alerts
    if gate_decision == "REFUSE":
        st.error(f"🚨 **COHERENCE GATE: REFUSE** — Response blocked for clinical safety: {reasoning}")
    elif gate_decision == "WARN":
        st.warning(f"⚠️ **COHERENCE GATE: WARN** — Clinical incoherence detected: {reasoning}")
    elif gate_decision == "CLARIFY":
        st.info(f"ℹ️ **COHERENCE GATE: CLARIFY** — Clarification recommended: {reasoning}")

    expander_icon = {"PASS": "🔍", "WARN": "⚠️", "CLARIFY": "ℹ️", "REFUSE": "🚨"}.get(gate_decision, "🔍")
    is_expanded = gate_decision != "PASS"

    with st.expander(f"{expander_icon} Clinical Verification & Provenance — [{gate_decision}]", expanded=is_expanded):
        # Decision Gate Banner
        st.markdown(
            f"""
            <div class="gate-badge {badge_class}">
                Decision Gate: {badge_label}
            </div>
            <div style="font-size: 0.85rem; color: #475569; margin-bottom: 0.75rem;">
                <strong>Reasoning:</strong> {reasoning}
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_l, col_r = st.columns(2)

        with col_l:
            # 1. Extracted Facts
            st.markdown(
                """
                <div class="verif-card-title">1. Newly Extracted Clinical Facts</div>
                """,
                unsafe_allow_html=True,
            )
            facts = payload.get("facts", [])
            if facts:
                for f in facts:
                    pol = "➕" if f.get("status") == "positive" else ("➖" if f.get("status") == "negative" else "❓")
                    typ = "[Antecedent]" if f.get("is_antecedent") else "[Symptom]"
                    st.markdown(
                        f"- **{pol} {f.get('description')}** (`{f.get('fact_id')}`) {typ} — "
                        f"status: `{f.get('status')}`, confidence: `{f.get('confidence', 0.7):.0%}`"
                    )
            else:
                st.caption("No new clinical facts extracted in this turn.")

            # 2. Longitudinal State
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                """
                <div class="verif-card-title">2. Longitudinal Patient State</div>
                """,
                unsafe_allow_html=True,
            )
            state_sum = payload.get("state_summary", {})
            if state_sum:
                v = state_sum.get("version", 0)
                t = state_sum.get("turn_number", 0)
                fc = state_sum.get("facts_count", 0)
                meds = state_sum.get("medications", [])
                st.markdown(f"- **Version**: v{v} (Turn {t})")
                st.markdown(f"- **Total Facts Tracked**: {fc}")
                st.markdown(f"- **Tracked Medications**: {', '.join(meds) if meds else 'None'}")

                contradictions = state_sum.get("contradictions", [])
                if contradictions:
                    st.warning(f"⚠️ Longitudinal Contradictions Detected ({len(contradictions)}):")
                    for c in contradictions:
                        st.markdown(f"  - `{c[0]}` changed: {c[1]} → {c[2]}")
                else:
                    st.caption("No longitudinal contradictions detected.")
            else:
                st.caption("State summary not available.")

            # 3. Changes from Prior Turn
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                """
                <div class="verif-card-title">3. Changes from Prior Turn</div>
                """,
                unsafe_allow_html=True,
            )
            changes = state_sum.get("changes_from_prior_turn", "No state changes from previous turn.")
            st.info(changes)

        with col_r:
            # 4. Medication Normalization (RxNorm)
            st.markdown(
                """
                <div class="verif-card-title">4. Medication Normalization (RxNorm)</div>
                """,
                unsafe_allow_html=True,
            )
            med_analysis = payload.get("medication_analysis", [])
            if med_analysis:
                for ma in med_analysis:
                    res_status = "✅ Resolved" if ma.get("resolved") else "⚠️ Unresolved"
                    st.markdown(
                        f"- **{ma.get('mention')}** ({res_status}): "
                        f"RxCUI: `{ma.get('rxcui')}`, Concept: `{ma.get('normalized_name')}`, "
                        f"Method: `{ma.get('match_method')}`"
                    )
                    st.caption(ma.get("explanation", ""))
            else:
                st.caption("No medication mentions detected in this turn.")

            # 5. Retrieved DailyMed Evidence
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                """
                <div class="verif-card-title">5. DailyMed Evidence & Provenance</div>
                """,
                unsafe_allow_html=True,
            )
            evidence = payload.get("evidence", [])
            if evidence:
                for e in evidence:
                    st.markdown(
                        f"- **[{e.get('evidence_id')}]** `{e.get('active_ingredient')}` ({e.get('section_name')}): "
                        f"{e.get('evidence_text')}... [DailyMed Source]({e.get('source_url')})"
                    )
            else:
                ev_expl = payload.get("evidence_explanation") or (
                    "No matching DailyMed evidence found. The local DailyMed corpus is limited to the "
                    "Alogliptin / Metformin combination product (24 records). Evidence retrieval returns empty results for other medications."
                )
                st.caption(ev_expl)

            # 6. Coherence Flags
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                """
                <div class="verif-card-title">6. Coherence Flags (5 Deterministic Checks)</div>
                """,
                unsafe_allow_html=True,
            )
            flags = ver.get("flags", [])
            if flags:
                for flag in flags:
                    sev = flag.get("severity", "WARNING")
                    cid = flag.get("check_id", "FLAG")
                    desc = flag.get("description", "")
                    if sev == "ERROR":
                        st.error(f"🚨 **[{cid}]**: {desc}")
                    else:
                        st.warning(f"⚠️ **[{cid}]**: {desc}")
            else:
                st.caption("✅ All 5 deterministic coherence checks passed without issues.")


# ---------------------------------------------------------------------------
# Helper: Start Consultation With Initial Message
# ---------------------------------------------------------------------------

def _start_conversation_with_message(user_msg: str, title: str, patient_profile: dict | None) -> None:
    """Helper to initialize a new conversation with a first message and run pipeline."""
    with st.spinner("Analyzing clinical state & verifying coherence..."):
        new_cid = create_conversation(st.session_state.user_id, title)
        st.session_state.conv_id = new_cid
        add_message(new_cid, "user", user_msg)
        result = run_pipeline(user_msg, new_cid, 0, [], patient_profile=patient_profile)
        asst_id = add_message(new_cid, "assistant", result["response_text"])
        payload = {
            "verification": result["verification"],
            "facts": result["facts"],
            "state_summary": result["state_summary"],
            "evidence": result["evidence"],
            "evidence_explanation": result.get("evidence_explanation", ""),
            "medication_analysis": result.get("medication_analysis", []),
        }
        save_verification_result(
            asst_id,
            json.dumps(payload),
            result["verification"]["gate_decision"],
            result["verification"]["reasoning"],
        )
    st.rerun()


# ---------------------------------------------------------------------------
# Part 3: Main Chat Interface & Starters
# ---------------------------------------------------------------------------

def show_main_chat(patient_profile: dict | None) -> None:
    """Render main conversational chat interface with ChatGPT-style starters and bubbles."""
    show_sidebar(patient_profile)

    # Route if profile edit mode requested
    if st.session_state.editing_profile:
        show_onboarding_page(is_editing=True)
        return

    # Render compact baseline patient context banner
    show_compact_patient_context(patient_profile)

    # If no conversation active, show attractive welcome screen
    if st.session_state.conv_id is None:
        pref_name = patient_profile.get("preferred_name") if patient_profile else st.session_state.username

        st.markdown(
            f"""
            <div class="welcome-container">
                <div class="welcome-logo-badge">🩺</div>
                <h1 class="welcome-title">How can I help you today, {pref_name}?</h1>
                <div class="welcome-desc">
                    I track your symptoms across conversation turns, normalize your medications against RxNorm, 
                    and verify clinical coherence using evidence-based medical records.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("##### Suggested conversation starters")
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            if st.button("🌡️ **Describe my symptoms**\n\nI have had a fever and mild fatigue for two days", use_container_width=True):
                _start_conversation_with_message(
                    "I have had a fever and mild fatigue for two days",
                    "Fever & Fatigue Consultation",
                    patient_profile,
                )

            if st.button("📋 **Update my health history**\n\nI want to report an update on my medical conditions", use_container_width=True):
                _start_conversation_with_message(
                    "I would like to update my active health profile and report my current symptoms",
                    "Health History Update",
                    patient_profile,
                )

        with col_s2:
            if st.button("💊 **Discuss a medication**\n\nI am taking Metformin 500mg and have questions about side effects", use_container_width=True):
                _start_conversation_with_message(
                    "I am taking Metformin 500mg and feeling slightly dizzy",
                    "Metformin Query",
                    patient_profile,
                )

            if st.button("🔄 **Continue health discussion**\n\nLet's follow up on symptoms from my previous discussion", use_container_width=True):
                _start_conversation_with_message(
                    "Can we review my baseline health profile and discuss follow-up care?",
                    "Follow-up Consultation",
                    patient_profile,
                )

        # Allow user to type in chat input directly from welcome screen
        welcome_user_input = st.chat_input("Message ClinCoherence...")
        if welcome_user_input:
            title = welcome_user_input[:35].strip() + ("..." if len(welcome_user_input.strip()) > 35 else "")
            _start_conversation_with_message(welcome_user_input, title, patient_profile)
        return

    # Conversation Active — Check Ownership
    conv = get_conversation(st.session_state.conv_id, st.session_state.user_id)
    if conv is None:
        st.error("Conversation not found or access denied.")
        st.session_state.conv_id = None
        return

    # Chat Header
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.75rem; margin-bottom: 1rem;">
            <div>
                <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #0f172a;">💬 {conv['title']}</h3>
                <small style="color: #64748b;">Active longitudinal state tracking & coherence verification enabled</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render Messages
    messages = get_messages(st.session_state.conv_id)

    for msg in messages:
        time_str = msg["created_at"][:16].replace("T", " ")
        if msg["role"] == "user":
            formatted_text = format_chat_text(msg['content'])
            st.markdown(
                f"""
                <div class="chat-row-user">
                    <div style="display: flex; flex-direction: column; align-items: flex-end; max-width: 80%;">
                        <div class="chat-bubble-user">
                            {formatted_text}
                        </div>
                        <div class="chat-timestamp-subtle" style="text-align: right; padding-right: 0.5rem;">{time_str} UTC</div>
                    </div>
                    <div class="chat-avatar-user" title="You">🧑</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            formatted_text = format_chat_text(msg['content'])
            st.markdown(
                f"""
                <div class="chat-row-assistant">
                    <div class="chat-avatar-assistant" title="ClinCoherence Assistant">🩺</div>
                    <div style="display: flex; flex-direction: column; align-items: flex-start; max-width: 85%; width: 100%;">
                        <div class="chat-bubble-assistant">
                            {formatted_text}
                        </div>
                        <div class="chat-timestamp-subtle" style="padding-left: 0.5rem;">{time_str} UTC</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            ver_record = get_verification_result(msg["id"])
            if ver_record:
                try:
                    raw_payload = json.loads(ver_record["flags_json"])
                    if isinstance(raw_payload, dict) and "verification" in raw_payload:
                        payload = raw_payload
                    else:
                        payload = {
                            "verification": raw_payload if isinstance(raw_payload, dict) else {},
                            "facts": [],
                            "state_summary": {},
                            "evidence": [],
                            "evidence_explanation": "",
                            "medication_analysis": [],
                        }
                        payload["verification"]["gate_decision"] = ver_record["gate_decision"]
                        payload["verification"]["reasoning"] = ver_record["reasoning"]
                except Exception:
                    payload = {
                        "verification": {
                            "gate_decision": ver_record["gate_decision"],
                            "reasoning": ver_record["reasoning"],
                            "flags": [],
                        },
                        "facts": [],
                        "state_summary": {},
                        "evidence": [],
                        "evidence_explanation": "",
                        "medication_analysis": [],
                    }
                show_verification_expander(payload)

    # Chat Input fixed at bottom
    user_input = st.chat_input("Message ClinCoherence...")
    if user_input:
        turn_index = len(messages)
        prior_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        # Save user message to database
        add_message(st.session_state.conv_id, "user", user_input)

        # Run pipeline with clean spinner
        with st.spinner("Analyzing clinical state & verifying coherence..."):
            result = run_pipeline(
                user_message=user_input,
                conversation_id=st.session_state.conv_id,
                turn_index=turn_index,
                prior_messages=prior_messages,
                patient_profile=patient_profile,
            )

        # Save assistant message & full verification payload
        asst_msg_id = add_message(
            st.session_state.conv_id, "assistant", result["response_text"]
        )

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

    # Route 1: Not signed in -> Auth View
    if st.session_state.page == "login" or st.session_state.user_id is None:
        show_auth_page()
        return

    # Check profile
    profile_row = get_patient_profile(st.session_state.user_id)
    profile_dict = dict(profile_row) if profile_row else None

    # Route 2: Signed in but onboarding profile incomplete -> 2-Step Wizard
    if profile_dict is None:
        show_onboarding_page(is_editing=False)
        return

    # Route 3: Main Chatbot App
    show_main_chat(profile_dict)


if __name__ == "__main__":
    main()
else:
    main()
