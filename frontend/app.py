"""
Adaptive Learning Engine – Streamlit Frontend
Single chat input drives the entire session (topic entry + answering).
"""

import uuid
import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"
MAX_ATTEMPTS = 5  # mirrors backend default

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Adaptive Tutor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global Styles */
* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
}

/* Hide Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
.block-container { 
    padding-top: 2.5rem; 
    padding-bottom: 1rem;
    max-width: 1400px;
}

/* Main background with gradient */
.stApp {
    background: linear-gradient(135deg, #0a0f1a 0%, #06080f 50%, #0a0d18 100%);
    background-attachment: fixed;
}

/* Sidebar - Modern gradient design */
section[data-testid="stSidebar"] { 
    background: linear-gradient(180deg, #0f172a 0%, #0b1220 100%) !important;
    border-right: 1px solid rgba(79, 142, 247, 0.1);
    backdrop-filter: blur(10px);
}

section[data-testid="stSidebar"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 200px;
    background: radial-gradient(circle at top, rgba(79, 142, 247, 0.15), transparent);
    pointer-events: none;
}

section[data-testid="stSidebar"] * { 
    color: #F0F2F0 !important; 
}

section[data-testid="stSidebar"] label { 
    color: #9ca3af !important; 
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* Smooth section headers */
.sidebar-section {
    margin: 2rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(79, 142, 247, 0.1);
}

.sidebar-title {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #4F8EF7;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Green gradient button */
section[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #4F8EF7 0%, #3B6FD8 100%);
    color: #0a0f1a;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    padding: 0.75rem 1.25rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 12px rgba(79, 142, 247, 0.15);
    position: relative;
    overflow: hidden;
}

section[data-testid="stSidebar"] .stButton button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    transition: left 0.5s;
}

section[data-testid="stSidebar"] .stButton button:hover::before {
    left: 100%;
}

section[data-testid="stSidebar"] .stButton button:hover {
    background: linear-gradient(135deg, #6EA8FE 0%, #4F8EF7 100%);
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(79, 142, 247, 0.35);
}

/* Score badges - Smooth glass design */
.badge { 
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 8px 18px; 
    border-radius: 24px; 
    font-size: 0.875rem; 
    font-weight: 600;
    letter-spacing: 0.02em;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.badge:hover {
    transform: translateY(-1px);
}

.badge-correct   { 
    background: linear-gradient(135deg, rgba(79, 142, 247, 0.15) 0%, rgba(79, 142, 247, 0.1) 100%);
    color: #6EA8FE;
    border: 1.5px solid rgba(79, 142, 247, 0.4);
    box-shadow: 0 4px 12px rgba(79, 142, 247, 0.15);
}

.badge-partial   { 
    background: linear-gradient(135deg, rgba(251, 191, 36, 0.2) 0%, rgba(251, 191, 36, 0.1) 100%);
    color: #FCD34D;
    border: 1.5px solid rgba(251, 191, 36, 0.4);
    box-shadow: 0 4px 12px rgba(251, 191, 36, 0.15);
}

.badge-incorrect { 
    background: linear-gradient(135deg, rgba(248, 113, 113, 0.2) 0%, rgba(248, 113, 113, 0.1) 100%);
    color: #FCA5A5;
    border: 1.5px solid rgba(248, 113, 113, 0.4);
    box-shadow: 0 4px 12px rgba(248, 113, 113, 0.15);
}

/* Misconception card - Smooth glass effect */
.mcard { 
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.6) 0%, rgba(20, 20, 20, 0.4) 100%);
    backdrop-filter: blur(20px);
    border-left: 3px solid #4F8EF7;
    border-radius: 16px;
    padding: 20px 24px;
    margin: 12px 0;
    font-size: 0.875rem;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.mcard:hover {
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.8) 0%, rgba(25, 25, 25, 0.6) 100%);
    transform: translateX(4px);
    box-shadow: 0 8px 24px rgba(79, 142, 247, 0.1);
}

.mcard-type { 
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #4F8EF7;
    margin-bottom: 10px;
    opacity: 0.9;
}

.mcard-fix { 
    color: #6EA8FE;
    margin-top: 12px;
    font-size: 0.875rem;
    padding-left: 24px;
    position: relative;
    line-height: 1.6;
}

.mcard-fix::before {
    content: "✓";
    position: absolute;
    left: 0;
    color: #4F8EF7;
    font-weight: bold;
    font-size: 1.1rem;
}

/* Feedback card - Premium glass design */
.fcard { 
    background: linear-gradient(135deg, rgba(25, 25, 25, 0.6) 0%, rgba(15, 15, 15, 0.4) 100%);
    backdrop-filter: blur(20px);
    border: 1.5px solid rgba(79, 142, 247, 0.15);
    border-radius: 20px;
    padding: 24px 28px;
    font-size: 0.875rem;
    margin-top: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}

.fcard:hover {
    border-color: rgba(79, 142, 247, 0.3);
    box-shadow: 0 12px 40px rgba(79, 142, 247, 0.1);
}

.fsection { 
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #9ca3af;
    margin: 20px 0 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(79, 142, 247, 0.1);
}

.fgreen { 
    color: #6EA8FE;
    margin: 8px 0;
    padding-left: 20px;
    position: relative;
    line-height: 1.6;
}

.fgreen::before {
    content: "→";
    position: absolute;
    left: 0;
    color: #4F8EF7;
}

.fred { 
    color: #FCA5A5;
    margin: 8px 0;
    padding-left: 20px;
    position: relative;
    line-height: 1.6;
}

.fred::before {
    content: "→";
    position: absolute;
    left: 0;
    color: #F87171;
}

.fblue { 
    color: #93C5FD;
    margin: 8px 0;
    padding-left: 20px;
    position: relative;
    line-height: 1.6;
}

.fblue::before {
    content: "→";
    position: absolute;
    left: 0;
    color: #60A5FA;
}

.fpurple { 
    color: #C4B5FD;
    line-height: 1.6;
}

/* Explanation tabs - Smooth pill design */
.etab { 
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 8px 18px;
    border-radius: 24px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 16px;
    margin-right: 10px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: default;
}

.etab:hover {
    transform: translateY(-2px);
}

.etab-simple { 
    background: linear-gradient(135deg, rgba(147, 197, 253, 0.2) 0%, rgba(147, 197, 253, 0.1) 100%);
    color: #93C5FD;
    border: 1.5px solid rgba(147, 197, 253, 0.3);
    box-shadow: 0 4px 12px rgba(147, 197, 253, 0.15);
}

.etab-normal { 
    background: linear-gradient(135deg, rgba(79, 142, 247, 0.15) 0%, rgba(79, 142, 247, 0.1) 100%);
    color: #6EA8FE;
    border: 1.5px solid rgba(79, 142, 247, 0.3);
    box-shadow: 0 4px 12px rgba(79, 142, 247, 0.15);
}

.etab-deep { 
    background: linear-gradient(135deg, rgba(196, 181, 253, 0.2) 0%, rgba(196, 181, 253, 0.1) 100%);
    color: #C4B5FD;
    border: 1.5px solid rgba(196, 181, 253, 0.3);
    box-shadow: 0 4px 12px rgba(196, 181, 253, 0.15);
}

/* Pills */
.pill { 
    display: inline-block;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    backdrop-filter: blur(10px);
}

.pill-on { 
    background: rgba(79, 142, 247, 0.25);
    color: #4F8EF7;
}

.pill-off { 
    background: rgba(91, 91, 91, 0.2);
    color: #9ca3af;
}

.pill-done { 
    background: rgba(147, 197, 253, 0.25);
    color: #93C5FD;
}

/* Horizontal rule */
hr.slim { 
    border: none;
    border-top: 1px solid rgba(79, 142, 247, 0.1);
    margin: 24px 0;
}

/* Chat messages - Premium glass cards */
.stChatMessage {
    background: transparent !important;
    padding: 1.5rem 0 !important;
}

[data-testid="stChatMessageContent"] {
    background: linear-gradient(135deg, rgba(25, 25, 25, 0.6) 0%, rgba(15, 15, 15, 0.4) 100%) !important;
    backdrop-filter: blur(20px) !important;
    border: 1.5px solid rgba(79, 142, 247, 0.1) !important;
    border-radius: 20px !important;
    padding: 1.5rem 1.75rem !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    transition: all 0.3s ease !important;
}

[data-testid="stChatMessageContent"]:hover {
    border-color: rgba(79, 142, 247, 0.15) !important;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4) !important;
}

/* User message - Green glass effect */
.stChatMessage[data-testid="user"] [data-testid="stChatMessageContent"] {
    background: linear-gradient(135deg, rgba(79, 142, 247, 0.15) 0%, rgba(79, 142, 247, 0.05) 100%) !important;
    border: 1.5px solid rgba(79, 142, 247, 0.3) !important;
    box-shadow: 0 8px 32px rgba(79, 142, 247, 0.1) !important;
}

/* Chat input - Modern design */
.stChatInputContainer {
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.8) 0%, rgba(20, 20, 20, 0.6) 100%);
    backdrop-filter: blur(20px);
    border: 1.5px solid rgba(79, 142, 247, 0.15);
    border-radius: 16px;
    padding: 6px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}

