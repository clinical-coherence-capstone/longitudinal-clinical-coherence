"""ClinCoherence — consistent light theme and UI styling."""

APP_CSS = """
<style>
:root {
    color-scheme: light;
    --bg: #f8fafc;
    --surface: #ffffff;
    --soft: #f1f5f9;
    --text: #172033;
    --muted: #64748b;
    --border: #dbe3ed;
    --primary: #2563eb;
}

/* GLOBAL */
html, body, [class*="css"] {
    font-family: Inter, -apple-system, BlinkMacSystemFont,
    "Segoe UI", Arial, sans-serif;
    color: var(--text) !important;
}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: var(--bg) !important;
    color: var(--text) !important;
}

[data-testid="stHeader"] {
    background: rgba(248,250,252,0.96) !important;
}

.main .block-container {
    max-width: 1120px;
    padding-top: 2rem;
    padding-bottom: 6rem;
}

/* TEXT */
.stMarkdown,
.stMarkdown p,
.stMarkdown li,
[data-testid="stMarkdownContainer"] {
    color: var(--text);
}

.stCaption,
small,
[data-testid="stCaptionContainer"] {
    color: var(--muted) !important;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] * {
    color: var(--text);
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

.brand-container {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 16px;
    margin-bottom: 16px;
    border-bottom: 1px solid #eef2f7;
}

.brand-logo,
.auth-logo-badge,
.welcome-logo-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white !important;
    background: linear-gradient(135deg, #2563eb, #0f766e);
}

.brand-logo {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    font-weight: 700;
}

.brand-text-title {
    color: #172033 !important;
    font-size: 1.12rem;
    font-weight: 700;
}

.brand-text-sub {
    color: #64748b !important;
    font-size: 0.78rem;
}

.conv-item {
    padding: 10px 12px;
    border-radius: 9px;
    color: #334155 !important;
    margin-bottom: 5px;
}

.conv-item:hover {
    background: #f1f5f9;
}

.conv-item.active {
    background: #eff6ff;
    color: #1d4ed8 !important;
    font-weight: 600;
    border: 1px solid #bfdbfe;
}

.sidebar-profile-card {
    background: #f8fafc;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px;
    margin: 16px 0;
}

.sidebar-profile-name {
    color: #172033 !important;
    font-weight: 700;
}

.sidebar-profile-meta {
    color: #64748b !important;
    font-size: 0.78rem;
}

/* INPUT FIELDS */
.stApp input,
.stApp textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] > div {
    color: #172033 !important;
    background-color: #ffffff !important;
    caret-color: #172033 !important;
}

.stApp input::placeholder,
.stApp textarea::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}

[data-baseweb="input"],
[data-baseweb="textarea"],
[data-baseweb="select"] > div {
    border-color: #cbd5e1 !important;
    border-radius: 9px !important;
}

[data-baseweb="input"]:focus-within,
[data-baseweb="textarea"]:focus-within,
[data-baseweb="select"]:focus-within {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 1px #2563eb !important;
}

[data-baseweb="select"] span,
[data-baseweb="select"] div {
    color: #172033 !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[role="option"] {
    background: white !important;
    color: #172033 !important;
}

[data-baseweb="popover"] *,
[data-baseweb="menu"] *,
[role="listbox"] *,
[role="option"] * {
    color: #172033 !important;
    background-color: white !important;
}

/* DATE PICKER */
[data-testid="stDateInput"] input {
    color: #172033 !important;
    background: white !important;
}

[data-baseweb="calendar"],
[data-baseweb="calendar"] * {
    color: #172033 !important;
    background-color: white !important;
}

/* LABELS */
.stApp label,
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] p {
    color: #334155 !important;
    font-weight: 600 !important;
}

.stApp [data-testid="stHelp"] {
    color: #64748b !important;
}

/* BUTTONS */
.stApp .stButton > button,
[data-testid="baseButton-secondary"] {
    color: #1e293b !important;
    background: white !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
    font-weight: 600;
}

.stApp .stButton > button:hover {
    color: #1d4ed8 !important;
    border-color: #93c5fd !important;
    background: #eff6ff !important;
}

.stApp .stButton > button[kind="primary"],
[data-testid="baseButton-primary"] {
    color: white !important;
    background: #2563eb !important;
    border-color: #2563eb !important;
}

.stApp .stButton > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
}

/* LOGIN AND REGISTRATION */
.auth-wrapper {
    max-width: 460px;
    margin: 2rem auto;
    padding: 2rem;
    background: white;
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: 0 8px 28px rgba(15,23,42,0.06);
}

.auth-header {
    text-align: center;
    margin-bottom: 24px;
}

.auth-logo-badge {
    width: 48px;
    height: 48px;
    border-radius: 13px;
    font-size: 1.35rem;
    margin-bottom: 12px;
}

.auth-title {
    color: #172033 !important;
    font-size: 1.45rem;
    font-weight: 700;
}

.auth-subtitle {
    color: #64748b !important;
    font-size: 0.9rem;
}

/* ONBOARDING */
.wizard-progress-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 12px 0 28px;
}

.wizard-step {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #334155 !important;
    font-weight: 600;
}

.wizard-step-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
}

.wizard-step-active .wizard-step-circle {
    background: #2563eb;
    color: white !important;
}

.wizard-step-inactive .wizard-step-circle {
    background: #f1f5f9;
    color: #64748b !important;
    border: 1px solid #cbd5e1;
}

.wizard-step-completed .wizard-step-circle {
    background: #0f766e;
    color: white !important;
}

.wizard-divider {
    flex: 1;
    height: 2px;
    background: #e2e8f0;
    margin: 0 16px;
}

.wizard-divider.completed {
    background: #0f766e;
}

[data-testid="stForm"],
.profile-form-card,
.onboarding-card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px;
}

/* WELCOME SCREEN */
.welcome-container {
    text-align: center;
    padding: 40px 16px 24px;
    max-width: 700px;
    margin: auto;
}

.welcome-logo-badge {
    width: 52px;
    height: 52px;
    border-radius: 15px;
    font-size: 1.5rem;
    margin-bottom: 16px;
}

.welcome-title {
    color: #172033 !important;
    font-size: 1.8rem;
    font-weight: 700;
}

.welcome-desc {
    color: #64748b !important;
    font-size: 0.98rem;
    line-height: 1.55;
}

.starter-card-btn {
    text-align: left;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.03);
}

.starter-card-btn:hover {
    border-color: #93c5fd;
    background: #f8fbff;
}

.starter-card-title {
    color: #172033 !important;
    font-weight: 650;
}

.starter-card-sub {
    color: #64748b !important;
    font-size: 0.8rem;
}

/* CHAT MESSAGES */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 8px 0 !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    color: #172033 !important;
}

.chat-row-user {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 20px;
    width: 100%;
}

.chat-avatar-user {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: #2563eb;
    color: white !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(37,99,235,0.25);
}

.chat-bubble-user {
    background: #eaf2ff;
    color: #1e3a8a !important;
    border: 1px solid #bfdbfe;
    border-radius: 18px 18px 4px 18px;
    padding: 14px 18px;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 0.95rem;
    box-shadow: 0 1px 3px rgba(37,99,235,0.06);
}

.chat-row-assistant {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
    width: 100%;
}

.chat-bubble-assistant {
    background: #ffffff;
    color: #0f172a !important;
    border: 1px solid #e2e8f0;
    border-radius: 18px 18px 18px 4px;
    padding: 16px 20px;
    line-height: 1.65;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 0.95rem;
    box-shadow: 0 2px 8px rgba(15,23,42,0.04);
}

.chat-avatar-assistant {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #2563eb, #0f766e);
    color: white !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(15,118,110,0.25);
}

.chat-timestamp-subtle {
    color: #94a3b8 !important;
    font-size: 0.72rem;
    margin-top: 6px;
}

/* CHAT INPUT CONTAINER FIXED AT BOTTOM */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
.stChatFloatingInputContainer,
[data-testid="stChatFloatingInputContainer"],
footer {
    background: #f8fafc !important;
    background-color: #f8fafc !important;
    border-top: 1px solid var(--border) !important;
}

[data-testid="stChatInput"] {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 16px rgba(15,23,42,0.06) !important;
}

[data-testid="stChatInput"] textarea {
    color: #0f172a !important;
    background: #ffffff !important;
    background-color: #ffffff !important;
    font-size: 0.95rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #64748b !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
}

[data-testid="stChatInput"] button {
    color: #2563eb !important;
}

/* PATIENT CONTEXT */
.context-banner {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 20px;
}

.context-chip {
    display: inline-flex;
    align-items: center;
    padding: 4px 9px;
    border-radius: 7px;
    font-size: 0.78rem;
    margin: 4px;
}

.chip-condition {
    background: #fff7df;
    color: #854d0e !important;
    border: 1px solid #fde68a;
}

.chip-med {
    background: #eaf2ff;
    color: #1e40af !important;
    border: 1px solid #bfdbfe;
}

.chip-allergy {
    background: #fff1f2;
    color: #9f1239 !important;
    border: 1px solid #fecdd3;
}

.chip-demographic {
    background: #f1f5f9;
    color: #334155 !important;
    border: 1px solid #cbd5e1;
}

/* VERIFICATION */
.gate-badge {
    display: inline-flex;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 8px;
}

.gate-pass {
    background: #ecfdf5;
    color: #065f46 !important;
    border: 1px solid #a7f3d0;
}

.gate-warn {
    background: #fffbeb;
    color: #92400e !important;
    border: 1px solid #fde68a;
}

.gate-clarify {
    background: #eff6ff;
    color: #1e40af !important;
    border: 1px solid #bfdbfe;
}

.gate-refuse {
    background: #fef2f2;
    color: #991b1b !important;
    border: 1px solid #fecaca;
}

.verif-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 13px 16px;
    margin-bottom: 12px;
}

.verif-card-title {
    color: #475569 !important;
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 7px;
}

/* MEDICATION ITEMS */
.med-item-pill {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: white;
    color: #172033 !important;
    border: 1px solid #e2e8f0;
    border-radius: 9px;
    padding: 8px 12px;
    margin-bottom: 6px;
}

/* EXPANDERS */
.stApp [data-testid="stExpander"] {
    background: white !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 11px !important;
}

.stApp [data-testid="stExpander"] summary,
.stApp [data-testid="stExpander"] summary span {
    color: #172033 !important;
}

/* KEYBOARD ACCESSIBILITY */
*:focus-visible {
    outline: 2px solid #2563eb !important;
    outline-offset: 2px !important;
}

/* MOBILE */
@media(max-width:768px) {
    .main .block-container {
        padding: 16px 12px 80px;
    }

    .auth-wrapper {
        margin: 16px auto;
        padding: 20px;
    }

    .chat-bubble-user,
    .chat-bubble-assistant {
        max-width: 94%;
    }

    .welcome-container {
        padding: 24px 8px 16px;
    }
}
</style>
"""