"""ClinCoherence — Deep Dark Blue & Soft Warm Amber / Steel Sky Blue UI styling."""

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
    --primary: #d97706;
    --primary-hover: #b45309;
    --sky: #38bdf8;
    --sky-dark: #0284c7;
    --dock-bg: #14233c;
    --dock-input-bg: #0b1628;
}

/* HIDE STREAMLIT DEFAULT DEPLOY HEADER & TOOLBAR COMPLETELY */
header[data-testid="stHeader"],
[data-testid="stHeader"],
.stAppHeader,
[data-testid="stDecoration"],
[data-testid="stToolbar"],
#MainMenu,
footer {
    display: none !important;
    height: 0 !important;
    visibility: hidden !important;
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

.main .block-container {
    max-width: 100% !important;
    padding-top: 0.35rem !important;
    padding-bottom: 2rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
}

/* TOP APP NAVIGATION BAR (MATCHING PREVIEW EXACTLY) */
.top-nav-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #0b1222;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 10px 18px;
    margin-bottom: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.top-nav-left {
    display: flex;
    align-items: center;
    gap: 12px;
}

.top-nav-logo {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #0284c7, #38bdf8);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
}

.top-nav-title {
    color: #ffffff !important;
    font-weight: 800;
    font-size: 1.1rem;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 8px;
}

.top-nav-pill {
    font-size: 0.68rem;
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 9999px;
}

.top-nav-subtitle {
    color: var(--muted) !important;
    font-size: 0.74rem;
}

/* PIPELINE BREATHING GLOW BADGE & SPINNER */
@keyframes breathe-glow {
    0%, 100% {
        opacity: 0.6;
        box-shadow: 0 0 6px rgba(56, 189, 248, 0.25);
        border-color: rgba(56, 189, 248, 0.4);
    }
    50% {
        opacity: 1;
        box-shadow: 0 0 16px rgba(56, 189, 248, 0.75), 0 0 8px rgba(14, 165, 233, 0.5);
        border-color: rgba(56, 189, 248, 0.95);
    }
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.pipeline-breathing {
    animation: breathe-glow 2.2s ease-in-out infinite;
}

.pipeline-status-badge {
    background: #080f1d;
    border: 1px solid rgba(56, 189, 248, 0.45);
    border-radius: 9999px;
    padding: 5px 16px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
}

.pipeline-spinner {
    animation: spin 2s linear infinite;
    width: 14px;
    height: 14px;
    display: inline-block;
    flex-shrink: 0;
}

.pipeline-dots {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-left: 4px;
    padding-left: 8px;
    border-left: 1px solid #334155;
}

.p-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
}

.dot-extractor { background: #10b981; }
.dot-evidence { background: #10b981; }
.dot-verifier { background: #38bdf8; box-shadow: 0 0 6px #38bdf8; }
.dot-gate { background: #d97706; }

/* USER CHIP IN HEADER */
.top-user-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #080d1a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 0.78rem;
    color: #cbd5e1;
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

/* BUTTONS — VELVET AMBER PRIMARY (NO EYE STRAIN) & STEEL SKY SECONDARY */
.stApp .stButton > button[data-testid="baseButton-primary"],
button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #b45309, #d97706) !important;
    background-color: #d97706 !important;
    color: #ffffff !important;
    border: 1px solid rgba(245, 158, 11, 0.4) !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    box-shadow: 0 2px 10px rgba(180, 83, 9, 0.3) !important;
    transition: all 0.15s ease-in-out !important;
}

.stApp .stButton > button[data-testid="baseButton-primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #d97706, #f59e0b) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px rgba(245, 158, 11, 0.4) !important;
}

.stApp .stButton > button,
.stApp .stButton > button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-secondary"] {
    color: #cbd5e1 !important;
    background: #14233c !important;
    background-color: #14233c !important;
    border: 1px solid #283854 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    box-shadow: none !important;
    transition: all 0.15s ease-in-out !important;
}

.stApp .stButton > button:hover,
.stApp .stButton > button[data-testid="baseButton-secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover {
    background: #1c3052 !important;
    border-color: #38bdf8 !important;
    color: #38bdf8 !important;
    box-shadow: 0 2px 10px rgba(56, 189, 248, 0.2) !important;
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
[data-baseweb="select"]:focus-within > div {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 1px #38bdf8 !important;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: #091122;
    padding: 4px;
    border-radius: 10px;
    border: 1px solid var(--border);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 16px;
    color: var(--muted) !important;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    background-color: #14233c !important;
    color: #38bdf8 !important;
}

/* CHAT BUBBLES */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 6px 0 !important;
}

.chat-row-user {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;
}

.chat-bubble-user {
    background: #1b2842;
    border: 1px solid rgba(217, 119, 6, 0.45);
    border-radius: 16px 16px 4px 16px;
    padding: 12px 18px;
    color: #f1f5f9;
    max-width: 100%;
    word-break: break-word;
    font-size: 0.94rem;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
}

.chat-avatar-user {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: #d97706;
    color: #ffffff !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(217, 119, 6, 0.35);
}

.chat-row-assistant {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;
}

.chat-bubble-assistant {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px 16px 16px 4px;
    padding: 14px 18px;
    color: #e2e8f0;
    max-width: 100%;
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

/* CHAT INPUT STYLING — REFINED STEEL SKY-BLUE DOCK (#14233c) */
/* Eliminate full-width glowing cyan border across the screen */
[data-testid="stBottom"],
[data-testid="stBottom"] > div {
    background: transparent !important;
    background-color: transparent !important;
    border-top: none !important;
    box-shadow: none !important;
}

/* Restrict chat input width so it does not blow out edge-to-edge */
[data-testid="stChatInput"] {
    max-width: 820px !important;
    margin: 8px auto 14px auto !important;
    background: #14233c !important;
    background-color: #14233c !important;
    border: 1.5px solid rgba(56, 189, 248, 0.6) !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 14px rgba(56, 189, 248, 0.2) !important;
    transition: all 0.2s ease-in-out !important;
}

[data-testid="stChatInput"] textarea {
    color: #f8fafc !important;
    background: #0b1628 !important;
    background-color: #0b1628 !important;
    border-radius: 10px !important;
    font-size: 0.92rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.45) !important;
}

[data-testid="stChatInput"] button {
    color: #38bdf8 !important;
}

/* RIGHT INTELLIGENCE PANEL CONTAINER & CARDS */
.intel-panel-card {
    background: #0b1222;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 14px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.intel-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 8px;
}

.intel-panel-title {
    color: #38bdf8 !important;
    font-size: 0.88rem;
    font-weight: 700;
}

.doc-folder-item {
    background: #070b14;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 10px;
}

.doc-badge-dailymed {
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    font-size: 0.68rem;
    font-family: monospace;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 4px;
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
</style>
"""