.stChatInputContainer:focus-within {
    border-color: rgba(79, 142, 247, 0.5);
    box-shadow: 0 8px 32px rgba(79, 142, 247, 0.15);
}

.stChatInputContainer textarea {
    background: transparent !important;
    color: #F0F2F0 !important;
    border: none !important;
}

.stChatInputContainer textarea::placeholder {
    color: #6b7280 !important;
}

/* Buttons */
.stButton button {
    background: linear-gradient(135deg, rgba(62, 63, 62, 0.8) 0%, rgba(46, 47, 46, 0.6) 100%);
    color: #F0F2F0;
    border: 1.5px solid rgba(91, 91, 91, 0.4);
    border-radius: 12px;
    font-weight: 600;
    padding: 0.65rem 1.25rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(10px);
}

.stButton button:hover {
    background: linear-gradient(135deg, rgba(78, 79, 78, 0.9) 0%, rgba(62, 63, 62, 0.7) 100%);
    border-color: rgba(79, 142, 247, 0.6);
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(79, 142, 247, 0.15);
}

/* Progress bars - Green gradient */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #4F8EF7 0%, #6EA8FE 100%) !important;
    border-radius: 10px;
}

.stProgress > div > div {
    background: rgba(30, 30, 30, 0.6) !important;
    border-radius: 10px;
    backdrop-filter: blur(10px);
}

