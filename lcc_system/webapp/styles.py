"""ClinCoherence — Deep Dark Blue & Velvet Warm Amber / Steel Sky Blue UI styling."""

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

/* HIDE STREAMLIT DEFAULT DEPLOY AND TOOLBAR ACTIONS, BUT KEEP SIDEBAR CONTROLS FULLY VISIBLE & INTERACTIVE */
header[data-testid="stHeader"] {
    background: transparent !important;
    background-color: transparent !important;
    height: 56px !important;
    z-index: 10000000 !important;
    pointer-events: none !important;
}

header[data-testid="stHeader"] button[data-testid="stExpandSidebarButton"],
header[data-testid="stHeader"] button[aria-label="Expand sidebar"],
header[data-testid="stHeader"] [data-testid="collapsedControl"],
header[data-testid="stHeader"] [data-testid="stToolbar"] {
    pointer-events: auto !important;
}

/* SIDEBAR EXPAND BUTTON (») WHEN SIDEBAR IS COLLAPSED — ALWAYS VISIBLE, INTERACTIVE & ELEVATED */
button[data-testid="stExpandSidebarButton"],
button[aria-label="Expand sidebar"],
[data-testid="collapsedControl"] {
    display: inline-flex !important;
    visibility: visible !important;
    pointer-events: auto !important;
    position: fixed !important;
    top: 10px !important;
    left: 12px !important;
    z-index: 10000001 !important;
    background: #14233c !important;
    background-color: #14233c !important;
    border: 1px solid rgba(56, 189, 248, 0.5) !important;
    border-radius: 8px !important;
    color: #38bdf8 !important;
    width: 36px !important;
    height: 36px !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5) !important;
    transition: all 0.2s ease-in-out !important;
    align-items: center !important;
    justify-content: center !important;
}

button[data-testid="stExpandSidebarButton"]:hover,
button[aria-label="Expand sidebar"]:hover,
[data-testid="collapsedControl"]:hover {
    background: #1d3254 !important;
    background-color: #1d3254 !important;
    border-color: #38bdf8 !important;
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.6) !important;
}

button[data-testid="stExpandSidebarButton"] svg,
button[aria-label="Expand sidebar"] svg,
[data-testid="collapsedControl"] svg {
    fill: #38bdf8 !important;
    stroke: #38bdf8 !important;
    color: #38bdf8 !important;
}

