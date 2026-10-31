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
    --primary: #f59e0b;
    --primary-hover: #d97706;
    --sky: #38bdf8;
    --sky-dark: #0284c7;
    --dock-bg: #14233c;
    --dock-input-bg: #0b1628;
}

/* CUSTOM SCROLLBARS */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0b1120; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #334155; }

/* SUPPRESS STREAMLIT DEFAULT HEADER & SIDEBAR ENTIRELY */
header[data-testid="stHeader"],
section[data-testid="stSidebar"],
[data-testid="collapsedControl"],
button[data-testid="stExpandSidebarButton"],
#MainMenu,
footer,
.stDeployButton {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    position: absolute !important;
    pointer-events: none !important;
}

/* GLOBAL RESET & FONTS */
html, body, [data-testid="stAppViewContainer"] {
    background: #070b14 !important;
    background-color: #070b14 !important;
    color: #f1f5f9 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    overflow-x: hidden !important;
}

/* MAIN CONTENT CONTAINER */
.main .block-container {
    max-width: 100% !important;
    padding-top: 0.65rem !important;
    padding-bottom: 5.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
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

/* BUTTONS — VELVET WARM AMBER PRIMARY & STEEL SKY SECONDARY */
.stApp .stButton > button[data-testid*="primary"],
.stApp button[data-testid*="primary"],
button[data-testid*="primary"],
button[kind="primary"],
button[kind="primaryFormSubmit"] {
    background: #f59e0b !important;
    background-color: #f59e0b !important;
    color: #020617 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3) !important;
    transition: all 0.15s ease-in-out !important;
}

.stApp .stButton > button[data-testid*="primary"]:hover,
.stApp button[data-testid*="primary"]:hover,
button[data-testid*="primary"]:hover {
    background: #d97706 !important;
    background-color: #d97706 !important;
    color: #000000 !important;
    box-shadow: 0 4px 14px rgba(245, 158, 11, 0.5) !important;
    transform: translateY(-1px) !important;
}

.stApp .stButton > button[data-testid*="secondary"],
.stApp button[data-testid*="secondary"],
button[data-testid*="secondary"],
button[kind="secondary"] {
    background: #14233c !important;
    background-color: #14233c !important;
    color: #bae6fd !important;
    border: 1px solid rgba(56, 189, 248, 0.35) !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.80rem !important;
    transition: all 0.15s ease-in-out !important;
}

.stApp .stButton > button[data-testid*="secondary"]:hover,
.stApp button[data-testid*="secondary"]:hover,
button[data-testid*="secondary"]:hover {
    background: #1d3254 !important;
    background-color: #1d3254 !important;
    border-color: #38bdf8 !important;
    color: #ffffff !important;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.35) !important;
}

/* INPUT FIELDS */
.stApp input,
.stApp textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] > div {
    color: #f1f5f9 !important;
    background-color: #070b14 !important;
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
    background-color: #070b14 !important;
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
    gap: 4px !important;
    background-color: #070b14 !important;
    padding: 4px !important;
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
    padding: 7px 18px !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
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

/* CHAT MESSAGES & CARDS */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 4px 0 !important;
}

.chat-row-user {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 14px;
    max-width: 90%;
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
    border-radius: 50%;
    background: #f59e0b;
    color: #020617 !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.80rem;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(245, 158, 11, 0.35);
}

.chat-row-assistant {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 14px;
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
    border-radius: 50%;
    background: #121e36;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.05rem;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(56, 189, 248, 0.2);
}

/* REFINED STEEL SKY-BLUE MESSAGE DOCK */
[data-testid="stBottom"] {
    background: transparent !important;
    background-color: transparent !important;
    padding: 0 !important;
    z-index: 100 !important;
}

[data-testid="stBottom"] > div {
    background: #14233c !important;
    background-color: #14233c !important;
    border-top: 2px solid rgba(56, 189, 248, 0.8) !important;
    box-shadow: 0 -4px 20px rgba(56, 189, 248, 0.25), 0 -1px 4px rgba(14, 165, 233, 0.15) !important;
    padding: 10px 16px 8px 16px !important;
}

[data-testid="stChatInput"] {
    background: #0b1628 !important;
    background-color: #0b1628 !important;
    border: 2px solid rgba(56, 189, 248, 0.6) !important;
    border-radius: 12px !important;
    box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.4) !important;
    transition: all 0.2s ease-in-out !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.4) !important;
}

[data-testid="stChatInput"] textarea {
    color: #f1f5f9 !important;
    background: #0b1628 !important;
    background-color: #0b1628 !important;
    border-radius: 10px !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"] button {
    background: #0284c7 !important;
    background-color: #0284c7 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    border: none !important;
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

/* NATIVE DIALOG MODAL STYLING */
div[data-testid="stDialog"] div[role="dialog"] {
    background: #0b1222 !important;
    border: 2px solid rgba(56, 189, 248, 0.5) !important;
    border-radius: 18px !important;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8) !important;
    color: #f1f5f9 !important;
}

div[data-testid="stDialog"] div[role="dialog"] header {
    border-bottom: 1px solid #1e293b !important;
}

div[data-testid="stDialog"] div[role="dialog"] button[aria-label="Close"] {
    color: #94a3b8 !important;
}

div[data-testid="stDialog"] div[role="dialog"] button[aria-label="Close"]:hover {
    color: #ffffff !important;
    background: #1e293b !important;
}
</style>
"""