/* Expander - Glass design */
.streamlit-expanderHeader {
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.6) 0%, rgba(20, 20, 20, 0.4) 100%) !important;
    backdrop-filter: blur(10px) !important;
    border: 1.5px solid rgba(79, 142, 247, 0.15) !important;
    border-radius: 12px !important;
    color: #F0F2F0 !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
}

.streamlit-expanderHeader:hover {
    border-color: rgba(79, 142, 247, 0.3) !important;
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.8) 0%, rgba(25, 25, 25, 0.6) 100%) !important;
}

.streamlit-expanderContent {
    background: linear-gradient(135deg, rgba(25, 25, 25, 0.5) 0%, rgba(15, 15, 15, 0.3) 100%) !important;
    backdrop-filter: blur(10px) !important;
    border: 1.5px solid rgba(79, 142, 247, 0.1) !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
}

/* Text inputs - Modern glass */
.stTextInput input {
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.6) 0%, rgba(20, 20, 20, 0.4) 100%) !important;
    backdrop-filter: blur(10px) !important;
    border: 1.5px solid rgba(79, 142, 247, 0.15) !important;
    border-radius: 12px !important;
    color: #F0F2F0 !important;
    padding: 0.75rem 1rem !important;
    transition: all 0.3s ease !important;
}

.stTextInput input:focus {
    border-color: rgba(79, 142, 247, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(79, 142, 247, 0.1) !important;
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.8) 0%, rgba(25, 25, 25, 0.6) 100%) !important;
}

/* File uploader - Modern design */
/* 📄 File uploader - clean minimal style */
[data-testid="stFileUploader"] {
    background: #1E1E1E;
    border: 1.5px solid rgba(79, 142, 247, 0.25);
    border-radius: 14px;
    padding: 1.5rem;
    text-align: center;
    transition: all 0.25s ease;
}

[data-testid="stFileUploader"]:hover {
    border-color: #4F8EF7;
    box-shadow: 0 0 0 1px rgba(84,199,80,0.3);
}

