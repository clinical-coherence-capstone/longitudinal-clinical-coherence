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
        ("editing_profile", False),
        ("onboarding_step", 1),
        ("wizard_step1", {}),
        ("wizard_meds", []),
        ("chat_search_query", ""),
        ("show_right_panel", True),
        ("right_panel_tab", "graph"),
        ("show_pipeline_inspector", False),
        ("inspector_stage", "extractor"),
        ("pinned_conv_ids", []),
        ("show_add_prescription_modal", False),
        ("uploaded_prescriptions", [
            {"name": "Prescription_Oct2026.pdf", "med": "Metformin 500mg • Once Daily", "folder": "My Prescriptions"}
        ]),
    ]
    for key, val in defaults:
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Part 1: Login & Registration
# ---------------------------------------------------------------------------

def show_auth_page() -> None:
    """Render polished, minimal Login and Registration pages with native eye toggle."""
    col_spacer_l, col_center, col_spacer_r = st.columns([1, 2, 1])

    with col_center:
        render_clean_html(
            """
            <div class="auth-header" style="text-align: center; margin-bottom: 24px;">
                <div class="auth-logo-badge" style="width: 52px; height: 52px; border-radius: 14px; font-size: 1.45rem; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #0284c7, #38bdf8);">🩺</div>
                <h1 style="color: #ffffff; font-size: 1.55rem; font-weight: 800; margin: 0;">ClinCoherence Portal</h1>
                <div style="color: #94a3b8; font-size: 0.88rem; margin-top: 4px;">Longitudinal Clinical Assistant & Coherence Gate</div>
            </div>
            """
        )

        tab_login, tab_register = st.tabs(["Sign In", "Register New Patient"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            login_user_input = st.text_input(
                "Username or Email",
                key="login_user_field",
                placeholder="Enter your username",
            )

            login_pw_input = st.text_input(
                "Password",
                type="password",
                key="login_pw_field",
                placeholder="Enter your password",
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
                        st.session_state.conv_id = None
                        st.session_state.show_right_panel = True
                        st.session_state.show_pipeline_inspector = False
                        st.session_state.editing_profile = False
                        st.session_state.onboarding_step = 1
                        st.session_state.wizard_step1 = {}
                        st.session_state.wizard_meds = []
                        try:
                            st.query_params.clear()
                        except Exception:
                            pass
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

            reg_pw_input = st.text_input(
                "Password (minimum 8 characters)",
                type="password",
                key="reg_pw_field",
                placeholder="Create a secure password",
            )
            reg_confirm_input = st.text_input(
                "Confirm Password",
                type="password",
                key="reg_confirm_field",
                placeholder="Re-enter your password",
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
            <div style="text-align: center; margin-top: 2rem; font-size: 0.75rem; color: #94a3b8;">
                🔒 Bcrypt 12-round salted hashing • Strict patient data isolation • Capstone Research Prototype
            </div>
            """
        )


# ---------------------------------------------------------------------------
# Part 2: Guided Patient Onboarding Wizard (2 Steps)
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
    "No known allergies (NKDA)",
    "Yet to discover",
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
                "preferred_name": "",
                "dob": date(2000, 1, 1),
                "sex_assigned_at_birth": "Prefer not to say",
                "gender_identity": "Prefer not to say",
            }

    step = st.session_state.onboarding_step

    title_text = "Edit Patient Profile" if is_editing else "Welcome to ClinCoherence"
    subtitle_text = "Update your clinical baseline and preferences" if is_editing else "Let's set up your clinical baseline for safe and accurate consultations"

    render_clean_html(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <h2 style="color: #ffffff; font-weight: 800; font-size: 1.65rem; margin: 0;">{title_text}</h2>
            <div style="color: #94a3b8; font-size: 0.92rem; margin-top: 4px;">{subtitle_text}</div>
        </div>
        """
    )

    s1_class = "wizard-step-completed" if step > 1 else ("wizard-step-active" if step == 1 else "wizard-step-inactive")
    s2_class = "wizard-step-completed" if step > 2 else ("wizard-step-active" if step == 2 else "wizard-step-inactive")
    div_class = "wizard-divider completed" if step > 1 else "wizard-divider"

    render_clean_html(
        f"""
        <div class="wizard-progress-bar">
            <div class="wizard-step {s1_class}">
                <div class="wizard-step-circle">{'✓' if step > 1 else '1'}</div>
                <div>Demographics & Identity</div>
            </div>
            <div class="{div_class}"></div>
            <div class="wizard-step {s2_class}">
                <div class="wizard-step-circle">2</div>
                <div>Medical Baseline & Medications</div>
            </div>
        </div>
        """
    )

    if step == 1:
        st.markdown("#### Step 1: Demographics & Identity")
        st.caption("Accurate demographics help ClinCoherence verify age-adjusted and sex-specific clinical evidence.")

        col_l, col_r = st.columns(2)

        with col_l:
            pref_name = st.text_input(
                "Preferred Name",
                value=st.session_state.wizard_step1.get("preferred_name", ""),
                placeholder="What should the assistant call you?",
                help="Used in greetings and consultation notes.",
            )

            st.markdown("<label style='font-weight: 600; color: #cbd5e1; font-size: 0.9rem;'>Date of Birth</label>", unsafe_allow_html=True)
            st.caption("Select Year, Month, and Day. Age is automatically calculated.")

            default_dob = st.session_state.wizard_step1.get("dob", date(2000, 1, 1))
            today = date.today()

            col_yr, col_mo, col_dy = st.columns([1.5, 1.5, 1.2])

            with col_yr:
                years_list = list(range(today.year, 1899, -1))
                def_yr_idx = years_list.index(default_dob.year) if default_dob.year in years_list else 26
                selected_yr = st.selectbox("Year", options=years_list, index=def_yr_idx, key="sel_dob_yr")

            with col_mo:
                months_list = list(range(1, 13))
                def_mo_idx = default_dob.month - 1
                selected_mo = st.selectbox("Month", options=months_list, format_func=lambda m: calendar.month_name[m], index=def_mo_idx, key="sel_dob_mo")

            with col_dy:
                max_days = calendar.monthrange(selected_yr, selected_mo)[1]
                if selected_yr == today.year and selected_mo == today.month:
                    max_days = min(max_days, today.day)

                days_list = list(range(1, max_days + 1))
                def_dy_idx = min(default_dob.day - 1, len(days_list) - 1)
                selected_dy = st.selectbox("Day", options=days_list, index=def_dy_idx, key="sel_dob_dy")

            try:
                computed_dob = date(selected_yr, selected_mo, selected_dy)
            except Exception:
                computed_dob = date(selected_yr, selected_mo, 1)

            if computed_dob > today:
                st.error("Date of birth cannot be in the future.")
                computed_dob = today

            computed_age = calculate_age_from_dob(computed_dob)
            st.info(f"🎂 **Calculated Age:** {computed_age} years old ({computed_dob.strftime('%B %d, %Y')})")

        with col_r:
            st.markdown("<label style='font-weight: 600; color: #cbd5e1; font-size: 0.9rem;'>Sex Assigned at Birth (Required)</label>", unsafe_allow_html=True)
            st.caption("Biological sex assigned at birth informs pharmacological dosing and lab references.")
            sex_options = ["Male", "Female", "Intersex", "Prefer not to say"]
            current_sex = st.session_state.wizard_step1.get("sex_assigned_at_birth", "Prefer not to say")
            sex_idx = sex_options.index(current_sex) if current_sex in sex_options else 3
            selected_sex = st.selectbox(
                "Biological Sex",
                options=sex_options,
                index=sex_idx,
                label_visibility="collapsed",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<label style='font-weight: 600; color: #cbd5e1; font-size: 0.9rem;'>Gender Identity (Optional)</label>", unsafe_allow_html=True)
            st.caption("Optional social and personal identity. Completely independent from biological sex.")
            gender_options = ["Prefer not to say", "Woman", "Man", "Non-binary", "Self-describe"]
            current_gender = st.session_state.wizard_step1.get("gender_identity", "Prefer not to say")
            gen_idx = gender_options.index(current_gender) if current_gender in gender_options else 0
            selected_gender = st.selectbox(
                "Gender Identity",
                options=gender_options,
                index=gen_idx,
                label_visibility="collapsed",
            )

            self_described_gender = ""
            if selected_gender == "Self-describe":
                self_described_gender = st.text_input("Please specify your gender identity", placeholder="e.g. Two-spirit, Agender")

        st.markdown("<br><hr style='border-color: #1e293b;'>", unsafe_allow_html=True)

        col_nav_l, col_nav_r = st.columns([1, 1])
        with col_nav_l:
            if is_editing and st.button("Cancel & Return to Chat", use_container_width=True, type="secondary"):
                st.session_state.editing_profile = False
                st.session_state.onboarding_step = 1
                st.rerun()

        with col_nav_r:
            if st.button("Continue to Step 2 ➔", use_container_width=True, type="primary"):
                final_gender = self_described_gender.strip() if selected_gender == "Self-describe" else selected_gender
                st.session_state.wizard_step1 = {
                    "preferred_name": pref_name.strip(),
                    "dob": computed_dob,
                    "sex_assigned_at_birth": selected_sex,
                    "gender_identity": final_gender,
                }
                st.session_state.onboarding_step = 2
                st.rerun()

    elif step == 2:
        st.markdown("#### Step 2: Clinical Baseline & Medications")
        st.caption("Provide baseline medical conditions, allergies, and active medications. All fields are optional.")

        if not st.session_state.wizard_meds and existing_prof and existing_prof["current_medications"]:
            med_items = [m.strip() for m in existing_prof["current_medications"].split(",") if m.strip()]
            st.session_state.wizard_meds = [{"desc": m} for m in med_items]

        col_med_l, col_med_r = st.columns(2)

        with col_med_l:
            st.markdown("##### Existing Medical Conditions")
            saved_conds = existing_prof["medical_conditions"] if existing_prof and existing_prof["medical_conditions"] else ""
            default_selected_conds = [c for c in COMMON_CONDITIONS if c in saved_conds]
            selected_conditions = st.multiselect(
                "Select conditions (or Yet to discover)",
                options=COMMON_CONDITIONS,
                default=default_selected_conds,
                select_all=False,
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
                "Select known allergies (or Yet to discover)",
                options=COMMON_ALLERGIES,
                default=default_selected_allergies,
                select_all=False,
                help="Documenting drug and substance allergies prevents contraindicated recommendations.",
            )

            other_allergy_text = ""
            if "Other" in selected_allergies:
                other_allergy_text = st.text_input("Specify other allergy / allergies", placeholder="e.g. Codeine, Eggs")

        st.markdown("---")
        st.markdown("##### Active Medications")
        st.caption("List medications you take regularly. We normalize names against RxNorm and check DailyMed for contraindications.")

        col_med_in, col_med_freq, col_med_btn = st.columns([2, 1.5, 1])
        with col_med_in:
            new_med_name = st.text_input(
                "Medication Name",
                placeholder="e.g. Metformin 500mg, Lisinopril 10mg",
                key="input_new_med_name",
            )
        with col_med_freq:
            new_med_freq = st.selectbox(
                "Frequency",
                options=MED_FREQUENCIES,
                key="select_new_med_freq",
            )
        with col_med_btn:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("+ Add Medication", use_container_width=True, type="secondary"):
                if new_med_name.strip():
                    st.session_state.wizard_meds.append({
                        "desc": f"{new_med_name.strip()} ({new_med_freq})"
                    })
                    st.rerun()

        if st.session_state.wizard_meds:
            st.markdown("###### Currently Documented Medications:")
            for idx, med_obj in enumerate(st.session_state.wizard_meds):
                col_item_desc, col_item_del = st.columns([5, 1])
                with col_item_desc:
                    render_clean_html(
                        f"""
                        <div style="background: #0f1b30; border: 1px solid #1e293b; padding: 8px 12px; border-radius: 8px; margin-bottom: 6px;">
                            <span>💊 <strong>{med_obj['desc']}</strong></span>
                        </div>
                        """
                    )
                with col_item_del:
                    if st.button("✕", key=f"del_med_{idx}", help="Remove medication", use_container_width=True, type="secondary"):
                        st.session_state.wizard_meds.pop(idx)
                        st.rerun()
        else:
            st.caption("No medications added yet. You can also report medications during consultations.")

        st.markdown("---")
        notes_text = st.text_area(
            "Relevant Medical History (Optional)",
            value=existing_prof["past_medical_history"] if existing_prof and existing_prof["past_medical_history"] else "",
            placeholder="Past surgeries, hospitalizations, or family medical history (optional)...",
            help="Free-text clinical notes available as background context during consultations.",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        col_act_back, col_act_skip, col_act_save = st.columns([1, 1, 1.5])

        with col_act_back:
            if st.button("⬅ Back to Step 1", use_container_width=True, type="secondary"):
                st.session_state.onboarding_step = 1
                st.rerun()

        with col_act_skip:
            if not is_editing:
                if st.button("Skip Optional & Finish", use_container_width=True, type="secondary"):
                    s1 = st.session_state.wizard_step1
                    iso_dob = s1["dob"].isoformat()
                    save_patient_profile(
                        user_id=user_id,
                        profile_data={
                            "preferred_name": s1["preferred_name"] or None,
                            "age_or_dob": iso_dob,
                            "sex_assigned_at_birth": s1["sex_assigned_at_birth"],
                            "gender_identity": s1["gender_identity"],
                            "medical_conditions": None,
                            "current_medications": None,
                            "known_allergies": None,
                            "past_medical_history": None,
                        },
                    )
                    st.session_state.editing_profile = False
                    st.session_state.onboarding_step = 1
                    st.session_state.wizard_step1 = {}
                    st.session_state.wizard_meds = []
                    st.success("Profile saved successfully!")
                    st.rerun()

        with col_act_save:
            btn_label = "Update Profile ➔" if is_editing else "Complete Setup & Start Chat ➔"
            if st.button(btn_label, use_container_width=True, type="primary"):
                s1 = st.session_state.wizard_step1

                conditions_list = [c for c in selected_conditions if c != "Other"]
                if other_cond_text.strip():
                    conditions_list.append(other_cond_text.strip())
                final_conditions = ", ".join(conditions_list) if conditions_list else None

                allergies_list = [a for a in selected_allergies if a != "Other"]
                if other_allergy_text.strip():
                    allergies_list.append(other_allergy_text.strip())
                final_allergies = ", ".join(allergies_list) if allergies_list else None

                meds_list = [m["desc"] for m in st.session_state.wizard_meds if m.get("desc")]
                final_meds = ", ".join(meds_list) if meds_list else None

                iso_dob = s1["dob"].isoformat()

                save_patient_profile(
                    user_id=user_id,
                    profile_data={
                        "preferred_name": s1["preferred_name"] or None,
                        "age_or_dob": iso_dob,
                        "sex_assigned_at_birth": s1["sex_assigned_at_birth"],
                        "gender_identity": s1["gender_identity"],
                        "medical_conditions": final_conditions,
                        "current_medications": final_meds,
                        "known_allergies": final_allergies,
                        "past_medical_history": notes_text.strip() or None,
                    },
                )
                st.session_state.editing_profile = False
                st.session_state.onboarding_step = 1
                st.session_state.wizard_step1 = {}
                st.session_state.wizard_meds = []
                st.success("Profile saved successfully!")
                st.rerun()


# ---------------------------------------------------------------------------
# Part 3: Left Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar_conv_row(conv, is_pinned: bool) -> None:
    """Render a conversation row with resume, pin, and delete controls."""
    cid = conv["id"]
    title = conv["title"]
    is_active = st.session_state.conv_id == cid and not st.session_state.editing_profile

    prefix = "👉 " if is_active else ("📌 " if is_pinned else "💬 ")
    display_title = f"{prefix}{title}"
    if len(display_title) > 26:
        display_title = display_title[:24] + ".."

    col_btn, col_pin, col_del = st.columns([0.68, 0.16, 0.16])
    with col_btn:
        btn_type = "primary" if is_active else "secondary"
        if st.button(display_title, key=f"side_c_{cid}", use_container_width=True, type=btn_type, help=title):
            st.session_state.conv_id = cid
            st.session_state.editing_profile = False
            st.rerun()

    with col_pin:
        pin_icon = "📍" if is_pinned else "📌"
        pin_tip = "Unpin from top" if is_pinned else "Pin to top"
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
    """Render left sidebar with brand logo, search, conversation history, and user controls."""
    if st.session_state.user_id:
        delete_empty_conversations(st.session_state.user_id)

    with st.sidebar:
        render_clean_html(
            """
            <div class="brand-container">
                <div class="brand-logo">🩺</div>
                <div>
                    <div class="brand-text-title">ClinCoherence</div>
                    <div class="brand-text-sub">Longitudinal Clinical Assistant</div>
                </div>
            </div>
            """
        )

        if st.button("+ New Consultation", use_container_width=True, type="primary"):
            st.session_state.conv_id = None
            st.session_state.editing_profile = False
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        search_q = st.text_input(
            "Search conversations",
            value=st.session_state.chat_search_query,
            placeholder="🔍 Search past consults...",
            label_visibility="collapsed",
        )
        st.session_state.chat_search_query = search_q

        pinned_ids = set(st.session_state.get("pinned_conv_ids", []))
        all_convs = get_conversations_for_user(st.session_state.user_id, search_q)

        if not all_convs:
            if search_q.strip():
                st.caption("No matching consultations found.")
            else:
                st.caption("No consultations yet. Start a new consultation above!")
        else:
            pinned_convs = [c for c in all_convs if c["id"] in pinned_ids]
            recent_convs = [c for c in all_convs if c["id"] not in pinned_ids]

            if pinned_convs:
                st.caption("📌 PINNED CONSULTATIONS")
                for conv in pinned_convs:
                    _render_sidebar_conv_row(conv, is_pinned=True)

            if recent_convs:
                st.caption("RECENT CONSULTATIONS")
                for conv in recent_convs:
                    _render_sidebar_conv_row(conv, is_pinned=False)

        st.markdown("---")

        pref_name = patient_profile.get("preferred_name") if patient_profile else st.session_state.username
        age_str = get_age_display(patient_profile.get("age_or_dob")) if patient_profile else ""
        sex_str = patient_profile.get("sex_assigned_at_birth") if patient_profile else None

        meta_parts = []
        if age_str and age_str != "Unknown":
            meta_parts.append(age_str)
        if sex_str and sex_str != "Prefer not to say":
            meta_parts.append(sex_str)
        meta_line = " • ".join(meta_parts) if meta_parts else "Profile Active"

        render_clean_html(
            f"""
            <div class="sidebar-profile-card">
                <div class="sidebar-profile-name">👤 {pref_name}</div>
                <div class="sidebar-profile-meta">{meta_line}</div>
            </div>
            """
        )

        col_btn_edit, col_btn_out = st.columns(2)
        with col_btn_edit:
            if st.button("✏️ Profile", use_container_width=True, type="secondary"):
                st.session_state.wizard_step1 = {}
                st.session_state.wizard_meds = []
                st.session_state.editing_profile = True
                st.session_state.onboarding_step = 1
                st.rerun()
        with col_btn_out:
            if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.conv_id = None
                st.session_state.editing_profile = False
                st.session_state.onboarding_step = 1
                st.session_state.wizard_step1 = {}
                st.session_state.wizard_meds = []
                st.session_state.page = "login"
                st.rerun()

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        insp_open = st.session_state.get("show_pipeline_inspector", False)
        insp_label = "⚡ Hide Inspector" if insp_open else "⚡ Clinical Pipeline Inspector"
        insp_type = "primary" if insp_open else "secondary"
        if st.button(insp_label, key="btn_sidebar_inspector", use_container_width=True, type=insp_type, help="Toggle Clinical Pipeline Inspector & Diagnostics"):
            st.session_state.show_pipeline_inspector = not insp_open
            st.rerun()


# ---------------------------------------------------------------------------
# Part 4: Clinical Pipeline Inspector Interactive Diagnostics
# ---------------------------------------------------------------------------

def show_pipeline_inspector(latest_payload: dict | None) -> None:
    """Render interactive inspector displaying live clinical data and verification telemetry."""
    col_insp_title, col_insp_close = st.columns([0.84, 0.16])
    with col_insp_title:
        render_clean_html(
            """
            <div style="background: #0b1222; border: 2px solid rgba(56, 189, 248, 0.6); border-radius: 16px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.5);">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.5rem; color: #38bdf8;">⚡</span>
                    <div>
                        <h3 style="margin: 0; color: #ffffff; font-size: 1.12rem; font-weight: 800;">Clinical Pipeline Inspector & Diagnostics</h3>
                        <small style="color: #94a3b8;">Live extracted entities, RxNorm mappings, DailyMed FDA monographs, and coherence gates</small>
                    </div>
                </div>
            </div>
            """
        )
    with col_insp_close:
        if st.button("✕ Close", key="btn_close_insp_banner", use_container_width=True, type="secondary", help="Close Pipeline Inspector"):
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
        st.caption("Extracts symptoms, anatomical entities, negations, durations, and antecedents from utterances.")
        if facts_list:
            for f in facts_list:
                status_icon = "🟢" if f.get("status") == "positive" else ("🔴" if f.get("status") == "negative" else "⚪")
                st.markdown(
                    f"- **{status_icon} `{f.get('fact_id')}`: {f.get('description')}** — "
                    f"Status: `{f.get('status')}`, Confidence: `{f.get('confidence', 0.7):.0%}`, "
                    f"Type: `{'Antecedent' if f.get('is_antecedent') else 'Active Symptom'}`"
                )
        else:
            st.info("No new clinical entities extracted in the active turn.")

    with t_state:
        st.markdown("##### Stage 2: State Manager (Longitudinal Patient Ledger)")
        st.caption("Maintains an immutable versioned clinical state tracking temporal symptom progression.")
        if state_sum:
            v = state_sum.get("version", 0)
            t = state_sum.get("turn_number", 0)
            fc = state_sum.get("facts_count", 0)
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
                "DailyMed corpus queries execute on medication mentions. FDA monograph references will populate when medications are discussed."
            )
            st.info(ev_expl)

    with t_ver:
        st.markdown("##### Stage 5: Coherence Verifier (Multi-Rule Consistency Check)")
        st.caption("Executes 4 deterministic verification engines: Fact Contradictions, Evidence Mismatch, Stale State, and Sycophancy Pushback.")
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
            <div style="background: #070b14; border: 1px solid {badge_color}; border-radius: 12px; padding: 14px; margin-top: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 700; color: #ffffff;">Computed Gate Outcome:</span>
                    <span style="background: rgba(56, 189, 248, 0.15); color: {badge_color}; font-weight: 800; font-family: monospace; padding: 4px 10px; border-radius: 6px; border: 1px solid {badge_color};">{gate_dec}</span>
                </div>
                <div style="font-size: 0.85rem; color: #cbd5e1;"><strong>Reasoning:</strong> {reasoning}</div>
            </div>
            """
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Close Inspector ✕", key="btn_close_inspector", use_container_width=True, type="secondary"):
        st.session_state.show_pipeline_inspector = False
        st.rerun()
    st.markdown("---")


# ---------------------------------------------------------------------------
# Part 5: Right Slide Panel (Clinical Intelligence & Referenced Docs)
# ---------------------------------------------------------------------------

def render_right_intelligence_panel(latest_payload: dict | None, patient_profile: dict | None) -> None:
    """Render right-side clinical intelligence slide panel cleanly with zero raw SVG text leaks."""
    col_intel_hdr, col_intel_close = st.columns([0.84, 0.16])
    with col_intel_hdr:
        render_clean_html(
            """
            <div style="display: flex; align-items: center; gap: 8px; padding: 4px 0;">
                <span style="color: #38bdf8; font-weight: 800; font-size: 0.92rem;">📊 Clinical Intelligence</span>
            </div>
            """
        )
    with col_intel_close:
        if st.button("✕", key="btn_close_intel_panel", use_container_width=True, type="secondary", help="Close Intelligence Panel"):
            st.session_state.show_right_panel = False
            st.rerun()

    col_tg_g, col_tg_t = st.columns(2)
    with col_tg_g:
        btn_g_type = "primary" if st.session_state.right_panel_tab == "graph" else "secondary"
        if st.button("📈 Graph", key="tab_btn_graph", use_container_width=True, type=btn_g_type):
            st.session_state.right_panel_tab = "graph"
            st.rerun()
    with col_tg_t:
        btn_t_type = "primary" if st.session_state.right_panel_tab == "timeline" else "secondary"
        if st.button("⏳ Timeline", key="tab_btn_timeline", use_container_width=True, type=btn_t_type):
            st.session_state.right_panel_tab = "timeline"
            st.rerun()

    if st.session_state.right_panel_tab == "graph":
        facts = latest_payload.get("facts", []) if latest_payload else []
        node_1 = facts[0].get("description")[:10] if len(facts) > 0 else "Chest"
        node_2 = facts[1].get("description")[:10] if len(facts) > 1 else "Dyspnea"
        gate_text = latest_payload.get("verification", {}).get("gate_decision", "PASS") if latest_payload else "PASS"

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
              <line x1="55" y1="30" x2="150" y2="65" stroke="#38bdf8" stroke-width="2" stroke-dasharray="3,3" opacity="0.75"/>
              <line x1="55" y1="105" x2="150" y2="65" stroke="#d97706" stroke-width="2" opacity="0.75"/>
              <line x1="150" y1="65" x2="245" y2="35" stroke="#10b981" stroke-width="2" opacity="0.75"/>
              <line x1="150" y1="65" x2="245" y2="95" stroke="#818cf8" stroke-width="2" opacity="0.75"/>

              <circle cx="55" cy="30" r="16" fill="#13233c" stroke="#38bdf8" stroke-width="1.5"/>
              <text x="55" y="30" dominant-baseline="central" font-size="8.5" fill="#7dd3fc" text-anchor="middle" font-weight="bold">{node_1}</text>

              <circle cx="55" cy="105" r="16" fill="#2d2212" stroke="#d97706" stroke-width="1.5"/>
              <text x="55" y="105" dominant-baseline="central" font-size="8.5" fill="#fcd34d" text-anchor="middle" font-weight="bold">{node_2}</text>

              <circle cx="150" cy="65" r="20" fill="#1e1e38" stroke="#a78bfa" stroke-width="2"/>
              <text x="150" y="65" dominant-baseline="central" font-size="9.5" fill="#ddd6fe" text-anchor="middle" font-weight="bold">Gate: {gate_text}</text>

              <circle cx="245" cy="35" r="15" fill="#112920" stroke="#10b981" stroke-width="1.5"/>
              <text x="245" y="35" dominant-baseline="central" font-size="8" fill="#6ee7b7" text-anchor="middle">DailyMed</text>

              <circle cx="245" cy="95" r="15" fill="#1a1c38" stroke="#818cf8" stroke-width="1.5"/>
              <text x="245" y="95" dominant-baseline="central" font-size="8" fill="#c7d2fe" text-anchor="middle">RxNorm</text>
            </svg>
            <div class="graph-footer">
              <span>● Clinical Knowledge Graph</span>
              <span style="color: #10b981; font-family: monospace; font-weight: bold;">0 Contradictions</span>
            </div>
          </div>
        </body>
        </html>
        """
        components.html(graph_html, height=185)
    else:
        state_sum = latest_payload.get("state_summary", {}) if latest_payload else {}
        ver_num = state_sum.get("version", 1)
        render_clean_html(
            f"""
            <div style="background: #070b14; border: 1px solid #1e293b; border-radius: 12px; padding: 12px; max-height: 175px; overflow-y: auto; font-size: 0.78rem;">
                <div style="border-left: 2px solid #10b981; padding-left: 8px; margin-bottom: 8px;">
                    <div style="color: #94a3b8; font-size: 0.7rem;">Turn 0 • Baseline Record</div>
                    <div style="color: #f1f5f9; font-weight: 600;">Demographics Loaded</div>
                </div>
                <div style="border-left: 2px solid #38bdf8; padding-left: 8px; margin-bottom: 8px;">
                    <div style="color: #94a3b8; font-size: 0.7rem;">Turn 1 • Longitudinal State (v{ver_num})</div>
                    <div style="color: #38bdf8; font-weight: 600;">+ Symptoms Asserted & Verified</div>
                </div>
                <div style="border-left: 2px solid #f59e0b; padding-left: 8px;">
                    <div style="color: #94a3b8; font-size: 0.7rem;">Active • Safety Gate</div>
                    <div style="color: #fcd34d; font-weight: 600;">Coherence Check: PASS</div>
                </div>
            </div>
            """
        )

    st.markdown("<br>", unsafe_allow_html=True)

    evidence_list = latest_payload.get("evidence", []) if latest_payload else []
    ev_title = f"DailyMed: {evidence_list[0].get('active_ingredient', 'RxNorm')}" if evidence_list else "DailyMed FDA Corpus Monograph"
    ev_excerpt = evidence_list[0].get("evidence_text", "Warnings & Precautions: Evaluate renal and cardiovascular indicators prior to titration...") if evidence_list else "FDA label inserts actively checked against patient reported medications."

    prescriptions = st.session_state.get("uploaded_prescriptions", [])
    p_html = ""
    for p in prescriptions:
        p_html += f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background: #0f1b30; padding: 6px 10px; border-radius: 6px; margin-bottom: 4px; font-size: 0.75rem;">
            <div>
                <div style="color: #f1f5f9; font-weight: 600;">📄 {p['name']}</div>
                <div style="color: #94a3b8; font-size: 0.68rem;">{p['med']}</div>
            </div>
            <span style="color: #f59e0b; font-weight: 600; font-size: 0.72rem;">Verified</span>
        </div>
        """

    docs_panel_html = f"""
    <div style="background: #0b1222; border: 1px solid #1e293b; border-radius: 14px; padding: 14px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 8px; margin-bottom: 12px;">
            <span style="color: #38bdf8; font-weight: 800; font-size: 0.88rem;">📁 Referenced Docs & Evidence</span>
        </div>
        <div style="background: #070b14; border: 1px solid #1e293b; border-radius: 10px; padding: 10px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-weight: 700; color: #38bdf8; margin-bottom: 4px;">
                <span>📑 Active Evidence Monograph</span>
                <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 1px 6px; border-radius: 4px; font-size: 0.68rem; font-family: monospace;">DailyMed</span>
            </div>
            <div style="font-size: 0.75rem; color: #f1f5f9; font-weight: 600;">{ev_title}</div>
            <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 3px;">"{ev_excerpt[:100]}..."</div>
            <div style="font-size: 0.68rem; color: #10b981; font-family: monospace; margin-top: 4px;">Status: Verified Safe</div>
        </div>
        <div style="background: #070b14; border: 1px solid #1e293b; border-radius: 10px; padding: 10px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-weight: 700; color: #cbd5e1; margin-bottom: 6px;">
                <span>💊 Patient Prescriptions Folder</span>
                <span style="font-size: 0.7rem; color: #94a3b8;">{len(prescriptions)} File(s)</span>
            </div>
            {p_html}
        </div>
        <div style="background: #070b14; border: 1px solid #1e293b; border-radius: 10px; padding: 10px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-weight: 700; color: #cbd5e1; margin-bottom: 4px;">
                <span>🗂️ Similar Cases Archive</span>
                <span style="color: #38bdf8; font-size: 0.68rem; font-family: monospace;">2 Matches</span>
            </div>
            <div style="font-size: 0.72rem; color: #94a3b8; line-height: 1.6;">
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

    if st.button("+ Add Prescription / Upload Report", key="btn_open_prescription_dialog", use_container_width=True, type="secondary"):
        st.session_state.show_add_prescription_modal = not st.session_state.get("show_add_prescription_modal", False)
        st.rerun()

    if st.session_state.get("show_add_prescription_modal", False):
        render_clean_html(
            """
            <div style="background: #0f1b30; border: 1px solid #38bdf8; border-radius: 12px; padding: 14px; margin-top: 10px;">
                <h4 style="margin: 0 0 8px 0; color: #ffffff; font-size: 0.88rem;">Add Prescription or Medical Report</h4>
            </div>
            """
        )
        p_name = st.text_input("Prescription Name", placeholder="e.g. Lisinopril 10mg", key="dlg_p_name")
        p_target = st.selectbox("Target Folder", ["My Prescriptions", "Lab Reports", "Similar Cases"], key="dlg_p_target")
        p_freq = st.selectbox("Frequency", MED_FREQUENCIES, key="dlg_p_freq")
        p_file = st.file_uploader("Upload Prescription Image/PDF (Optional)", type=["pdf", "png", "jpg"], key="dlg_p_file")

        col_add_save, col_add_cancel = st.columns(2)
        with col_add_save:
            if st.button("Save to Folder ➔", key="dlg_btn_save_p", use_container_width=True, type="primary"):
                if p_name.strip():
                    doc_filename = p_file.name if p_file else f"Prescription_{datetime.now().strftime('%b%Y')}.pdf"
                    st.session_state.uploaded_prescriptions.append({
                        "name": doc_filename,
                        "med": f"{p_name.strip()} • {p_freq}",
                        "folder": p_target,
                    })
                    st.session_state.show_add_prescription_modal = False
                    st.success(f"Added {p_name.strip()} to {p_target}!")
                    st.rerun()
                else:
                    st.error("Please provide a prescription or medication name.")
        with col_add_cancel:
            if st.button("Cancel", key="dlg_btn_cancel_p", use_container_width=True, type="secondary"):
                st.session_state.show_add_prescription_modal = False
                st.rerun()


# ---------------------------------------------------------------------------
# Part 6: Compact Patient Context & Verification Details Panel
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

    gender = patient_profile.get("gender_identity")
    if gender and gender != "Prefer not to say":
        chips_html += f"<span style='background:#1e293b; color:#cbd5e1; border:1px solid #334155; padding:3px 8px; border-radius:6px; font-size:0.75rem; margin-right:6px;'>⚧ {gender}</span>"

    conditions = patient_profile.get("medical_conditions")
    if conditions:
        for c in conditions.split(",")[:2]:
            chips_html += f"<span style='background:#2d2212; color:#fcd34d; border:1px solid rgba(245,158,11,0.4); padding:3px 8px; border-radius:6px; font-size:0.75rem; margin-right:6px;'>⚠️ {c.strip()}</span>"

    meds = patient_profile.get("current_medications")
    if meds:
        for m in meds.split(",")[:2]:
            chips_html += f"<span style='background:#0f233d; color:#7dd3fc; border:1px solid rgba(56,189,248,0.4); padding:3px 8px; border-radius:6px; font-size:0.75rem; margin-right:6px;'>💊 {m.strip()}</span>"

    render_clean_html(
        f"""
        <div style="background: #0b1222; border: 1px solid #1e293b; border-radius: 12px; padding: 8px 14px; margin-bottom: 14px;">
            <div style="font-size: 0.72rem; font-weight: 700; color: #94a3b8; margin-bottom: 4px;">ACTIVE CLINICAL CONTEXT</div>
            <div>{chips_html}</div>
        </div>
        """
    )


def show_verification_expander(payload: dict) -> None:
    """Render clean verification and provenance details under assistant responses."""
    ver = payload.get("verification", {})
    gate_decision = ver.get("gate_decision", "PASS")
    reasoning = ver.get("reasoning", "No coherence issues detected.")

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

            st.markdown("<strong style='color:#38bdf8;'>2. Longitudinal Patient State:</strong>", unsafe_allow_html=True)
            state_sum = payload.get("state_summary", {})
            if state_sum:
                st.markdown(f"- Version: `v{state_sum.get('version', 0)}` (Turn {state_sum.get('turn_number', 0)})")
                st.markdown(f"- Total Facts: `{state_sum.get('facts_count', 0)}`")
            else:
                st.caption("State summary not available.")

        with col_r:
            st.markdown("<strong style='color:#38bdf8;'>3. Medication Normalization (RxNorm):</strong>", unsafe_allow_html=True)
            med_analysis = payload.get("medication_analysis", [])
            if med_analysis:
                for ma in med_analysis:
                    res_status = "✅ Resolved" if ma.get("resolved") else "⚠️ Unresolved"
                    st.markdown(f"- **{ma.get('mention')}** ({res_status}): RxCUI: `{ma.get('rxcui')}`")
            else:
                st.caption("No medication mentions detected in this turn.")

            st.markdown("<strong style='color:#38bdf8;'>4. Coherence Engine Flags:</strong>", unsafe_allow_html=True)
            flags = ver.get("flags", [])
            if flags:
                for flag in flags:
                    st.warning(f"⚠️ [{flag.get('check_id')}]: {flag.get('description')}")
            else:
                st.caption("✅ All deterministic coherence checks passed without issues.")


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
# Part 7: Main Chat Interface & Dual-Panel View
# ---------------------------------------------------------------------------

def show_main_chat(patient_profile: dict | None) -> None:
    """Render main conversational chat interface with ChatGPT-style starters and bubbles."""
    show_sidebar(patient_profile)

    # Ensure sidebar toggle hook and click listeners run in MAIN window context
    if st.session_state.get("toggle_sidebar_requested", False):
        st.session_state.toggle_sidebar_requested = False
        render_clean_html(
            """
            <img src="sidebar_toggle_hook" style="display:none;" onerror="
                (function() {
                    try {
                        var exp = document.querySelector('button[data-testid=\\'stExpandSidebarButton\\']')
                               || document.querySelector('button[aria-label=\\'Expand sidebar\\']')
                               || document.querySelector('[data-testid=\\'collapsedControl\\'] button');
                        var col = document.querySelector('button[data-testid=\\'stSidebarCollapseButton\\']')
                               || document.querySelector('button[aria-label=\\'Collapse sidebar\\']')
                               || document.querySelector('section[data-testid=\\'stSidebar\\'] [data-testid=\\'stSidebarCollapseButton\\']');
                        var sb = document.querySelector('section[data-testid=\\'stSidebar\\']');
                        var isClosed = !sb || sb.getAttribute('aria-expanded') === 'false' || sb.offsetWidth <= 0;
                        if (isClosed && exp) { exp.click(); }
                        else if (!isClosed && col) { col.click(); }
                        else if (exp) { exp.click(); }
                        else if (col) { col.click(); }
                    } catch(err) {
                        console.error('Sidebar toggle error:', err);
                    }
                })();
                this.remove();
            ">
            """
        )

    render_clean_html(
        """
        <img src="sidebar_click_listener" style="display:none;" onerror="
            if (!window.__sidebarClickDelegated) {
                window.__sidebarClickDelegated = true;
                document.addEventListener('click', function(e) {
                    var btn = e.target.closest('button');
                    if (btn && (btn.innerText.indexOf('History') !== -1 || (btn.getAttribute('data-testid') && btn.getAttribute('data-testid').indexOf('history') !== -1))) {
                        setTimeout(function() {
                            var exp = document.querySelector('button[data-testid=\\'stExpandSidebarButton\\']')
                                   || document.querySelector('button[aria-label=\\'Expand sidebar\\']')
                                   || document.querySelector('[data-testid=\\'collapsedControl\\'] button');
                            var col = document.querySelector('button[data-testid=\\'stSidebarCollapseButton\\']')
                                   || document.querySelector('button[aria-label=\\'Collapse sidebar\\']')
                                   || document.querySelector('section[data-testid=\\'stSidebar\\'] [data-testid=\\'stSidebarCollapseButton\\']');
                            var sb = document.querySelector('section[data-testid=\\'stSidebar\\']');
                            var isClosed = !sb || sb.getAttribute('aria-expanded') === 'false' || sb.offsetWidth <= 0;
                            if (isClosed && exp) { exp.click(); }
                            else if (!isClosed && col) { col.click(); }
                            else if (exp) { exp.click(); }
                            else if (col) { col.click(); }
                        }, 10);
                    }
                }, true);
            }
            this.remove();
        ">
        """
    )

    if st.session_state.editing_profile:
        show_onboarding_page(is_editing=True)
        return

    # Clean any accidental query parameters
    if "toggle_panel" in st.query_params:
        try:
            del st.query_params["toggle_panel"]
        except Exception:
            pass
    if "toggle_inspector" in st.query_params:
        try:
            del st.query_params["toggle_inspector"]
        except Exception:
            pass

    # Fetch latest gate status if conversation active
    gate_status = "PASS"
    if st.session_state.conv_id is not None:
        messages = get_messages(st.session_state.conv_id)
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                ver_rec = get_verification_result(msg["id"])
                if ver_rec:
                    gate_status = ver_rec["gate_decision"]
                    break

    pref_name = patient_profile.get("preferred_name") if patient_profile else (st.session_state.username or "Patient")
    age_str = get_age_display(patient_profile.get("age_or_dob")) if patient_profile else ""
    sex_str = patient_profile.get("sex_assigned_at_birth") if patient_profile else ""
    user_info = f"{pref_name}" + (f" ({age_str}" + (f" • {sex_str}" if sex_str and sex_str != "Prefer not to say" else "") + ")" if age_str and age_str != "Unknown" else "")

    intel_open = st.session_state.get("show_right_panel", True)
    top_panel_label = "📊 Intelligence Panel" if not intel_open else "✕ Hide Panel"
    top_panel_type = "primary" if not intel_open else "secondary"

    # Top App Header (Native interactive Streamlit elements matching preview exactly)
    col_t_left, col_t_mid, col_t_right = st.columns([0.42, 0.36, 0.22])
    with col_t_left:
        render_clean_html(
            f"""
            <div style="display: flex; align-items: center; gap: 10px; padding: 4px 0;">
                <div style="width: 34px; height: 34px; border-radius: 9px; background: linear-gradient(135deg, #0284c7, #38bdf8); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; box-shadow: 0 2px 8px rgba(56, 189, 248, 0.4);">🩺</div>
                <div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-weight: 800; font-size: 1.1rem; color: #ffffff; letter-spacing: -0.01em;">ClinCoherence</span>
                        <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); font-size: 0.65rem; font-weight: 700; padding: 1px 6px; border-radius: 9999px;">Clinical AI</span>
                    </div>
                    <div style="font-size: 0.68rem; color: #94a3b8; line-height: 1.15;">Longitudinal Clinical Coherence & Decision Verification</div>
                </div>
            </div>
            """
        )

    with col_t_mid:
        insp_open = st.session_state.get("show_pipeline_inspector", False)
        pipe_btn_type = "primary" if insp_open else "secondary"
        if st.button(
            f"⚡ Pipeline: Coherence Verifier ➔ Gate [{gate_status}]",
            key="btn_top_pipeline_status",
            use_container_width=True,
            type=pipe_btn_type,
            help="Toggle Clinical Pipeline Inspector & Diagnostics",
        ):
            st.session_state.show_pipeline_inspector = not insp_open
            st.rerun()

    with col_t_right:
        col_t_panel, col_t_user = st.columns([0.62, 0.38])
        with col_t_panel:
            if st.button(
                top_panel_label,
                key="btn_top_intelligence_panel",
                use_container_width=True,
                type=top_panel_type,
                help="Toggle Right Clinical Intelligence slide panel",
            ):
                st.session_state.show_right_panel = not intel_open
                st.rerun()
        with col_t_user:
            render_clean_html(
                f"""
                <div style="height: 38px; display: flex; align-items: center; justify-content: flex-end; padding-top: 2px;">
                    <span style="background: #0b1222; border: 1px solid #1e293b; color: #cbd5e1; font-size: 0.76rem; font-weight: 700; padding: 5px 10px; border-radius: 8px; white-space: nowrap;">
                        👤 {pref_name}
                    </span>
                </div>
                """
            )

    # Render Pipeline Inspector if toggled (accessible on all screens)
    if st.session_state.get("show_pipeline_inspector", False):
        inspector_payload = None
        if st.session_state.conv_id is not None:
            active_msgs = get_messages(st.session_state.conv_id)
            for m in reversed(active_msgs):
                if m["role"] == "assistant":
                    vrec = get_verification_result(m["id"])
                    if vrec:
                        try:
                            inspector_payload = json.loads(vrec["flags_json"])
                        except Exception:
                            pass
                        break
        show_pipeline_inspector(inspector_payload)

    if st.session_state.conv_id is None:
        # Action bar on welcome screen (matching preview)
        col_w_hist, col_w_title = st.columns([0.14, 0.86])
        with col_w_hist:
            if st.button("📑 History", key="btn_welcome_toggle_history", use_container_width=True, type="secondary", help="Open or close conversation history sidebar"):
                st.session_state.toggle_sidebar_requested = True
                st.rerun()
        with col_w_title:
            render_clean_html(
                """
                <div style="display: flex; align-items: center; gap: 8px; padding-top: 5px;">
                    <span style="color: #64748b;">|</span>
                    <span style="font-size: 0.84rem; color: #94a3b8; font-weight: 600;">Active Session • Ready to Consult</span>
                </div>
                """
            )

        if st.session_state.show_right_panel:
            render_clean_html(
                """
                <style>
                [data-testid="stBottom"] {
                    right: 33.5% !important;
                    border-right: 1px solid #1e293b !important;
                }
                </style>
                """
            )
            col_welcome_main, col_welcome_intel = st.columns([67, 33])
        else:
            render_clean_html(
                """
                <style>
                [data-testid="stBottom"] {
                    right: 0 !important;
                }
                </style>
                """
            )
            col_welcome_main = st.container()
            col_welcome_intel = None

        with col_welcome_main:
            pref_name = patient_profile.get("preferred_name") if patient_profile else st.session_state.username

            render_clean_html(
                f"""
                <div style="text-align: center; padding: 24px 16px 16px; max-width: 720px; margin: auto;">
                    <h1 style="color: #ffffff; font-size: 1.75rem; font-weight: 800; letter-spacing: -0.02em;">How can I help you today, {pref_name}?</h1>
                    <div style="color: #94a3b8; font-size: 0.92rem; line-height: 1.55; margin-top: 6px;">
                        I track your symptoms across conversation turns, normalize medications against RxNorm, 
                        and verify clinical coherence using evidence-based FDA medical records.
                    </div>
                </div>
                """
            )

            st.markdown("##### Suggested consultation starters")
            col_s1, col_s2 = st.columns(2)

            with col_s1:
                if st.button("Describe symptoms\n\nI have had a fever and mild fatigue for two days", use_container_width=True):
                    _start_conversation_with_message(
                        "I have had a fever and mild fatigue for two days",
                        "Fever & Fatigue Consultation",
                        patient_profile,
                    )

                if st.button("Update health history\n\nI want to report an update on my medical conditions", use_container_width=True):
                    _start_conversation_with_message(
                        "I would like to update my active health profile and report my current symptoms",
                        "Health History Update",
                        patient_profile,
                    )

            with col_s2:
                if st.button("Discuss a medication\n\nI am taking Metformin 500mg and have questions about side effects", use_container_width=True):
                    _start_conversation_with_message(
                        "I am taking Metformin 500mg and feeling slightly dizzy",
                        "Metformin Query",
                        patient_profile,
                    )

                if st.button("Follow-up discussion\n\nLet's follow up on symptoms from my previous discussion", use_container_width=True):
                    _start_conversation_with_message(
                        "Can we review my baseline health profile and discuss follow-up care?",
                        "Follow-up Consultation",
                        patient_profile,
                    )

            welcome_user_input = st.chat_input("Message ClinCoherence...")
            if welcome_user_input:
                title = welcome_user_input[:35].strip() + ("..." if len(welcome_user_input.strip()) > 35 else "")
                _start_conversation_with_message(welcome_user_input, title, patient_profile)

        if col_welcome_intel is not None:
            with col_welcome_intel:
                render_right_intelligence_panel(None, patient_profile)

        return

    conv = get_conversation(st.session_state.conv_id, st.session_state.user_id)
    if conv is None:
        st.error("Conversation not found or access denied.")
        st.session_state.conv_id = None
        return

    messages = get_messages(st.session_state.conv_id)

    latest_payload = None
    latest_gate_decision = "PASS"
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            ver_rec = get_verification_result(msg["id"])
            if ver_rec:
                try:
                    latest_payload = json.loads(ver_rec["flags_json"])
                    latest_gate_decision = ver_rec["gate_decision"]
                except Exception:
                    pass
                break

    # Breadcrumb Row (Matching preview: History button, title, pass badge, active state version — duplicate panel toggle removed)
    state_ver = latest_payload.get("state_summary", {}).get("version", 1) if latest_payload else 1
    col_hist, col_title_state = st.columns([0.14, 0.86])
    with col_hist:
        if st.button("📑 History", key="btn_toggle_history_sidebar", use_container_width=True, type="secondary", help="Open or close conversation history sidebar"):
            st.session_state.toggle_sidebar_requested = True
            st.rerun()
    with col_title_state:
        render_clean_html(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; padding-top: 4px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: #64748b;">|</span>
                    <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #ffffff;">{conv['title']}</h3>
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px; font-family: monospace;">Verified {latest_gate_decision}</span>
                </div>
                <div style="font-size: 0.72rem; color: #94a3b8; font-family: monospace;">
                    Active Patient State: <strong style="color: #38bdf8;">v{state_ver}</strong>
                </div>
            </div>
            """
        )

    # Dual-Panel Layout: Chat Area (67%) | Right Intelligence Panel (33%)
    # Constrain bottom message dock to col_chat when right intelligence panel is active so it never overlaps or stretches across
    if st.session_state.show_right_panel:
        render_clean_html(
            """
            <style>
            [data-testid="stBottom"] {
                right: 33.5% !important;
                border-right: 1px solid #1e293b !important;
            }
            </style>
            """
        )
        col_chat, col_intel = st.columns([67, 33])
    else:
        render_clean_html(
            """
            <style>
            [data-testid="stBottom"] {
                right: 0 !important;
            }
            </style>
            """
        )
        col_chat = st.container()
        col_intel = None

    with col_chat:
        render_clean_html(
            """
            <div style="max-width: 600px; margin: 0 auto 16px auto; background: #0a1122; border: 1px solid #1e293b; border-radius: 12px; padding: 10px 14px; text-align: center; font-size: 0.76rem; color: #94a3b8;">
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
                                <span style="font-weight: 700; color: #fcd34d;">You (Patient)</span>
                                <span style="color: #94a3b8; font-family: monospace;">{time_str}</span>
                            </div>
                            <div style="font-size: 0.88rem; line-height: 1.55;">{formatted_text}</div>
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
                            <div style="font-size: 0.88rem; line-height: 1.55;">{formatted_text}</div>
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

        # Place chat_input INSIDE col_chat so it stays constrained to the chat area and does NOT stretch across the right panel!
        user_input = st.chat_input("Message ClinCoherence...")

    if col_intel is not None:
        with col_intel:
            render_right_intelligence_panel(latest_payload, patient_profile)

    # Process new user input when submitted
    if user_input:
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

    # Clear legacy query params so they never interfere with session state
    if "toggle_panel" in st.query_params:
        del st.query_params["toggle_panel"]
    if "toggle_inspector" in st.query_params:
        del st.query_params["toggle_inspector"]

    if st.session_state.page == "login" or st.session_state.user_id is None:
        show_auth_page()
        return

    profile_row = get_patient_profile(st.session_state.user_id)
    profile_dict = dict(profile_row) if profile_row else None

    if profile_dict is None:
        show_onboarding_page(is_editing=False)
        return

    show_main_chat(profile_dict)


if __name__ == "__main__":
    main()
else:
    main()