button[data-testid="stExpandSidebarButton"] button,
[data-testid="collapsedControl"] button {
    background: transparent !important;
    border: none !important;
    color: #38bdf8 !important;
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* SIDEBAR COLLAPSE BUTTON («) INSIDE OPEN SIDEBAR */
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
section[data-testid="stSidebar"] button[kind="header"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-header"],
button[data-testid="stSidebarCollapseButton"],
button[aria-label="Collapse sidebar"] {
    display: flex !important;
    visibility: visible !important;
    pointer-events: auto !important;
    color: #38bdf8 !important;
    z-index: 10000001 !important;
}

section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] svg,
button[data-testid="stSidebarCollapseButton"] svg,
button[aria-label="Collapse sidebar"] svg {
    fill: #38bdf8 !important;
    stroke: #38bdf8 !important;
    color: #38bdf8 !important;
}

/* HIDE ONLY DEPLOY BUTTON AND MAIN MENU, NEVER THE EXPAND/COLLAPSE CONTROLS */
.stDeployButton,
[data-testid="stDeployButton"],
#MainMenu,
[data-testid="stMainMenu"],
[data-testid="stToolbarActions"],
[data-testid="stDecoration"],
footer {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
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

/* TOP APP NAVIGATION BAR (CLEAN INTEGRATED BANNER MATCHING PREVIEW) */
.top-header-banner,
.top-nav-bar {
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    background: #0b1222 !important;
    border: 1px solid rgba(30, 41, 59, 0.9) !important;
    border-radius: 14px !important;
    padding: 8px 16px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45) !important;
    box-sizing: border-box !important;
}

button[data-testid*="btn_top_pipeline_status"] {
    animation: breathe-glow 2.2s ease-in-out infinite !important;
    border-radius: 9999px !important;
    font-size: 0.78rem !important;
    padding: 6px 14px !important;
    font-weight: 700 !important;
}

.top-nav-left {
    display: flex;
    align-items: center;
    gap: 12px;
}

.top-nav-logo {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, #0284c7, #38bdf8);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    box-shadow: 0 3px 10px rgba(56, 189, 248, 0.3);
}

.top-nav-title {
    color: #ffffff !important;
    font-weight: 800;
    font-size: 1.05rem;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 8px;
}

.top-nav-pill {
    font-size: 0.65rem;
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    font-weight: 600;
    padding: 1px 7px;
    border-radius: 9999px;
}

.top-nav-subtitle {
    color: var(--muted) !important;
    font-size: 0.72rem;
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

/* TOP USER BADGE */
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

/* SIDEBAR — POSITIONED BELOW TOP HEADER */
section[data-testid="stSidebar"] {
    top: 56px !important;
    height: calc(100vh - 56px) !important;
    background: #0a101f !important;
    background-color: #0a101f !important;
    border-right: 1px solid var(--border) !important;
    z-index: 100 !important;
}

section[data-testid="stSidebar"] * {
    color: var(--text);
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
}

/* MAIN CONTENT CONTAINER — PADDED DOWN BELOW FIXED TOP HEADER */
.main .block-container {
    max-width: 100% !important;
    padding-top: 68px !important;
    padding-bottom: 7rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
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

/* BUTTONS — VELVET WARM AMBER PRIMARY & STEEL SKY SECONDARY */
.stApp .stButton > button[data-testid*="primary"],
.stApp button[data-testid*="primary"],
button[data-testid*="primary"],
button[kind="primary"],
button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #d97706, #f59e0b) !important;
    background-color: #f59e0b !important;
    color: #070b14 !important;
    border: 1px solid rgba(245, 158, 11, 0.6) !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    font-size: 0.85rem !important;
    box-shadow: 0 2px 10px rgba(217, 119, 6, 0.35) !important;
    transition: all 0.15s ease-in-out !important;
}

.stApp .stButton > button[data-testid*="primary"]:hover,
.stApp button[data-testid*="primary"]:hover,
button[data-testid*="primary"]:hover {
    background: linear-gradient(135deg, #f59e0b, #fbbf24) !important;
    color: #070b14 !important;
    box-shadow: 0 4px 16px rgba(245, 158, 11, 0.5) !important;
    transform: translateY(-1px);
}

.stApp .stButton > button[data-testid*="primary"] *,
button[data-testid*="primary"] * {
    color: #070b14 !important;
    fill: #070b14 !important;
    stroke: #070b14 !important;
    font-weight: 800 !important;
}

.stApp .stButton > button,
.stApp .stButton > button[data-testid*="secondary"],
.stApp button[data-testid*="secondary"],
button[data-testid*="secondary"],
button[kind="secondary"] {
    color: #cbd5e1 !important;
    background: #14233c !important;
    background-color: #14233c !important;
    border: 1px solid #283854 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25) !important;
    transition: all 0.15s ease-in-out !important;
}

.stApp .stButton > button:hover,
.stApp .stButton > button[data-testid*="secondary"]:hover,
button[data-testid*="secondary"]:hover {
    background: #1d3254 !important;
    border-color: #38bdf8 !important;
    color: #ffffff !important;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.3) !important;
}

.stApp .stButton > button *,
button[data-testid*="secondary"] * {
    color: inherit !important;
    fill: currentColor !important;
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

/* TABS — SLEEK SEGMENTED PILLS (ELIMINATES CLUNKY ODD GLOWING HIGHLIGHT LINE) */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    background-color: #070b14 !important;
    padding: 5px !important;
    border-radius: 12px !important;
    border: 1px solid #1e293b !important;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4) !important;
}

.stTabs [data-baseweb="tab-border"],
.stTabs [data-baseweb="tab-highlight"],
[data-baseweb="tab-highlight"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 8px 20px !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 0.86rem !important;
    border: 1px solid transparent !important;
    background-color: transparent !important;
    transition: all 0.15s ease-in-out !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #ffffff !important;
    background: rgba(255, 255, 255, 0.04) !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"],
.stTabs [aria-selected="true"] {
    background: #14233c !important;
    background-color: #14233c !important;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.4) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35) !important;
    font-weight: 700 !important;
}

/* CHAT MESSAGES & CARDS (MATCHING PREVIEW EXACTLY) */
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
    max-width: 88%;
    margin-left: auto;
}

.chat-card-user {
    background: #1b253b;
    border: 1px solid rgba(245, 158, 11, 0.4);
    border-radius: 16px 16px 4px 16px;
    padding: 12px 16px;
    color: #f1f5f9;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
    width: 100%;
}

.chat-card-user-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(245, 158, 11, 0.25);
    padding-bottom: 5px;
    margin-bottom: 8px;
    font-size: 0.72rem;
}

.chat-avatar-user {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: #d97706;
    color: #ffffff !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.82rem;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(217, 119, 6, 0.35);
}

.chat-row-assistant {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;
    max-width: 90%;
}

.chat-card-assistant {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px 16px 16px 4px;
    padding: 14px 18px;
    color: #e2e8f0;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
    width: 100%;
}

.chat-card-assistant-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 5px;
    margin-bottom: 8px;
    font-size: 0.72rem;
}

.chat-avatar-assistant {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: #121e36;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(56, 189, 248, 0.2);
}

/* REFINED MIDNIGHT STEEL MESSAGE DOCK (BALANCED DARK TONE, ZERO EYE STRAIN) */
[data-testid="stBottom"] {
    background: #0b1424 !important;
    background-color: #0b1424 !important;
    border-top: 1px solid rgba(56, 189, 248, 0.4) !important;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.5), 0 -1px 3px rgba(56, 189, 248, 0.15) !important;
    padding: 10px 16px 12px 16px !important;
    z-index: 50 !important;
}

[data-testid="stBottom"] > div {
    background: transparent !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}

[data-testid="stChatInput"] {
    background: #070e1a !important;
    background-color: #070e1a !important;
    border: 1.5px solid rgba(56, 189, 248, 0.45) !important;
    border-radius: 12px !important;
    box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.4) !important;
    transition: all 0.2s ease-in-out !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.35) !important;
}

[data-testid="stChatInput"] textarea {
    color: #f1f5f9 !important;
    background: #070e1a !important;
    background-color: #070e1a !important;
    border-radius: 10px !important;
    font-size: 0.90rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #64748b !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"] button {
    color: #38bdf8 !important;
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