/* remove inner ugly box */
[data-testid="stFileUploader"] section {
    background: transparent !important;
    border: none !important;
}

/* upload button */
[data-testid="stFileUploader"] button {
    background: rgba(84,199,80,0.12);
    color: #4F8EF7;
    border: 1px solid rgba(84,199,80,0.4);
    border-radius: 10px;
    padding: 0.5rem 1.2rem;
    font-weight: 500;
    transition: all 0.2s ease;
}

[data-testid="stFileUploader"] button:hover {
    background: #4F8EF7;
    color: black;
}

/* text under button */
[data-testid="stFileUploader"] small {
    color: #5B5B5B !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: rgba(79, 142, 247, 0.5);
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.6) 0%, rgba(25, 25, 25, 0.4) 100%);
}

[data-testid="stFileUploader"] section {
    border: none !important;
    padding: 0 !important;
}

[data-testid="stFileUploader"] button {
    background: linear-gradient(135deg, rgba(79, 142, 247, 0.15) 0%, rgba(79, 142, 247, 0.1) 100%);
    color: #6EA8FE;
    border: 1.5px solid rgba(79, 142, 247, 0.4);
    border-radius: 10px;
    padding: 0.6rem 1.5rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

[data-testid="stFileUploader"] button:hover {
    background: linear-gradient(135deg, rgba(79, 142, 247, 0.3) 0%, rgba(79, 142, 247, 0.15) 100%);
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(79, 142, 247, 0.15);
}

/* Selectbox - Glass design */
.stSelectbox > div > div {
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.6) 0%, rgba(20, 20, 20, 0.4) 100%) !important;
    backdrop-filter: blur(10px) !important;
    border: 1.5px solid rgba(79, 142, 247, 0.15) !important;
    border-radius: 12px !important;
    transition: all 0.3s ease !important;
}

.stSelectbox > div > div:hover {
    border-color: rgba(79, 142, 247, 0.3) !important;
}

/* Info/Success/Warning/Error boxes */
.stAlert {
    background: linear-gradient(135deg, rgba(25, 25, 25, 0.6) 0%, rgba(15, 15, 15, 0.4) 100%) !important;
    backdrop-filter: blur(20px) !important;
    border-radius: 16px !important;
    border: 1.5px solid rgba(79, 142, 247, 0.15) !important;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
}

[data-baseweb="notification"] {
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.8) 0%, rgba(20, 20, 20, 0.6) 100%) !important;
    backdrop-filter: blur(20px) !important;
    border-left: 3px solid #4F8EF7 !important;
}

/* Headings */
h1, h2, h3 {
    color: #F0F2F0 !important;
    font-weight: 700 !important;
    line-height: 1.2 !important;
}

h2 {
    font-size: 1.75rem !important;
    margin-bottom: 0.75rem !important;
}

h3 {
    font-size: 1.25rem !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.75rem !important;
}

/* Captions */
.stCaption {
    color: #9ca3af !important;
    font-size: 0.75rem !important;
    line-height: 1.5 !important;
}

/* Markdown text */
.stMarkdown {
    color: #e5e7eb !important;
    line-height: 1.7 !important;
}

/* Code blocks */
code {
    background: linear-gradient(135deg, rgba(79, 142, 247, 0.15) 0%, rgba(79, 142, 247, 0.08) 100%) !important;
    color: #6EA8FE !important;
    padding: 3px 8px !important;
    border-radius: 6px !important;
    font-size: 0.875rem !important;
    border: 1px solid rgba(79, 142, 247, 0.15) !important;
}

/* Spinner */
.stSpinner > div {
    border-top-color: #4F8EF7 !important;
}

/* Custom title styling */
.main-title {
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #F0F2F0 0%, #6EA8FE 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    animation: fadeInUp 0.6s ease-out;
}

.main-title .emoji {
    font-size: 2.5rem;
    filter: drop-shadow(0 4px 12px rgba(79, 142, 247, 0.3));
}

