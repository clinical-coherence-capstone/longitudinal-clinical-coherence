"""ClinCoherence — Deep Dark Blue & Warm Amber / Sky Blue UI styling."""

APP_CSS = """
<style>
:root {
    color-scheme: dark;
    --bg: #070b14;
    --surface: #0b1222;
    --card: #0f172a;
    --card-hover: #14233c;
    --text: #f1f5f9;
    --muted: #94a3b8;
    --border: #1e293b;
    --border-light: #283854;
    --primary: #f59e0b;
    --primary-hover: #d97706;
    --primary-text: #090d16;
    --sky: #38bdf8;
    --sky-dark: #0284c7;
    --dock-bg: #14233c;
    --dock-input-bg: #0b1628;
}

/* GLOBAL RESET & FONTS */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: var(--text) !important;
}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: var(--bg) !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

[data-testid="stHeader"] {
    background: rgba(11, 18, 34, 0.92) !important;
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--border);
}

.main .block-container {
    max-width: 1360px;
    padding-top: 1.25rem;
    padding-bottom: 6.5rem;
}

/* TEXT & TYPOGRAPHY */
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
    background: #0a101f !important;
    background-color: #0a101f !important;
    border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] * {
    color: var(--text);
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1.25rem;
    padding-bottom: 2rem;
}

.brand-container {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 14px;
    margin-bottom: 14px;
    border-bottom: 1px solid var(--border);
}

.brand-logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    font-weight: 700;
    color: #ffffff !important;
    background: linear-gradient(135deg, #0284c7, #38bdf8);
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
}

.brand-text-title {
    color: #ffffff !important;
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.brand-text-sub {
    color: var(--muted) !important;
    font-size: 0.76rem;
}

.sidebar-profile-card {
    background: #0b1222;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    margin: 14px 0 10px;
}

.sidebar-profile-name {
    color: #ffffff !important;
    font-weight: 700;
    font-size: 0.88rem;
}

.sidebar-profile-meta {
    color: var(--muted) !important;
    font-size: 0.75rem;
    margin-top: 2px;
}

/* BUTTONS — WARM AMBER WITH POLISHED IMMERSED LABELS (NO COLOR CLASH) */
.stApp .stButton > button {
    color: #0f172a !important;
    background: #f59e0b !important;
    background-color: #f59e0b !important;
    border: 1px solid #d97706 !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.25) !important;
    transition: all 0.15s ease-in-out !important;
}

.stApp .stButton > button:hover {
    background: #d97706 !important;
    background-color: #d97706 !important;
    border-color: #b45309 !important;
    color: #000000 !important;
    box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35) !important;
    transform: translateY(-1px);
}

.stApp .stButton > button[kind="secondary"],
[data-testid="baseButton-secondary"] {
    color: #f1f5f9 !important;
    background: #14233c !important;
    background-color: #14233c !important;
    border: 1px solid #283854 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}

.stApp .stButton > button[kind="secondary"]:hover,
[data-testid="baseButton-secondary"]:hover {
    background: #1c3052 !important;
    border-color: #38bdf8 !important;
    color: #38bdf8 !important;
}

/* INPUT FIELDS */
.stApp input,
.stApp textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] > div {
    color: #f1f5f9 !important;
    background-color: #091122 !important;
    caret-color: #38bdf8 !important;
    border-radius: 10px !important;
}

.stApp input::placeholder,
.stApp textarea::placeholder {
    color: #64748b !important;
    opacity: 1 !important;
}

[data-baseweb="input"],
[data-baseweb="textarea"],
[data-baseweb="select"] > div {
    border-color: #1e293b !important;
    background-color: #091122 !important;
    border-radius: 10px !important;
}

[data-baseweb="input"]:focus-within,
[data-baseweb="textarea"]:focus-within,
[data-baseweb="select"]:focus-within {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 1px #38bdf8 !important;
}

[data-baseweb="select"] span,
[data-baseweb="select"] div {
    color: #f1f5f9 !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[role="option"] {
    background: #0f172a !important;
    background-color: #0f172a !important;
    color: #f1f5f9 !important;
    border: 1px solid #1e293b !important;
}

[data-baseweb="popover"] *,
[data-baseweb="menu"] *,
[role="listbox"] *,
[role="option"] * {
    color: #f1f5f9 !important;
    background-color: #0f172a !important;
}

[role="option"]:hover {
    background-color: #1e293b !important;
}

/* LABELS */
.stApp label,
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] p {
    color: #cbd5e1 !important;
    font-weight: 600 !important;
}

/* AUTHENTICATION VIEW */
.auth-wrapper {
    max-width: 480px;
    margin: 2.5rem auto;
    padding: 2.25rem;
    background: #0b1222;
    border: 1px solid #1e293b;
    border-radius: 20px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45), 0 0 20px rgba(56, 189, 248, 0.08);
}

.auth-header {
    text-align: center;
    margin-bottom: 24px;
}

.auth-logo-badge {
    width: 52px;
    height: 52px;
    border-radius: 14px;
    font-size: 1.45rem;
    margin: 0 auto 12px auto;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #0284c7, #38bdf8);
    box-shadow: 0 6px 20px rgba(56, 189, 248, 0.3);
}

.auth-title {
    color: #ffffff !important;
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.auth-subtitle {
    color: #94a3b8 !important;
    font-size: 0.88rem;
    margin-top: 4px;
}

/* WIZARD & PROFILE CARDS */
.profile-form-card,
.onboarding-card {
    background: #0b1222;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
}

.wizard-progress-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 12px 0 26px;
}

.wizard-step {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #cbd5e1 !important;
    font-weight: 600;
    font-size: 0.9rem;
}

.wizard-step-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
}

.wizard-step-active .wizard-step-circle {
    background: #f59e0b;
    color: #0f172a !important;
    box-shadow: 0 0 12px rgba(245, 158, 11, 0.4);
}

.wizard-step-inactive .wizard-step-circle {
    background: #091122;
    color: #64748b !important;
    border: 1px solid #1e293b;
}

.wizard-step-completed .wizard-step-circle {
    background: #10b981;
    color: white !important;
}

.wizard-divider {
    flex: 1;
    height: 2px;
    background: #1e293b;
    margin: 0 16px;
}

.wizard-divider.completed {
    background: #10b981;
}

/* CHAT BUBBLE LAYOUT */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 6px 0 !important;
    border: none !important;
}

.chat-row-user {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 18px;
    width: 100%;
}

.chat-bubble-user {
    background: #1b253b;
    color: #f8fafc !important;
    border: 1px solid rgba(245, 158, 11, 0.45);
    border-radius: 18px 18px 4px 18px;
    padding: 14px 18px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 0.94rem;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
}

.chat-avatar-user {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: #f59e0b;
    color: #0f172a !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.05rem;
    font-weight: 700;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
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
    background: #0f172a;
    color: #f1f5f9 !important;
    border: 1px solid #1e293b;
    border-radius: 18px 18px 18px 4px;
    padding: 16px 20px;
    line-height: 1.65;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 0.94rem;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
}

.chat-avatar-assistant {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: #121e36;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(56, 189, 248, 0.2);
}

.chat-timestamp-subtle {
    color: #64748b !important;
    font-size: 0.72rem;
    margin-top: 5px;
}

/* REFINED STEEL SKY-BLUE MESSAGE DOCK (USER APPROVED #14233c) */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
.stChatFloatingInputContainer,
[data-testid="stChatFloatingInputContainer"],
footer {
    background: #14233c !important;
    background-color: #14233c !important;
    border-top: 2px solid #38bdf8 !important;
    box-shadow: 0 -6px 25px rgba(56, 189, 248, 0.22) !important;
}

[data-testid="stChatInput"] {
    background: #0b1628 !important;
    background-color: #0b1628 !important;
    border: 1.5px solid rgba(56, 189, 248, 0.5) !important;
    border-radius: 14px !important;
    box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.4) !important;
}

[data-testid="stChatInput"] textarea {
    color: #f8fafc !important;
    background: #0b1628 !important;
    background-color: #0b1628 !important;
    font-size: 0.95rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 16px rgba(56, 189, 248, 0.4) !important;
}

[data-testid="stChatInput"] button {
    color: #38bdf8 !important;
}

/* BREATHING GLOW ANIMATION FOR LIVE PIPELINE STATUS */
@keyframes breathe-glow {
    0%, 100% {
        opacity: 0.55;
        box-shadow: 0 0 6px rgba(56, 189, 248, 0.25);
        border-color: rgba(56, 189, 248, 0.4);
    }
    50% {
        opacity: 1;
        box-shadow: 0 0 16px rgba(56, 189, 248, 0.75), 0 0 8px rgba(14, 165, 233, 0.5);
        border-color: rgba(56, 189, 248, 0.95);
    }
}

.pipeline-status-badge {
    animation: breathe-glow 2.2s ease-in-out infinite;
    background: #080f1d;
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 9999px;
    padding: 4px 14px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

/* CARDS & EXPANDERS */
.stApp [data-testid="stExpander"] {
    background: #0b1222 !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
}

.stApp [data-testid="stExpander"] summary,
.stApp [data-testid="stExpander"] summary span {
    color: #f1f5f9 !important;
    font-weight: 600 !important;
}

.intel-panel-card {
    background: #0b1222;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 14px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.intel-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 8px;
}

.intel-panel-title {
    color: #38bdf8 !important;
    font-size: 0.88rem;
    font-weight: 700;
}

/* KEYBOARD ACCESSIBILITY */
*:focus-visible {
    outline: 2px solid #38bdf8 !important;
    outline-offset: 2px !important;
}
</style>
"""