.subtitle {
    color: #9ca3af;
    font-size: 0.95rem;
    margin-bottom: 2.5rem;
    font-weight: 400;
    animation: fadeInUp 0.6s ease-out 0.1s backwards;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Upload section card */
.upload-card {
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.5) 0%, rgba(20, 20, 20, 0.3) 100%);
    backdrop-filter: blur(20px);
    border: 1.5px solid rgba(79, 142, 247, 0.15);
    border-radius: 16px;
    padding: 1.5rem;
    margin: 1.5rem 0;
    transition: all 0.3s ease;
}

.upload-card:hover {
    border-color: rgba(79, 142, 247, 0.3);
    box-shadow: 0 8px 24px rgba(79, 142, 247, 0.1);
}

/* Stats card */
.stats-card {
    background: linear-gradient(135deg, rgba(79, 142, 247, 0.1) 0%, rgba(79, 142, 247, 0.05) 100%);
    backdrop-filter: blur(10px);
    border: 1.5px solid rgba(79, 142, 247, 0.15);
    border-radius: 12px;
    padding: 1rem;
    margin: 0.75rem 0;
    transition: all 0.3s ease;
}

.stats-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(79, 142, 247, 0.15);
}

.stat-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #9ca3af;
    margin-bottom: 0.5rem;
}

.stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #6EA8FE;
}

/* Divider */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(79, 142, 247, 0.3), transparent);
    margin: 2rem 0;
}
            
/* Hide header visually but keep sidebar toggle working */
header {
    position: fixed;
    top: 0;
    height: 0px;
    background: transparent !important;
    border: none !important;
    z-index: 999;
}

/* Keep sidebar toggle button accessible */
[data-testid="collapsedControl"] {
    position: fixed !important;
    top: 10px;
    left: 10px;
    z-index: 1000;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "user_id": str(uuid.uuid4())[:8],
        "messages": [],
        "session_active": False,
        "session_complete": False,
        "waiting_for_answer": False,
        "topic": "",
        "exp_level": "normal",
        "current_question": {},
        "learning_profile": {"weak_areas": [], "strengths": [], "progress": {}},
        "attempts": 0,
        "next_action": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── API ───────────────────────────────────────────────────────────────────────
def api_start(topic: str) -> dict:
    r = requests.post(f"{BACKEND_URL}/start",
                      json={"user_id": st.session_state.user_id, "topic": topic},
                      timeout=120)
    r.raise_for_status()
    return r.json()

def api_answer(answer: str) -> dict:
    r = requests.post(f"{BACKEND_URL}/answer",
                      json={"user_id": st.session_state.user_id, "user_answer": answer},
                      timeout=120)
    r.raise_for_status()
    return r.json()

def api_upload_pdf(data: bytes, name: str, topic: str) -> dict:
    r = requests.post(f"{BACKEND_URL}/upload_pdf",
                      files={"file": (name, data, "application/pdf")},
                      data={"topic": topic}, timeout=120)
    r.raise_for_status()
    return r.json()


# ── Render helpers ────────────────────────────────────────────────────────────
def render_explanation(exp: dict, level: str):
    text = exp.get(level) or exp.get("normal", "")
    tab_cls = {"simple": "etab-simple", "normal": "etab-normal", "deep": "etab-deep"}
    tab_lbl = {"simple": "🔵 Simple", "normal": "🟢 Standard", "deep": "🟣 Deep dive"}
    st.markdown(
        f'<span class="etab {tab_cls.get(level,"etab-normal")}">'
        f'{tab_lbl.get(level,"🟢 Standard")}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(text)
    cols = st.columns(2)
    kc = exp.get("key_concepts", [])
    cp = exp.get("common_pitfalls", [])
    if kc:
        with cols[0]:
            st.markdown("**💡 Key concepts**")
            for c in kc:
                st.markdown(f"- `{c}`")
    if cp:
        with cols[1]:
            st.markdown("**⚠️ Common pitfalls**")
            for p in cp:
                st.markdown(f"- {p}")


def render_question(q: dict):
    st.markdown(f"### {q.get('question','')}")
    parts = []
    if q.get("question_type"): parts.append(f"**Type:** {q['question_type']}")
    if q.get("difficulty"):    parts.append(f"**Difficulty:** {q['difficulty']}")
    if parts: st.caption("  ·  ".join(parts))
    if q.get("hint"):
        with st.expander("💡 Need a hint?"):
            st.info(q["hint"])


def render_eval_feedback(evaluation: dict, misconceptions: list, feedback: dict | None):
    score = evaluation.get("score", 0.0)
    label = evaluation.get("label", "incorrect")
    cls   = {"correct":"badge-correct","partial":"badge-partial",
             "incorrect":"badge-incorrect"}.get(label,"badge-incorrect")
    icon  = {"correct":"✓","partial":"◐","incorrect":"✗"}.get(label,"?")
    st.markdown(
        f'<span class="badge {cls}">{icon} {int(score*100)}% — {label.upper()}</span>',
        unsafe_allow_html=True,
    )
    reasoning = evaluation.get("reasoning","")
    if reasoning:
        st.markdown(
            f'<p style="color:#9ca3af;font-size:.875rem;margin-top:10px;line-height:1.6">{reasoning}</p>',
            unsafe_allow_html=True,
        )

    if misconceptions:
        st.markdown("<hr class='slim'>", unsafe_allow_html=True)
        st.markdown("**🔍 Misconceptions detected**")
        for m in misconceptions:
            st.markdown(f"""
<div class="mcard">
  <div class="mcard-type">{m.get('type','').replace('_',' ')} · {int(float(m.get('confidence',0))*100)}% confidence</div>
  <div style="color:#e5e7eb;line-height:1.6">{m.get('description','')}</div>
  <div class="mcard-fix">{m.get('correction','')}</div>
</div>""", unsafe_allow_html=True)

    if feedback:
        html = '<div class="fcard">'
        if feedback.get("message"):
            html += f'<p style="color:#e5e7eb;margin:0 0 10px;line-height:1.7">{feedback["message"]}</p>'
        if feedback.get("reinforcements"):
            html += '<div class="fsection">✓ What you got right</div>'
            for r in feedback["reinforcements"]:
                html += f'<div class="fgreen">{r}</div>'
        if feedback.get("improvements"):
            html += '<div class="fsection">→ Where to improve</div>'
            for i in feedback["improvements"]:
                html += f'<div class="fred">{i}</div>'
        if feedback.get("learning_guidance"):
            html += '<div class="fsection">📚 Learning guidance</div>'
            for g in feedback["learning_guidance"]:
                html += f'<div class="fblue">{g}</div>'
        if feedback.get("next_steps"):
            html += '<div class="fsection">🎯 Next steps</div>'
            ns = feedback["next_steps"]
            if isinstance(ns, list):
                for s in ns:
                    html += f'<div class="fpurple">• {s}</div>'
            else:
                html += f'<div class="fpurple">{ns}</div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)


# ── Replay chat history ───────────────────────────────────────────────────────
def replay_messages():
    for msg in st.session_state.messages:
        role = msg.get("role")
        typ  = msg.get("type")

        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg.get("content", ""))

        elif role == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                if typ == "explanation":
                    st.markdown("**📖 Explanation**")
                    render_explanation(msg["data"], st.session_state.exp_level)
                elif typ == "question":
                    st.markdown("**❓ Question**")
                    render_question(msg["data"])
                elif typ == "evaluation":
                    render_eval_feedback(
                        msg.get("evaluation", {}),
                        msg.get("misconceptions", []),
                        msg.get("feedback")
                    )
                elif typ == "complete":
                    st.success(msg.get("content", ""))
                elif typ == "error":
                    st.error(msg.get("content", ""))
                elif typ == "action":
                    act = msg.get("action", "")
                    if act == "followup":
                        st.info("📌 Let's try another question on the same topic.")
                    elif act == "simplify":
                        st.warning("🔁 Let me re-explain this more simply.")
                elif typ == "text":
                    st.markdown(msg.get("content", ""))


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚙️ Session Controls</div>', unsafe_allow_html=True)
    
    # Exp level
    exp_options = ["simple", "normal", "deep"]
    exp_labels = {"simple": "🔵 Simple", "normal": "🟢 Standard", "deep": "🟣 Deep"}
    current_exp = st.session_state.exp_level
    
    st.markdown("**Explanation depth**")
    selected = st.selectbox(
        "Choose your level",
        exp_options,
        index=exp_options.index(current_exp),
        format_func=lambda x: exp_labels[x],
        label_visibility="collapsed"
    )
    if selected != st.session_state.exp_level:
        st.session_state.exp_level = selected
        st.rerun()

    st.markdown("")
    
    # New session
    if st.button("🔄 New Session", use_container_width=True):
        for k in ["messages", "session_active", "session_complete", "waiting_for_answer",
                  "topic", "current_question", "attempts", "next_action"]:
            if k == "messages":
                st.session_state[k] = []
            elif k in ["session_active", "session_complete", "waiting_for_answer"]:
                st.session_state[k] = False
            elif k in ["topic", "next_action"]:
                st.session_state[k] = ""
            elif k == "current_question":
                st.session_state[k] = {}
            elif k == "attempts":
                st.session_state[k] = 0
        st.rerun()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # PDF upload - Modern file uploader style
    st.markdown('<div class="sidebar-title">📄 Reference Material</div>', unsafe_allow_html=True)
    st.caption("Upload PDFs to enhance explanations")
    
    uploaded = st.file_uploader("Drop your PDF here", type="pdf", label_visibility="collapsed")
    
    if uploaded:
        pdf_topic = st.text_input(
            "Tag this material",
            value=st.session_state.topic,
            placeholder="e.g., machine learning, calculus..."
        )
        
        if st.button("📤 Upload & Process", use_container_width=True):
            if pdf_topic.strip():
                with st.spinner("Processing your PDF..."):
                    try:
                        res = api_upload_pdf(uploaded.read(), uploaded.name, pdf_topic.strip())
                        st.success(f"✓ Indexed {res['chunks_stored']} sections")
                    except Exception as e:
                        st.error(f"Upload failed: {str(e)}")
            else:
                st.warning("Please tag your material first")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Learning profile
    profile = st.session_state.learning_profile
    progress = profile.get("progress", {})
    
    if progress or profile.get("strengths") or profile.get("weak_areas"):
        st.markdown('<div class="sidebar-title">📊 Your Progress</div>', unsafe_allow_html=True)
    
    if progress:
        for t, d in progress.items():
            avg = d.get("avg_score", 0)
            att = d.get("attempts", 0)
            st.markdown(f'<div class="stat-label">{t}</div>', unsafe_allow_html=True)
            st.caption(f"{att} attempts · {int(avg*100)}% average")
            st.progress(float(avg))
            st.markdown("")

    strengths = profile.get("strengths", [])
    if strengths:
        st.markdown("**💪 Strengths**")
        for s in strengths[:5]: 
            st.markdown(f'<div style="color:#6EA8FE;font-size:0.875rem;margin:6px 0">✓ {s}</div>', unsafe_allow_html=True)

    weak = profile.get("weak_areas", [])
    if weak:
        st.markdown("**🎯 Focus Areas**")
        for w in weak[:5]: 
            st.markdown(f'<div style="color:#FCD34D;font-size:0.875rem;margin:6px 0">→ {w}</div>', unsafe_allow_html=True)

    if st.session_state.session_active and not st.session_state.session_complete:
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        att = st.session_state.attempts
        st.markdown(f'<div class="stat-label">Current Attempt</div>', unsafe_allow_html=True)
        st.caption(f"{att} of {MAX_ATTEMPTS} attempts used")
        st.progress(min(att / MAX_ATTEMPTS, 1.0))


# ── Main chat area ────────────────────────────────────────────────────────────
st.markdown('<div class="main-title"><span class="emoji">🧠</span> Adaptive Tutor</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Your AI-powered personalized learning companion</div>', unsafe_allow_html=True)

# Replay history
replay_messages()

# Welcome hint when idle
if not st.session_state.session_active and not st.session_state.session_complete:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(
            "**Welcome!** I'm your adaptive tutor, ready to help you master any topic.\n\n"
            "**How it works:**\n"
            "1. **Start** — Type any topic you want to learn\n"
            "2. **Learn** — Get explanations tailored to your level\n"
            "3. **Practice** — Answer adaptive questions\n"
            "4. **Master** — Receive personalized feedback and guidance\n\n"
            "**Try topics like:** *binary search trees*, *neural networks*, *the French Revolution*, "
            "*recursion*, *photosynthesis*, *quantum mechanics*"
        )

# ── Chat input ────────────────────────────────────────────────────────────────
if st.session_state.session_complete:
    st.chat_input("🎓 Session complete — start a new one to continue learning", disabled=True)

elif not st.session_state.session_active:
    # Waiting for a topic
    user_input = st.chat_input("💭 What would you like to learn today?")
    if user_input and user_input.strip():
        topic = user_input.strip()
        st.session_state.topic = topic
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        st.session_state.messages.append({"role":"user","type":"text","content":user_input})

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"Preparing your lesson on **{topic}**..."):
                try:
                    data = api_start(topic)
                    explanation = data.get("explanation", {})
                    question    = data.get("question", {})

                    st.session_state.current_question  = question
                    st.session_state.attempts          = data.get("attempts", 0)
                    st.session_state.session_active    = True
                    st.session_state.waiting_for_answer = True

                    st.markdown("**📖 Here's your explanation:**")
                    render_explanation(explanation, st.session_state.exp_level)
                    st.session_state.messages.append(
                        {"role":"assistant","type":"explanation","data":explanation})

                    st.markdown("---")
                    st.markdown("**❓ Question for you:**")
                    render_question(question)
                    st.session_state.messages.append(
                        {"role":"assistant","type":"question","data":question})

                except requests.HTTPError as e:
                    err = f"Backend error: {e.response.text}"
                    st.error(err)
                    st.session_state.messages.append({"role":"assistant","type":"error","content":err})
                except Exception as e:
                    err = f"Could not reach backend: {e}"
                    st.error(err)
                    st.session_state.messages.append({"role":"assistant","type":"error","content":err})
        st.rerun()

else:
    # Active session — waiting for answer
    user_input = st.chat_input("✍️ Type your answer...")
    if user_input and user_input.strip():
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        st.session_state.messages.append({"role":"user","type":"answer","content":user_input})

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyzing your response..."):
                try:
                    data = api_answer(user_input.strip())

                    evaluation    = data.get("evaluation", {})
                    misconceptions = data.get("misconceptions", [])
                    feedback      = data.get("feedback")
                    next_action   = data.get("next_action", "")
                    status        = data.get("status", "")

                    st.session_state.learning_profile = data.get(
                        "learning_profile", st.session_state.learning_profile)
                    st.session_state.attempts  = data.get("attempts", 0)
                    st.session_state.next_action = next_action

                    render_eval_feedback(evaluation, misconceptions, feedback)
                    st.session_state.messages.append({
                        "role":"assistant","type":"evaluation",
                        "evaluation":evaluation,"misconceptions":misconceptions,"feedback":feedback,
                    })

                    if status == "session_complete":
                        st.session_state.session_complete  = True
                        st.session_state.waiting_for_answer = False
                        completion_msg = (
                            f"🎓 **Congratulations!** You've mastered **{st.session_state.topic}**! "
                            "Start a **New Session** to continue your learning journey."
                        )
                        st.success(completion_msg)
                        st.session_state.messages.append(
                            {"role":"assistant","type":"complete","content":completion_msg})
                    else:
                        # Router action label
                        if next_action == "followup":
                            st.info("📌 Let's try another question on the same topic.")
                        elif next_action == "simplify":
                            st.warning("🔁 Let me re-explain this more simply.")
                        st.session_state.messages.append(
                            {"role":"assistant","type":"action","action":next_action})

                        # New explanation on simplify
                        if next_action == "simplify" and data.get("explanation"):
                            exp = data["explanation"]
                            st.markdown("**📖 Updated explanation:**")
                            render_explanation(exp, st.session_state.exp_level)
                            st.session_state.messages.append(
                                {"role":"assistant","type":"explanation","data":exp})

                        # Next question
                        if data.get("question"):
                            q = data["question"]
                            st.session_state.current_question  = q
                            st.session_state.waiting_for_answer = True
                            st.markdown("**❓ Next question:**")
                            render_question(q)
                            st.session_state.messages.append(
                                {"role":"assistant","type":"question","data":q})

                except requests.HTTPError as e:
                    err = f"Backend error: {e.response.text}"
                    st.error(err)
                    st.session_state.messages.append({"role":"assistant","type":"error","content":err})
                except Exception as e:
                    err = f"Connection error: {e}"
                    st.error(err)
                    st.session_state.messages.append({"role":"assistant","type":"error","content":err})
        st.rerun()