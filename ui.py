"""
Soil & Crop Planner — Streamlit UI v2
Farmer-first guided workflow with map-based field selection.

Run: python -m streamlit run streamlit_app.py
Requires FastAPI backend on http://localhost:8000
"""

import json
import urllib.request
import urllib.error
from datetime import date, datetime

import streamlit as st
import folium
from streamlit_folium import st_folium

API = "http://localhost:8000/api/v1"

st.set_page_config(
    page_title="Soil & Crop Planner",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Centralized Accessibility Color Tokens ─────────────────────────────────────
# All color pairings verified for WCAG 2.2 AA (>= 4.5:1) and AAA (>= 7.0:1)
COLOR_PAGE_BG        = "#F7F6F1"
COLOR_SURFACE        = "#FFFFFF"
COLOR_SURFACE_SUBTLE = "#F1EFE8"
COLOR_TEXT_PRIMARY   = "#1F2923"  # 13.9:1 on page bg, 15.0:1 on white (AAA)
COLOR_TEXT_SECONDARY = "#46534B"  # 7.5:1 on page bg, 8.1:1 on white (AAA)
COLOR_TEXT_MUTED     = "#56645C"  # 5.8:1 on page bg, 6.2:1 on white (AA)
COLOR_PRIMARY        = "#245236"  # 8.3:1 on page bg, 9.0:1 on white (AAA)
COLOR_PRIMARY_HOVER  = "#1A3C28"  # 12.2:1 with white text
COLOR_BORDER_DEFAULT = "#C8CEC8"
COLOR_BORDER_STRONG  = "#8B948C"  # 3.1:1 non-text control contrast (WCAG 2.1 1.4.11)
COLOR_BORDER_SUBTLE  = "#D8DDD8"

COLOR_GOOD_TEXT      = "#1B4D2E"  # 8.5:1 on badge bg, 9.8:1 on white (AAA)
COLOR_GOOD_BG        = "#E8F2EA"
COLOR_GOOD_BORDER    = "#9DC3A7"

COLOR_MOD_TEXT       = "#784805"  # 6.9:1 on badge bg, 7.7:1 on white (AAA)
COLOR_MOD_BG         = "#FDF2DC"
COLOR_MOD_BORDER     = "#DFC188"

COLOR_LOW_TEXT       = "#8E231C"  # 7.5:1 on badge bg, 8.7:1 on white (AAA)
COLOR_LOW_BG         = "#FBE9E8"
COLOR_LOW_BORDER     = "#E4A7A4"

COLOR_INFO_TEXT      = "#204C68"  # 8.0:1 on badge bg, 9.2:1 on white (AAA)
COLOR_INFO_BG        = "#E9F1F6"
COLOR_INFO_BORDER    = "#A6C5D7"

COLOR_TEXT_INVERSE   = "#FFFFFF"
COLOR_BG_SURFACE     = COLOR_SURFACE

COLOR_STATUS_GOOD_TEXT = COLOR_GOOD_TEXT
COLOR_STATUS_GOOD_BG   = COLOR_GOOD_BG
COLOR_STATUS_GOOD_BORDER = COLOR_GOOD_BORDER

COLOR_STATUS_MOD_TEXT  = COLOR_MOD_TEXT
COLOR_STATUS_MOD_BG    = COLOR_MOD_BG
COLOR_STATUS_MOD_BORDER = COLOR_MOD_BORDER

COLOR_STATUS_LOW_TEXT  = COLOR_LOW_TEXT
COLOR_STATUS_LOW_BG    = COLOR_LOW_BG
COLOR_STATUS_LOW_BORDER = COLOR_LOW_BORDER

COLOR_STATUS_INFO_TEXT = COLOR_INFO_TEXT
COLOR_STATUS_INFO_BG   = COLOR_INFO_BG
COLOR_STATUS_INFO_BORDER = COLOR_INFO_BORDER


# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap');

/* Centralized Semantic Color Tokens */
:root {
    /* Page & Surfaces */
    --bg-page: #F7F6F1;
    --bg-surface: #FFFFFF;
    --bg-surface-subtle: #F1EFE8;
    --bg-hover: #ECEAE2;
    --bg-sidebar: #EDEAE2;

    /* Typography Hierarchy (All >= 4.5:1, mostly >= 7:1) */
    --text-primary: #1F2923;      /* 13.9:1 on page, 15.0:1 on white (AAA) */
    --text-secondary: #46534B;    /* 7.5:1 on page, 8.1:1 on white (AAA) */
    --text-muted: #56645C;        /* 5.8:1 on page, 6.2:1 on white (AA) */
    --text-inverse: #FFFFFF;      /* for dark backgrounds */
    --text-on-primary: #FFFFFF;   /* 9.0:1 on primary button (AAA) */

    /* Brand & Primary Actions */
    --primary: #245236;           /* 8.3:1 on page, 9.0:1 on white (AAA) */
    --primary-hover: #1A3C28;     /* 12.2:1 with white text */
    --primary-active: #132E1E;
    --primary-subtle: #E8F2EA;

    /* Structural & Control Borders */
    --border-default: #C8CEC8;    /* card boundaries & dividers */
    --border-strong: #8B948C;     /* 3.1:1 input/control boundaries (WCAG 2.1 1.4.11) */
    --border-subtle: #D8DDD8;     /* table row & data item dividers */

    /* Focus & States */
    --focus-ring: #245236;
    --focus-ring-outline: rgba(36, 82, 54, 0.35);

    /* Accessible Status Tokens (Each pair >= 6.9:1) */
    --status-good-text: #1B4D2E;   /* 8.5:1 on badge, 9.8:1 on white (AAA) */
    --status-good-bg: #E8F2EA;
    --status-good-border: #9DC3A7;

    --status-mod-text: #784805;    /* 6.9:1 on badge, 7.7:1 on white (AAA) */
    --status-mod-bg: #FDF2DC;
    --status-mod-border: #DFC188;

    --status-low-text: #8E231C;    /* 7.5:1 on badge, 8.7:1 on white (AAA) */
    --status-low-bg: #FBE9E8;
    --status-low-border: #E4A7A4;

    --status-info-text: #204C68;   /* 8.0:1 on badge, 9.2:1 on white (AAA) */
    --status-info-bg: #E9F1F6;
    --status-info-border: #A6C5D7;
}

html, body, [class*="css"], .stApp {
    font-family: 'Source Sans 3', 'Segoe UI', system-ui, sans-serif;
    font-size: 14px;
    color: var(--text-primary);
    background-color: var(--bg-page);
}

/* Headings */
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}

/* Paragraphs & Text */
p, span, div, label {
    color: var(--text-primary);
}

/* Primary and Download Buttons */
.stButton > button,
.stDownloadButton > button {
    background-color: var(--primary) !important;
    color: var(--text-on-primary) !important;
    border: 1px solid var(--primary) !important;
    border-radius: 4px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 8px 22px !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.stButton > button:hover,
.stDownloadButton > button:hover {
    background-color: var(--primary-hover) !important;
    border-color: var(--primary-hover) !important;
    color: var(--text-on-primary) !important;
}
.stButton > button:active,
.stDownloadButton > button:active {
    background-color: var(--primary-active) !important;
    border-color: var(--primary-active) !important;
}
.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {
    outline: 2px solid var(--focus-ring) !important;
    outline-offset: 2px !important;
}
/* Secondary / Clear / Back buttons */
.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {
    background-color: var(--bg-surface) !important;
    color: var(--primary) !important;
    border: 1px solid var(--border-strong) !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button[data-testid="baseButton-secondary"]:hover {
    background-color: var(--bg-hover) !important;
    color: var(--primary-hover) !important;
    border-color: var(--primary) !important;
}

/* Step navigation */
.step-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    margin-bottom: 24px;
    border-bottom: 2px solid var(--border-default);
}
.step-item {
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    cursor: default;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    letter-spacing: 0.02em;
    transition: color 0.15s ease;
}
.step-item.active {
    color: var(--primary);
    font-weight: 700;
    border-bottom: 3px solid var(--primary);
}
.step-item.done {
    color: var(--primary);
    font-weight: 600;
}

/* Section label */
.section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    text-transform: uppercase;
    margin-bottom: 8px;
    margin-top: 20px;
}

/* Step description */
.step-desc {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 14px;
    line-height: 1.5;
}

/* Data rows */
.data-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-subtle);
    font-size: 13px;
}
.data-row:last-child {
    border-bottom: none;
}
.data-row .param {
    color: var(--text-secondary);
    font-weight: 500;
}
.data-row .val {
    font-weight: 700;
    color: var(--text-primary);
}

/* Status text classes (AA/AAA compliant) */
.status-good {
    color: var(--status-good-text);
    font-weight: 700;
}
.status-mod {
    color: var(--status-mod-text);
    font-weight: 700;
}
.status-low {
    color: var(--status-low-text);
    font-weight: 700;
}

/* Status pills */
.pill-good {
    background: var(--status-good-bg);
    color: var(--status-good-text);
    border: 1px solid var(--status-good-border);
    padding: 3px 9px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    display: inline-block;
}
.pill-mod {
    background: var(--status-mod-bg);
    color: var(--status-mod-text);
    border: 1px solid var(--status-mod-border);
    padding: 3px 9px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    display: inline-block;
}
.pill-low {
    background: var(--status-low-bg);
    color: var(--status-low-text);
    border: 1px solid var(--status-low-border);
    padding: 3px 9px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    display: inline-block;
}

/* Info box */
.info-box {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-left: 4px solid var(--primary);
    border-radius: 4px;
    padding: 14px 16px;
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.6;
    margin-bottom: 16px;
}
.info-box.warn {
    border-left-color: var(--status-mod-text);
    background: var(--status-mod-bg);
    border-color: var(--status-mod-border);
}
.info-box.alert {
    border-left-color: var(--status-low-text);
    background: var(--status-low-bg);
    border-color: var(--status-low-border);
}
.info-box.info {
    border-left-color: var(--status-info-text);
    background: var(--status-info-bg);
    border-color: var(--status-info-border);
}

/* Score bar */
.score-bar-wrap {
    margin: 4px 0 10px 0;
}
.score-bar-label {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 3px;
}
.score-bar-track {
    background: var(--border-subtle);
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
}
.sb-good {
    background: var(--primary);
    height: 8px;
    border-radius: 4px;
}
.sb-mod {
    background: #C27803;
    height: 8px;
    border-radius: 4px;
}
.sb-low {
    background: var(--status-low-text);
    height: 8px;
    border-radius: 4px;
}

/* Tables */
.report-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-top: 6px;
    margin-bottom: 14px;
    border: 1px solid var(--border-default);
    border-radius: 4px;
    overflow: hidden;
}
.report-table th {
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-primary);
    background-color: var(--bg-surface-subtle);
    border-bottom: 2px solid var(--border-strong);
    padding: 9px 10px;
}
.report-table td {
    padding: 9px 10px;
    border-bottom: 1px solid var(--border-subtle);
    color: var(--text-primary);
    font-size: 13px;
}
.report-table tr:last-child td {
    border-bottom: none;
}
.report-table tr:hover td {
    background-color: var(--bg-hover);
}

/* Financial cards */
.fin-card {
    border: 1px solid var(--border-default);
    border-radius: 4px;
    background: var(--bg-surface);
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.fin-card .fc-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
}
.fin-card .fc-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.25;
    margin-top: 4px;
}
.fin-card .fc-sub {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-top: 3px;
}

/* Recommendation card */
.rec-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-left: 4px solid var(--primary);
    border-radius: 4px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.rec-card.alt {
    border-left-color: var(--status-mod-text);
}

/* Timeline card in rotation */
.timeline-card {
    border: 1px solid var(--border-strong);
    border-radius: 4px;
    padding: 14px 12px;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

/* Disclaimers */
.disclaimer {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    border-top: 1px solid var(--border-default);
    padding-top: 12px;
    margin-top: 20px;
    line-height: 1.5;
}

hr {
    border: none;
    border-top: 1px solid var(--border-default);
    margin: 18px 0;
}

/* Streamlit Native Form Elements - WCAG Compliance */
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.01em;
}

/* Inputs & Textareas */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    color: var(--text-primary) !important;
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 4px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}
[data-baseweb="input"] input:focus,
[data-baseweb="textarea"] textarea:focus,
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 2px var(--focus-ring-outline) !important;
    outline: none !important;
}

/* Input Placeholders */
input::placeholder,
textarea::placeholder {
    color: var(--text-muted) !important;
    opacity: 1 !important;
}

/* NumberInput steppers (+/-) */
.stNumberInput button {
    color: var(--text-primary) !important;
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-strong) !important;
}
.stNumberInput button:hover {
    background-color: var(--bg-hover) !important;
    color: var(--primary) !important;
}

/* Selectbox & Dropdowns */
[data-baseweb="select"] > div {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 4px !important;
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}
[data-baseweb="select"] > div:focus-within {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 2px var(--focus-ring-outline) !important;
}
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"] {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-default) !important;
}
[data-baseweb="popover"] [role="option"] {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}
[data-baseweb="popover"] [role="option"][aria-selected="true"],
[data-baseweb="popover"] [role="option"]:hover {
    background-color: var(--status-good-bg) !important;
    color: var(--status-good-text) !important;
    font-weight: 600 !important;
}

/* Multiselect Tags */
[data-baseweb="tag"] {
    background-color: var(--status-good-bg) !important;
    border: 1px solid var(--status-good-border) !important;
    border-radius: 4px !important;
}
[data-baseweb="tag"] span {
    color: var(--status-good-text) !important;
    font-weight: 600 !important;
}
[data-baseweb="tag"] svg,
[data-baseweb="tag"] [role="presentation"] {
    color: var(--status-good-text) !important;
}

/* Date input */
.stDateInput input {
    color: var(--text-primary) !important;
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 4px !important;
}

/* Tabs */
[data-testid="stTabs"] button[role="tab"] {
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border-bottom: 3px solid transparent !important;
    padding: 8px 16px !important;
}
[data-testid="stTabs"] button[role="tab"]:hover {
    color: var(--primary) !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: var(--primary) !important;
    border-bottom: 3px solid var(--primary) !important;
    font-weight: 700 !important;
}

/* Expander */
[data-testid="stExpander"] {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: 4px !important;
}
[data-testid="stExpander"] summary {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}
[data-testid="stExpander"] summary:hover {
    color: var(--primary) !important;
}
[data-testid="stExpander"] summary svg {
    color: var(--primary) !important;
}

/* Streamlit Metrics */
[data-testid="stMetric"] {
    background: none;
    border: none;
    padding: 0;
}
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 24px !important;
    font-weight: 700 !important;
}

/* Alerts */
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p,
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] div {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}

/* Sidebar Accessibility */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-default) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span {
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] label {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────

def _get(path):
    try:
        with urllib.request.urlopen(API + path, timeout=10) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("detail", e.reason)
        except Exception:
            detail = e.reason
        return None, f"Server returned {e.code}: {detail}"
    except Exception as e:
        return None, str(e)


def _post(path, data=None):
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(
        API + path, data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("detail", e.reason)
        except Exception:
            detail = e.reason
        return None, f"Server returned {e.code}: {detail}"
    except Exception as e:
        return None, str(e)


def _delete(path):
    req = urllib.request.Request(API + path, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return True, None
    except urllib.error.HTTPError as e:
        return False, f"Server returned {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def _backend_ok():
    d, e = _get("/health")
    return e is None and d and d.get("status") == "ok"


# ── Render helpers ────────────────────────────────────────────────────────────

def _section(label):
    st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)


def _info_box(text, variant=""):
    cls = f"info-box {variant}".strip()
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def _data_row(param, value):
    st.markdown(
        f'<div class="data-row"><span class="param">{param}</span>'
        f'<span class="val">{value}</span></div>',
        unsafe_allow_html=True
    )


def _status_pill(status):
    cls = {"Good": "pill-good", "Moderate": "pill-mod", "Low": "pill-low",
           "Excellent": "pill-good", "High": "pill-low",
           "Positive": "pill-good", "Neutral": "pill-mod"}.get(status, "pill-mod")
    symbol = {
        "Good": "✓ ", "Excellent": "✓ ", "Positive": "✓ ",
        "Moderate": "● ", "Neutral": "● ",
        "Low": "▲ ", "High": "▲ "
    }.get(status, "")
    return f'<span class="{cls}">{symbol}{status}</span>'


def _bar(label, score, status, right=""):
    fill = {"Good": "sb-good", "Moderate": "sb-mod", "Low": "sb-low",
            "Excellent": "sb-good"}.get(status, "sb-mod")
    symbol = {
        "Good": "✓ ", "Excellent": "✓ ", "Positive": "✓ ",
        "Moderate": "● ", "Neutral": "● ",
        "Low": "▲ ", "High": "▲ "
    }.get(status, "")
    right_txt = right or status
    display_right = f"{symbol}{right_txt}" if not right_txt.startswith(("✓", "●", "▲")) else right_txt
    st.markdown(f"""
    <div class="score-bar-wrap">
      <div class="score-bar-label"><span>{label}</span><span>{display_right}</span></div>
      <div class="score-bar-track">
        <div class="{fill}" style="width:{min(score,100):.0f}%"></div>
      </div>
    </div>""", unsafe_allow_html=True)


def _score_status(s):
    return "Good" if s >= 70 else ("Moderate" if s >= 45 else "Low")


# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _load_crops():
    data, _ = _get("/crops")
    return data or []


@st.cache_data(ttl=300)
def _load_fertilizers():
    data, _ = _get("/fertilizers")
    return data or []


# ── Season helpers ────────────────────────────────────────────────────────────

def _season_label(season_type, year):
    if season_type == "Kharif":
        return f"Kharif {year}  (June–October {year})"
    if season_type == "Rabi":
        return f"Rabi {year}–{year+1}  (November {year}–March {year+1})"
    if season_type == "Zaid":
        return f"Zaid {year}  (March–June {year})"
    return f"{season_type} {year}"


# ── Step nav ──────────────────────────────────────────────────────────────────

STEPS = [
    "1. Select Field",
    "2. Farm Details",
    "3. Crop History",
    "4. Problems & Inputs",
    "5. Soil Data",
    "6. Analysis",
    "7. Recommendation",
]

def _render_nav(current_idx):
    items = ""
    for i, s in enumerate(STEPS):
        css = "active" if i == current_idx else ("done" if i < current_idx else "")
        items += f'<div class="step-item {css}">{s}</div>'
    st.markdown(f'<div class="step-nav">{items}</div>', unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────

def _ss(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


_ss("step", 0)
_ss("field_id", None)
_ss("field_data", None)
_ss("history_entries", [])   # list of dicts built on step 3
_ss("problems_entries", [])  # list of dicts built on step 4
_ss("fert_entries", [])      # list of dicts built on step 4
_ss("analysis", None)
_ss("opt", None)
_ss("lat", 20.5937)
_ss("lon", 78.9629)

step = st.session_state["step"]


# ── App header ────────────────────────────────────────────────────────────────
col_hdr, col_status = st.columns([6, 1])
with col_hdr:
    st.markdown(
        f'<div style="font-size:20px;font-weight:700;color:{COLOR_TEXT_PRIMARY};margin-bottom:2px">'
        'Soil & Crop Planner</div>'
        f'<div style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin-bottom:12px">'
        'Field assessment and multi-season crop planning</div>',
        unsafe_allow_html=True,
    )
with col_status:
    if _backend_ok():
        st.markdown(
            f'<div style="font-size:12px;font-weight:600;color:{COLOR_STATUS_GOOD_TEXT};text-align:right;padding-top:8px">'
            '✓ Backend connected</div>', unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div style="font-size:12px;font-weight:600;color:{COLOR_STATUS_LOW_TEXT};text-align:right;padding-top:8px">'
            f'▲ Backend offline<br><code style="color:{COLOR_TEXT_PRIMARY};background:#FDE8E8;">python run.py</code></div>',
            unsafe_allow_html=True
        )

_render_nav(step)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 0 — SELECT FIELD ON MAP
# ══════════════════════════════════════════════════════════════════════════════

if step == 0:
    st.markdown("### Select your agricultural field")
    st.markdown(
        '<div class="step-desc">'
        'Click anywhere on the map to place your field location, then confirm below.</div>',
        unsafe_allow_html=True,
    )

    col_map, col_info = st.columns([2, 1], gap="large")

    with col_map:
        # Build folium map centred on last known location
        m = folium.Map(
            location=[st.session_state["lat"], st.session_state["lon"]],
            zoom_start=10,
            tiles="OpenStreetMap",
        )
        # Existing marker
        folium.Marker(
            [st.session_state["lat"], st.session_state["lon"]],
            tooltip="Selected location",
            icon=folium.Icon(color="darkgreen", icon="leaf", prefix="fa"),
        ).add_to(m)

        map_data = st_folium(m, height=420, width=None, key="field_map",
                             returned_objects=["last_clicked"])

        # Capture click
        if map_data and map_data.get("last_clicked"):
            st.session_state["lat"] = map_data["last_clicked"]["lat"]
            st.session_state["lon"] = map_data["last_clicked"]["lng"]
            st.rerun()

    with col_info:
        _section("Selected Location")
        _data_row("Latitude",  f"{st.session_state['lat']:.4f}")
        _data_row("Longitude", f"{st.session_state['lon']:.4f}")

        st.markdown('<hr>', unsafe_allow_html=True)
        _section("Field Area")
        area_ha = st.number_input(
            "Estimated field area (hectares)", min_value=0.1,
            max_value=1000.0, value=2.0, step=0.5,
            label_visibility="collapsed",
        )
        st.markdown(
            f'<div style="font-size:12px;font-weight:500;color:{COLOR_TEXT_SECONDARY};margin-top:-8px">'
            'Estimated field area (ha)</div>', unsafe_allow_html=True
        )

        st.markdown('<hr>', unsafe_allow_html=True)
        _info_box(
            "Click the map to set your field location, then click "
            "<strong>Use This Location</strong> to continue.",
            "info",
        )

        if st.button("Use This Location", use_container_width=True):
            # Find or create field
            payload = {
                "latitude": st.session_state["lat"],
                "longitude": st.session_state["lon"],
                "area_ha": area_ha,
            }
            result, err = _post("/fields/find-or-create", payload)
            if err:
                st.error(f"Could not register field: {err}")
            else:
                st.session_state["field_id"] = result["id"]
                st.session_state["field_data"] = result
                st.session_state["step"] = 1
                st.rerun()

    st.markdown("""
    <div class="disclaimer">
      Location data is used for field registration only.
      No personal data is collected or transmitted.
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — FARM DETAILS
# ══════════════════════════════════════════════════════════════════════════════

elif step == 1:
    field_id = st.session_state["field_id"]
    f = st.session_state["field_data"] or {}

    st.markdown("### Farm and field information")
    st.markdown(
        '<div class="step-desc">'
        'Confirm or update the basic details for this field.</div>',
        unsafe_allow_html=True,
    )

    with st.form("farm_details"):
        col1, col2 = st.columns(2)
        farm_name = col1.text_input("Farm / farmer name (optional)",
                                     value=f.get("farm_name") or "")
        field_name = col2.text_input("Field name (optional)",
                                      value=f.get("name") or "")

        col3, col4 = st.columns(2)
        area_ha = col3.number_input("Field area (ha)", min_value=0.1,
                                     value=float(f.get("area_ha") or 2.0), step=0.5)
        irrigation = col4.selectbox(
            "Irrigation type",
            ["Rainfed", "Partial", "Irrigated"],
            index=["Rainfed", "Partial", "Irrigated"].index(
                f.get("irrigation_type") or "Partial"
            ),
        )

        col5, col6 = st.columns(2)
        farming_type = col5.selectbox(
            "Farming type",
            ["Conventional", "Organic", "Mixed"],
            index=0,
        )
        soil_type_known = col6.selectbox(
            "Soil type (if known)",
            ["Not sure", "Loam", "Clay Loam", "Sandy Loam", "Clay", "Sandy", "Silt Loam"],
        )

        current_crop = st.text_input("Current / most recent crop",
                                      value=f.get("current_crop") or "Rice")

        submitted = st.form_submit_button("Save & Continue", use_container_width=True)

    if submitted:
        patch_payload = {
            "area_ha": area_ha,
            "irrigation_type": irrigation,
            "farm_name": farm_name or None,
            "name": field_name or f"Field at {st.session_state['lat']:.3f}, {st.session_state['lon']:.3f}",
            "farming_type": farming_type,
            "soil_type": None if soil_type_known == "Not sure" else soil_type_known,
            "current_crop": current_crop or None,
        }
        # PATCH is not straightforward with urllib so we POST to the find-or-create endpoint
        # instead use a direct PATCH
        req = urllib.request.Request(
            f"{API}/fields/{field_id}",
            data=json.dumps(patch_payload).encode(),
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                updated = json.loads(r.read())
            st.session_state["field_data"] = updated
        except Exception:
            pass  # non-critical — continue anyway
        st.session_state["step"] = 2
        st.rerun()

    col_back, _ = st.columns([1, 5])
    if col_back.button("Back"):
        st.session_state["step"] = 0
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — CROP HISTORY
# ══════════════════════════════════════════════════════════════════════════════

elif step == 2:
    field_id = st.session_state["field_id"]
    crops = _load_crops()
    crop_opts = {c["name"]: c["id"] for c in crops}
    crop_names = list(crop_opts.keys())

    st.markdown("### Previous crop history")
    st.markdown(
        '<div class="step-desc">'
        'Enter the crops grown on this field in recent seasons, most recent last.</div>',
        unsafe_allow_html=True,
    )

    SEASON_TYPES = ["Kharif", "Rabi", "Zaid"]
    current_year = datetime.now().year

    # Add a season row
    with st.expander("Add a previous crop season", expanded=True):
        c1, c2, c3 = st.columns(3)
        s_type = c1.selectbox("Season", SEASON_TYPES, key="hist_stype")
        s_year = c2.number_input("Year", min_value=2010, max_value=current_year,
                                   value=current_year - 1, step=1, key="hist_year")
        s_crop = c3.selectbox("Crop grown", crop_names, key="hist_crop")

        c4, c5, c6 = st.columns(3)
        prod_qty = c4.number_input("Production quantity", min_value=0.0,
                                     value=0.0, step=0.5, key="hist_qty")
        prod_unit = c5.selectbox("Unit", ["tonnes", "quintal", "kg"],
                                   key="hist_unit")
        cult_area = c6.number_input("Cultivated area (ha)", min_value=0.1,
                                      value=float(st.session_state["field_data"].get("area_ha", 2.0) or 2.0),
                                      step=0.5, key="hist_area")

        c7, c8 = st.columns(2)
        sow_date = c7.date_input("Sowing date (approx)",
                                   value=date(s_year, 6, 15) if s_type == "Kharif"
                                   else (date(s_year, 11, 1) if s_type == "Rabi"
                                   else date(s_year, 3, 15)),
                                   key="hist_sow")
        harv_date = c8.date_input("Harvest date (approx)",
                                    value=date(s_year, 10, 20) if s_type == "Kharif"
                                    else (date(s_year + 1 if s_type == "Rabi" else s_year, 3, 15)
                                    if s_type == "Rabi" else date(s_year, 6, 10)),
                                    key="hist_harv")

        if st.button("Add season", use_container_width=True):
            # Auto yield
            qty_t = prod_qty
            if prod_unit == "quintal":
                qty_t = prod_qty / 10.0
            elif prod_unit == "kg":
                qty_t = prod_qty / 1000.0
            yld = round(qty_t / cult_area, 3) if (qty_t > 0 and cult_area > 0) else None

            season_label = _season_label(s_type, s_year)
            entry = {
                "season_name": season_label,
                "season_type": s_type,
                "year": s_year,
                "crop_name": s_crop,
                "crop_id": crop_opts[s_crop],
                "production_qty": prod_qty if prod_qty > 0 else None,
                "production_unit": prod_unit,
                "cultivated_area_ha": cult_area,
                "yield_t_ha": yld,
                "sowing_date": str(sow_date),
                "harvest_date": str(harv_date),
                "duration_days": (harv_date - sow_date).days,
            }
            st.session_state["history_entries"].append(entry)
            st.rerun()

    # Show entered history
    entries = st.session_state["history_entries"]
    if entries:
        _section("Crop history entered")
        rows_html = "".join(
            f"<tr><td>{i+1}</td>"
            f"<td>{e['season_name']}</td>"
            f"<td style='font-weight:600;color:{COLOR_TEXT_PRIMARY}'>{e['crop_name']}</td>"
            f"<td>{e.get('yield_t_ha') or '—'} t/ha</td>"
            f"<td>{e.get('cultivated_area_ha') or '—'} ha</td></tr>"
            for i, e in enumerate(entries)
        )
        st.markdown(f"""
        <table class="report-table">
          <thead><tr><th>#</th><th>Season</th><th>Crop</th><th>Yield</th><th>Area</th></tr></thead>
          <tbody>{rows_html}</tbody>
        </table>""", unsafe_allow_html=True)
        if st.button("Clear all history", type="secondary"):
            st.session_state["history_entries"] = []
            st.rerun()
    else:
        _info_box(
            "No crop history entered yet. You can continue without it, "
            "but rotation recommendations will be less accurate.",
            "info",
        )

    st.markdown('<hr>', unsafe_allow_html=True)
    col_back, _, col_next = st.columns([1, 4, 1])
    if col_back.button("Back"):
        st.session_state["step"] = 1
        st.rerun()
    if col_next.button("Continue"):
        st.session_state["step"] = 3
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — PROBLEMS & FERTILIZER INPUTS
# ══════════════════════════════════════════════════════════════════════════════

elif step == 3:
    from app.data.crop_data import PROBLEM_TYPES

    st.markdown("### Problems faced and fertilizer inputs")

    tab_prob, tab_fert = st.tabs(["Problems faced in previous crop", "Fertilizer used"])

    with tab_prob:
        st.markdown(
            '<div class="step-desc">'
            'Select any problems experienced in the previous growing season.</div>',
            unsafe_allow_html=True,
        )
        problem_labels = [p["label"] for p in PROBLEM_TYPES]
        selected_labels = st.multiselect(
            "Problems", problem_labels, key="prob_select",
            label_visibility="collapsed",
        )
        prob_notes = st.text_area("Additional observations (optional)",
                                    height=80, key="prob_notes")

        if st.button("Add problems", key="btn_add_prob"):
            label_to_code = {p["label"]: p["code"] for p in PROBLEM_TYPES}
            for lbl in selected_labels:
                code = label_to_code.get(lbl, "other")
                st.session_state["problems_entries"].append({
                    "problem_code": code,
                    "problem_label": lbl,
                    "severity": "Moderate",
                    "season_name": None,
                    "notes": prob_notes or None,
                })
            st.rerun()

        if st.session_state["problems_entries"]:
            _section("Problems recorded")
            for p in st.session_state["problems_entries"]:
                st.markdown(
                    f'<div style="font-size:13px;font-weight:500;color:{COLOR_TEXT_PRIMARY};padding:3px 0">'
                    f'&bull;&nbsp;{p["problem_label"]}</div>',
                    unsafe_allow_html=True,
                )
            if st.button("Clear problems"):
                st.session_state["problems_entries"] = []
                st.rerun()
        else:
            _info_box("No problems recorded. Continue if none apply.", "info")

    with tab_fert:
        fertilizers = _load_fertilizers()
        fert_opts = {f["name"]: f["id"] for f in fertilizers}
        fert_names = list(fert_opts.keys())

        st.markdown(
            '<div class="step-desc">'
            'Select fertilizers applied in the previous season.</div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        fert_name  = c1.selectbox("Fertilizer", fert_names, key="fert_name")
        fert_qty   = c2.number_input("Quantity (kg/ha)", min_value=0.0,
                                       value=50.0, step=10.0, key="fert_qty")
        fert_seas  = c3.text_input("Season applied (e.g. Kharif 2024)",
                                     key="fert_seas")

        if st.button("Add fertilizer", key="btn_add_fert"):
            fid = fert_opts.get(fert_name)
            # Estimate cost
            fert_info = next((f for f in fertilizers if f["name"] == fert_name), {})
            cost_per_50kg = fert_info.get("cost_rs_per_50kg", 0) or 0
            total_cost = (fert_qty / 50.0) * cost_per_50kg * (
                st.session_state["field_data"].get("area_ha") or 1.0
            )
            st.session_state["fert_entries"].append({
                "fertilizer_id": fid,
                "fertilizer_name": fert_name,
                "quantity_kg_ha": fert_qty,
                "season_name": fert_seas or None,
                "total_cost_rs": round(total_cost, 0),
            })
            st.rerun()

        if st.session_state["fert_entries"]:
            _section("Fertilizers recorded")
            rows_html = "".join(
                f"<tr><td style='font-weight:600;color:{COLOR_TEXT_PRIMARY}'>{e['fertilizer_name']}</td>"
                f"<td>{e['quantity_kg_ha']} kg/ha</td>"
                f"<td>{e.get('season_name') or '—'}</td>"
                f"<td>Rs {e.get('total_cost_rs') or '—'}</td></tr>"
                for e in st.session_state["fert_entries"]
            )
            st.markdown(f"""
            <table class="report-table">
              <thead><tr><th>Fertilizer</th><th>Qty</th><th>Season</th><th>Est. cost</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>""", unsafe_allow_html=True)
            if st.button("Clear fertilizers"):
                st.session_state["fert_entries"] = []
                st.rerun()

    st.markdown('<hr>', unsafe_allow_html=True)
    col_back, _, col_next = st.columns([1, 4, 1])
    if col_back.button("Back"):
        st.session_state["step"] = 2
        st.rerun()
    if col_next.button("Continue"):
        st.session_state["step"] = 4
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — SOIL DATA
# ══════════════════════════════════════════════════════════════════════════════

elif step == 4:
    field_id = st.session_state["field_id"]
    f = st.session_state["field_data"] or {}

    # Load existing soil observations
    existing_soil, _ = _get(f"/fields/{field_id}/soil")
    obs = existing_soil[0] if existing_soil else None

    st.markdown("### Soil information")
    st.markdown(
        '<div class="step-desc">'
        'Enter the latest soil test results. Leave fields blank if not measured. '
        'SOC is stored as concentration (%) — not SOC stock.</div>',
        unsafe_allow_html=True,
    )

    with st.form("soil_form"):
        col1, col2, col3 = st.columns(3)
        ph      = col1.number_input("pH", min_value=0.0, max_value=14.0,
                                     value=float(obs["ph"] or 6.7) if obs else 6.7,
                                     step=0.1)
        soc_pct = col2.number_input("Organic carbon (SOC %)",
                                      min_value=0.0, max_value=100.0,
                                      value=float(obs["soc_pct"] or 0.62) if obs else 0.62,
                                      step=0.01)
        ec      = col3.number_input("EC (dS/m)",
                                      min_value=0.0,
                                      value=float(obs["ec"] or 0.8) if obs else 0.8,
                                      step=0.1)

        col4, col5, col6 = st.columns(3)
        n = col4.number_input("Nitrogen (g/kg)",
                               min_value=0.0,
                               value=float(obs["nitrogen"] or 0.10) if obs else 0.10,
                               step=0.01)
        p = col5.number_input("Phosphorus (mg/kg)",
                               min_value=0.0,
                               value=float(obs["phosphorus"] or 18.0) if obs else 18.0,
                               step=1.0)
        k = col6.number_input("Potassium (mg/kg)",
                               min_value=0.0,
                               value=float(obs["potassium"] or 85.0) if obs else 85.0,
                               step=5.0)

        col7, col8, col9 = st.columns(3)
        sand = col7.number_input("Sand %", min_value=0.0, max_value=100.0,
                                   value=float(obs["sand_pct"] or 40.0) if obs else 40.0,
                                   step=1.0)
        silt = col8.number_input("Silt %", min_value=0.0, max_value=100.0,
                                   value=float(obs["silt_pct"] or 35.0) if obs else 35.0,
                                   step=1.0)
        clay = col9.number_input("Clay %", min_value=0.0, max_value=100.0,
                                   value=float(obs["clay_pct"] or 25.0) if obs else 25.0,
                                   step=1.0)

        st.markdown('<hr>', unsafe_allow_html=True)
        _section("Climate (for this location)")
        cc1, cc2, cc3 = st.columns(3)
        temp_c  = cc1.number_input("Mean temperature (°C)", value=27.0, step=0.5)
        rain_mm = cc2.number_input("Seasonal rainfall (mm)", value=1050.0, step=50.0)
        dry_risk = cc3.selectbox("Dry-season risk", ["Low", "Moderate", "High"], index=1)

        submitted = st.form_submit_button("Save & Run Analysis", use_container_width=True)

    if submitted:
        # Save soil observation
        soil_payload = {
            "ph": ph, "soc_pct": soc_pct, "ec": ec,
            "nitrogen": n, "phosphorus": p, "potassium": k,
            "sand_pct": sand, "silt_pct": silt, "clay_pct": clay,
            "sample_date": str(date.today()),
        }
        _post(f"/fields/{field_id}/soil", soil_payload)

        # Save crop history (clear first to avoid duplicates)
        _delete(f"/fields/{field_id}/history")
        for i, entry in enumerate(st.session_state["history_entries"]):
            h_payload = {
                "season_order": i + 1,
                "season_name": entry["season_name"],
                "season_type": entry["season_type"],
                "year": entry["year"],
                "crop_id": entry["crop_id"],
                "sowing_date": entry.get("sowing_date"),
                "harvest_date": entry.get("harvest_date"),
                "duration_days": entry.get("duration_days"),
                "cultivated_area_ha": entry.get("cultivated_area_ha"),
                "production_qty": entry.get("production_qty"),
                "production_unit": entry.get("production_unit", "tonnes"),
                "yield_t_ha": entry.get("yield_t_ha"),
            }
            _post(f"/fields/{field_id}/history", h_payload)

        # Save problems
        _delete(f"/fields/{field_id}/problems")
        for prob in st.session_state["problems_entries"]:
            _post(f"/fields/{field_id}/problems", prob)

        # Save fertilizer usage
        _delete(f"/fields/{field_id}/fertilizers")
        for fert in st.session_state["fert_entries"]:
            _post(f"/fields/{field_id}/fertilizers", {
                "fertilizer_id": fert["fertilizer_id"],
                "season_name": fert.get("season_name"),
                "quantity_kg_ha": fert["quantity_kg_ha"],
                "total_cost_rs": fert.get("total_cost_rs"),
            })

        # Store climate for next steps
        st.session_state["climate"] = {
            "mean_temp_c": temp_c,
            "seasonal_rainfall_mm": rain_mm,
            "dry_season_risk": dry_risk,
            "heavy_rainfall_risk": "Low",
        }

        # Run analysis
        with st.spinner("Running field assessment..."):
            result, err = _post(
                f"/fields/{field_id}/analyze",
                st.session_state["climate"]
            )
        if err:
            st.error(f"Analysis failed: {err}")
        else:
            st.session_state["analysis"] = result
            st.session_state["step"] = 5
            st.rerun()

    col_back, _ = st.columns([1, 5])
    if col_back.button("Back"):
        st.session_state["step"] = 3
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — ANALYSIS RESULTS
# ══════════════════════════════════════════════════════════════════════════════

elif step == 5:
    data = st.session_state.get("analysis")
    if not data:
        _info_box("No analysis available. Please complete the previous steps.", "warn")
        st.stop()

    soil   = data.get("soil_assessment", {})
    deg    = data.get("degradation", {})
    suits  = data.get("crop_suitability", [])
    history = data.get("history_summary", [])
    problems = data.get("problem_summary", [])

    st.markdown("### Field assessment")

    # Summary sentence
    rl = soil.get("risk_level", "Unknown")
    drivers = deg.get("main_drivers", [])
    driver_txt = " and ".join(d.lower() for d in drivers[:2]) if drivers else "no major issues identified"
    _info_box(
        f"Soil condition is <strong>{rl.lower()}</strong>. "
        f"{driver_txt.capitalize()}. "
        f"Soil health score: <strong>{soil.get('soil_health_score', 0):.0f}/100</strong>."
    )

    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        _section("Soil Condition")
        hs = soil.get("soil_health_score", 0)
        fill = "sb-good" if hs >= 70 else ("sb-mod" if hs >= 45 else "sb-low")
        st.markdown(f"""
        <div style="margin-bottom:16px">
          <span style="font-size:28px;font-weight:700;color:{COLOR_TEXT_PRIMARY}">{hs:.0f}</span>
          <span style="font-size:14px;font-weight:600;color:{COLOR_TEXT_SECONDARY}"> / 100</span>
          <div style="font-size:13px;font-weight:600;color:{COLOR_TEXT_SECONDARY};margin-top:2px">{rl} condition</div>
        </div>
        <div class="score-bar-track" style="height:8px;margin-bottom:16px">
          <div class="{fill}" style="width:{hs:.0f}%;height:8px;border-radius:2px"></div>
        </div>""", unsafe_allow_html=True)

        for param, label in [
            ("ph", "pH"), ("soc", "Organic carbon"),
            ("nitrogen", "Nitrogen"), ("phosphorus", "Phosphorus"),
            ("potassium", "Potassium"), ("ec", "EC / Salinity"),
        ]:
            ind = soil.get(param, {})
            val = ind.get("value")
            val_str = f" ({val})" if val is not None else ""
            _bar(f"{label}{val_str}", ind.get("score", 50),
                 ind.get("status", "Unknown"), ind.get("status", "Unknown"))

    with col_right:
        _section("Degradation Risk")
        ds  = deg.get("overall_degradation_score", 0)
        drl = deg.get("risk_level", "Unknown")
        dfill = "sb-low" if ds >= 60 else ("sb-mod" if ds >= 35 else "sb-good")
        st.markdown(f"""
        <div style="margin-bottom:16px">
          <span style="font-size:28px;font-weight:700;color:{COLOR_TEXT_PRIMARY}">{ds:.0f}</span>
          <span style="font-size:14px;font-weight:600;color:{COLOR_TEXT_SECONDARY}"> / 100</span>
          <div style="font-size:13px;font-weight:600;color:{COLOR_TEXT_SECONDARY};margin-top:2px">{drl} degradation risk</div>
        </div>
        <div class="score-bar-track" style="height:8px;margin-bottom:16px">
          <div class="{dfill}" style="width:{ds:.0f}%;height:8px;border-radius:2px"></div>
        </div>""", unsafe_allow_html=True)

        for label, key in [
            ("Organic carbon", "soc_risk"), ("Nutrients (N/P/K)", "nutrient_risk"),
            ("Salinity", "water_risk"), ("Vegetation cover", "vegetation_risk"),
            ("Crop history", "history_risk"),
        ]:
            val = deg.get(key, "—")
            sc = "status-good" if val == "Low" else ("status-mod" if val == "Moderate" else "status-low")
            icon = "✓ " if val == "Low" else ("● " if val == "Moderate" else "▲ ")
            st.markdown(
                f'<div class="data-row"><span class="param">{label}</span>'
                f'<span class="{sc}">{icon}{val}</span></div>',
                unsafe_allow_html=True,
            )

        if drivers:
            st.markdown('<hr>', unsafe_allow_html=True)
            _section("Main contributing factors")
            for d in drivers:
                st.markdown(
                    f'<div style="font-size:13px;font-weight:500;color:{COLOR_TEXT_PRIMARY};padding:3px 0">&bull;&nbsp;{d}</div>',
                    unsafe_allow_html=True,
                )

    # Crop history
    if history:
        st.markdown('<hr>', unsafe_allow_html=True)
        _section("Crop history")
        cols = st.columns(len(history))
        for i, (c, crop) in enumerate(zip(cols, history)):
            c.metric(f"Season {i+1}", crop)

    # Problems
    if problems:
        st.markdown('<hr>', unsafe_allow_html=True)
        _section("Reported problems")
        prob_pills = "".join(
            f'<span class="pill-mod" style="margin-right:6px;margin-bottom:6px;display:inline-block">'
            f'{p["label"]}</span>'
            for p in problems if p.get("label")
        )
        st.markdown(prob_pills, unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)
    col_back, _, col_next = st.columns([1, 4, 1])
    if col_back.button("Back"):
        st.session_state["step"] = 4
        st.rerun()
    if col_next.button("View Recommendations"):
        # Trigger optimization
        field_id = st.session_state["field_id"]
        f = st.session_state["field_data"] or {}
        with st.spinner("Generating crop rotation plan..."):
            opt_payload = {
                **st.session_state.get("climate", {}),
                "horizon": 4,
            }
            opt_result, opt_err = _post(f"/fields/{field_id}/optimize", opt_payload)
        if opt_err:
            st.warning(f"Rotation optimisation failed: {opt_err}")
        else:
            st.session_state["opt"] = opt_result
        st.session_state["step"] = 6
        st.rerun()

    st.markdown("""
    <div class="disclaimer">
      Rule-based assessment prototype. Requires regional calibration and expert validation.
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — RECOMMENDATION & FINANCIAL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

elif step == 6:
    data = st.session_state.get("analysis")
    opt  = st.session_state.get("opt")
    field_id = st.session_state["field_id"]
    f = st.session_state["field_data"] or {}

    if not data:
        _info_box("No analysis available. Please go back and run the analysis.", "warn")
        st.stop()

    suits   = data.get("crop_suitability", [])
    problems = data.get("problem_summary", [])

    tab_rec, tab_rot, tab_fin, tab_report = st.tabs([
        "Crop Recommendation",
        "Rotation Plan",
        "Financial Analysis",
        "Final Report",
    ])

    # ── Tab 1: Crop Recommendation ────────────────────────────────────────────
    with tab_rec:
        st.markdown("#### Recommended crops")
        st.markdown(
            '<div class="step-desc">'
            'Top candidates based on soil, climate, water, rotation, and economic factors.</div>',
            unsafe_allow_html=True,
        )

        top3 = suits[:3]

        for i, s in enumerate(top3):
            is_top = (i == 0)
            name = s["crop_name"]
            score = s["final_score"]
            level = s["suitability_level"]

            # Build why-it-fits from scores
            fit_pts, limit_pts = [], []
            if s["soil_score"]     >= 70: fit_pts.append("Good soil compatibility")
            elif s["soil_score"]   <  50: limit_pts.append("Sub-optimal soil conditions")
            if s["climate_score"]  >= 70: fit_pts.append("Suitable temperature range")
            if s["water_score"]    >= 70: fit_pts.append("Water requirement matched")
            elif s["water_score"]  <  50: limit_pts.append("Water availability may be limiting")
            if s["rotation_score"] >= 80: fit_pts.append("Good rotation break from recent history")
            elif s["rotation_score"] < 50: limit_pts.append("Limited rotation benefit")
            if s["economic_score"] >= 70: fit_pts.append("Favourable estimated margin")

            # Fetch economics for this crop
            crops_list = _load_crops()
            crop_info = next((c for c in crops_list if c["name"] == name), {})

            # Get sowing/harvest window from crop data
            sow_win = crop_info.get("sowing_window") or "—"
            harv_win = crop_info.get("harvest_window") or "—"
            dur = crop_info.get("duration_days") or "—"

            st.markdown(f"""
            <div class="rec-card {'alt' if i > 0 else ''}">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <div style="font-size:18px;font-weight:700;color:{COLOR_TEXT_PRIMARY}">
                  {'Recommended: ' if is_top else f'{i+1}. '}{name}
                </div>
                <div>{_status_pill(level)}&nbsp;
                  <span style="font-size:14px;font-weight:700;color:{COLOR_TEXT_PRIMARY}">{score:.0f}/100</span>
                </div>
              </div>
              <div style="margin-top:10px;display:flex;gap:24px;font-size:13px;font-weight:600;color:{COLOR_TEXT_SECONDARY}">
                <span>Sowing: {sow_win}</span>
                <span>Harvest: {harv_win}</span>
                <span>Duration: ~{dur} days</span>
              </div>
              <div style="margin-top:10px">
                {''.join(f'<div style="font-size:13px;font-weight:500;color:{COLOR_TEXT_PRIMARY};padding:2px 0">&bull;&nbsp;{pt}</div>' for pt in fit_pts)}
              </div>
              {'<div style="margin-top:8px;font-size:13px;font-weight:600;color:' + COLOR_STATUS_MOD_TEXT + '">' + ''.join(f'<div>▲&nbsp;{pt}</div>' for pt in limit_pts) + '</div>' if limit_pts else ''}
            </div>""", unsafe_allow_html=True)

        # Full suitability table
        with st.expander("All crops — full suitability table"):
            rows_html = ""
            for s in suits:
                pill = _status_pill(s["suitability_level"])
                rows_html += (
                    f"<tr><td style='font-weight:600;color:{COLOR_TEXT_PRIMARY}'>{s['crop_name']}</td>"
                    f"<td><strong style='color:{COLOR_TEXT_PRIMARY}'>{s['final_score']:.0f}</strong>&nbsp;{pill}</td>"
                    f"<td>{s['soil_score']:.0f}</td><td>{s['climate_score']:.0f}</td>"
                    f"<td>{s['water_score']:.0f}</td><td>{s['rotation_score']:.0f}</td>"
                    f"<td>{s['economic_score']:.0f}</td></tr>"
                )
            st.markdown(f"""
            <table class="report-table">
              <thead><tr><th>Crop</th><th>Overall</th><th>Soil</th>
                <th>Climate</th><th>Water</th><th>Rotation</th><th>Economic</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>""", unsafe_allow_html=True)

    # ── Tab 2: Rotation Plan ──────────────────────────────────────────────────
    with tab_rot:
        if not opt or not opt.get("rotation"):
            _info_box("Rotation plan not available.", "info")
        else:
            rotation = opt.get("rotation", [])
            status   = opt.get("status", "—")

            st.markdown(f"**Solver status:** {status}  &nbsp;|&nbsp;  "
                        f"**Seasons:** {len(rotation)}")
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

            # Timeline
            cols = st.columns(len(rotation))
            bg_list = ["#EAF2EB", "#FBF5EA", "#EAF2EB", "#EEF2F6",
                       "#EAF2EB", "#FBF5EA", "#EAF2EB", "#EEF2F6"]
            for i, (col, s) in enumerate(zip(cols, rotation)):
                with col:
                    bg = bg_list[i % len(bg_list)]
                    st.markdown(f"""
                    <div style="background:{bg};border:1.5px solid {COLOR_BORDER_DEFAULT};border-radius:4px;
                                padding:12px 10px;text-align:center">
                      <div style="font-size:11px;font-weight:700;color:{COLOR_TEXT_SECONDARY};text-transform:uppercase;
                                  letter-spacing:0.08em">Season {s['season']}</div>
                      <div style="font-size:16px;font-weight:700;color:{COLOR_PRIMARY};margin:6px 0">
                        {s['crop']}</div>
                      <div style="font-size:12px;font-weight:600;color:{COLOR_TEXT_PRIMARY}">
                        Score {s['suitability_score']:.0f}</div>
                      <div style="font-size:12px;font-weight:600;color:{COLOR_TEXT_SECONDARY};margin-top:2px">
                        Rs {s['expected_margin_rs_ha']:,.0f}/ha</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

            rows_html = "".join(
                f"<tr><td>Season {s['season']}</td>"
                f"<td style='font-weight:600;color:{COLOR_TEXT_PRIMARY}'>{s['crop']}</td>"
                f"<td>{s['suitability_score']:.0f}</td>"
                f"<td>Rs {s['expected_margin_rs_ha']:,.0f}</td></tr>"
                for s in rotation
            )
            st.markdown(f"""
            <table class="report-table">
              <thead><tr><th>Season</th><th>Crop</th><th>Suitability</th>
                         <th>Est. margin/ha</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>""", unsafe_allow_html=True)

            st.markdown('<hr>', unsafe_allow_html=True)
            _section("Why this rotation?")
            for s in rotation:
                exp = s.get("explanation", "")
                exp_clean = exp.split("Estimated net margin")[0].strip().rstrip(".")
                st.markdown(
                    f'<div style="font-size:13px;padding:5px 0;border-bottom:1px solid {COLOR_BORDER_DEFAULT}">'
                    f'<span style="font-weight:700;color:{COLOR_PRIMARY}">Season {s["season"]} — {s["crop"]}:</span>'
                    f'<span style="color:{COLOR_TEXT_PRIMARY}">&nbsp;{exp_clean}</span></div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<hr>', unsafe_allow_html=True)
            _section("Summary impacts")
            _data_row("Soil impact",   opt.get("soil_impact", "—"))
            _data_row("Water impact",  opt.get("water_impact", "—"))
            _data_row("Disease risk",  opt.get("disease_risk", "—"))
            _data_row("Total est. margin",
                      f"Rs {opt.get('total_expected_margin_rs', 0):,.0f} "
                      f"({f.get('area_ha', 1)} ha, {len(rotation)} seasons)")

    # ── Tab 3: Financial Analysis ─────────────────────────────────────────────
    with tab_fin:
        if not top3:
            _info_box("Run analysis first.", "info")
            st.stop()

        top_crop_name = top3[0]["crop_name"] if top3 else None
        area_ha = float(f.get("area_ha") or 1.0)

        # Fetch crop economics from backend
        crop_econ_data, _ = _post(
            f"/fields/{field_id}/analyze",
            st.session_state.get("climate", {})
        )

        # Find economic data for top crop
        all_crops = _load_crops()
        top_crop_info = next((c for c in all_crops if c.get("name") == top_crop_name), {})

        # We call the backend analyze to get fresh data including economics
        # Use in-memory crop catalogue for cost breakdown
        from app.data.crop_data import CROP_CATALOGUE as _CC
        top_cc = next((c for c in _CC if c["name"] == top_crop_name), None)

        st.markdown(f"#### Financial analysis — {top_crop_name}")
        st.markdown(
            '<div class="step-desc">'
            'All values are demonstration estimates. '
            'Actual costs and prices vary by region and season.</div>',
            unsafe_allow_html=True,
        )

        if top_cc:
            yield_t  = top_cc.get("expected_yield_t_ha", 0)
            price    = top_cc.get("price_rs_per_t", 0)
            rev_ha   = yield_t * price
            cost_ha  = sum([
                top_cc.get("seed_cost_rs_ha", 0) or 0,
                top_cc.get("fertilizer_cost_rs_ha", 0) or 0,
                top_cc.get("pesticide_cost_rs_ha", 0) or 0,
                top_cc.get("irrigation_cost_rs_ha", 0) or 0,
                top_cc.get("labor_cost_rs_ha", 0) or 0,
                top_cc.get("machinery_cost_rs_ha", 0) or 0,
                top_cc.get("other_cost_rs_ha", 0) or 0,
            ])
            margin_ha = rev_ha - cost_ha
            roi       = (margin_ha / cost_ha * 100) if cost_ha > 0 else 0

            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                <div class="fin-card">
                  <div class="fc-label">Est. Investment</div>
                  <div class="fc-value">Rs {cost_ha * area_ha:,.0f}</div>
                  <div class="fc-sub">Rs {cost_ha:,.0f}/ha</div>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="fin-card">
                  <div class="fc-label">Est. Revenue</div>
                  <div class="fc-value">Rs {rev_ha * area_ha:,.0f}</div>
                  <div class="fc-sub">Rs {rev_ha:,.0f}/ha · {yield_t} t/ha</div>
                </div>""", unsafe_allow_html=True)
            with col3:
                profit_color = COLOR_STATUS_GOOD_TEXT if margin_ha > 0 else COLOR_STATUS_LOW_TEXT
                st.markdown(f"""
                <div class="fin-card">
                  <div class="fc-label">Est. Profit</div>
                  <div class="fc-value" style="color:{profit_color}">Rs {margin_ha * area_ha:,.0f}</div>
                  <div class="fc-sub">Rs {margin_ha:,.0f}/ha</div>
                </div>""", unsafe_allow_html=True)
            with col4:
                roi_color = COLOR_STATUS_GOOD_TEXT if roi > 0 else COLOR_STATUS_LOW_TEXT
                st.markdown(f"""
                <div class="fin-card">
                  <div class="fc-label">Est. ROI</div>
                  <div class="fc-value" style="color:{roi_color}">{roi:.1f}%</div>
                  <div class="fc-sub">Return on investment</div>
                </div>""", unsafe_allow_html=True)

            st.markdown('<hr>', unsafe_allow_html=True)

            col_left, col_right = st.columns(2, gap="large")

            with col_left:
                _section("Investment breakdown (per hectare)")
                items = [
                    ("Seed",                top_cc.get("seed_cost_rs_ha") or 0),
                    ("Fertilizer",          top_cc.get("fertilizer_cost_rs_ha") or 0),
                    ("Crop protection",     top_cc.get("pesticide_cost_rs_ha") or 0),
                    ("Irrigation",          top_cc.get("irrigation_cost_rs_ha") or 0),
                    ("Labor",               top_cc.get("labor_cost_rs_ha") or 0),
                    ("Machinery",           top_cc.get("machinery_cost_rs_ha") or 0),
                    ("Other",               top_cc.get("other_cost_rs_ha") or 0),
                ]
                rows_html = "".join(
                    f"<tr><td>{label}</td><td style='text-align:right'>Rs {val:,.0f}</td></tr>"
                    for label, val in items if val > 0
                )
                rows_html += f"<tr style='font-weight:700;border-top:1.5px solid {COLOR_BORDER_STRONG};color:{COLOR_TEXT_PRIMARY}'><td>Total</td><td style='text-align:right'>Rs {cost_ha:,.0f}</td></tr>"
                st.markdown(f"""
                <table class="report-table">
                  <thead><tr><th>Cost item</th><th style="text-align:right">Rs/ha</th></tr></thead>
                  <tbody>{rows_html}</tbody>
                </table>""", unsafe_allow_html=True)

            with col_right:
                _section("Sensitivity analysis")
                st.markdown(
                    f'<div style="font-size:12px;font-weight:500;color:{COLOR_TEXT_SECONDARY};margin-bottom:8px">'
                    'Conservative: 75% yield, 85% price &nbsp;|&nbsp; '
                    'Favorable: 120% yield, 110% price</div>',
                    unsafe_allow_html=True,
                )
                scenarios = {
                    "Conservative": (0.75, 0.85),
                    "Expected":     (1.00, 1.00),
                    "Favorable":    (1.20, 1.10),
                }
                rows_html = ""
                for sc_name, (ym, pm) in scenarios.items():
                    sc_rev  = yield_t * ym * price * pm
                    sc_prof = (sc_rev - cost_ha) * area_ha
                    sc_roi  = (sc_rev - cost_ha) / cost_ha * 100 if cost_ha > 0 else 0
                    col_style = (f"color:{COLOR_STATUS_GOOD_TEXT}" if sc_prof > 0 else f"color:{COLOR_STATUS_LOW_TEXT}")
                    rows_html += (
                        f"<tr><td>{sc_name}</td>"
                        f"<td>Rs {sc_rev*area_ha:,.0f}</td>"
                        f"<td style='{col_style};font-weight:700'>Rs {sc_prof:,.0f}</td>"
                        f"<td>{sc_roi:.1f}%</td></tr>"
                    )
                st.markdown(f"""
                <table class="report-table">
                  <thead><tr><th>Scenario</th><th>Revenue</th>
                    <th>Profit ({area_ha} ha)</th><th>ROI</th></tr></thead>
                  <tbody>{rows_html}</tbody>
                </table>""", unsafe_allow_html=True)

                st.markdown('<hr>', unsafe_allow_html=True)
                _section("Resource requirements")
                dur = top_crop_info.get("duration_days") or top_cc.get("duration_days", "—")
                sow = top_cc.get("sowing_window", "—")
                harv = top_cc.get("harvest_window", "—")
                prot = top_cc.get("crop_protection_level", "—")
                labor = top_cc.get("labor_level", "—")
                _data_row("Expected duration", f"~{dur} days")
                _data_row("Sowing window",   sow)
                _data_row("Harvest window",  harv)
                _data_row("Crop protection", prot)
                _data_row("Labor requirement", labor)

        else:
            _info_box("Economic data not available for this crop.", "info")

        # Cautions
        st.markdown('<hr>', unsafe_allow_html=True)
        _section("Cautions before planting")

        cautions = [
            "Economic values are demonstration estimates based on indicative figures. "
            "Actual costs and prices vary significantly by region and season.",
            "Actual yield depends on weather, soil management, seed quality and pest pressure.",
        ]
        if problems:
            water_probs = [p for p in problems if p.get("code") == "water_shortage"]
            if water_probs:
                cautions.append(
                    "Water shortage was reported as a previous problem. "
                    "Verify water availability before committing to this crop."
                )
        if top_cc and top_cc.get("water_need") == "High":
            cautions.append(
                f"{top_crop_name} has high water demand. Ensure adequate irrigation "
                "or sufficient seasonal rainfall before planting."
            )
        cautions.append(
            "Fertilizer recommendations should be validated with local soil-test guidance "
            "and agronomist advice."
        )
        for c in cautions:
            st.markdown(
                f'<div style="font-size:13px;font-weight:600;color:{COLOR_STATUS_MOD_TEXT};padding:5px 0;'
                f'border-bottom:1px solid {COLOR_BORDER_DEFAULT}">▲&nbsp;{c}</div>',
                unsafe_allow_html=True,
            )

    # ── Tab 4: Final Report ───────────────────────────────────────────────────
    with tab_report:
        soil   = data.get("soil_assessment", {})
        deg    = data.get("degradation", {})
        history = data.get("history_summary", [])

        st.markdown("#### Field assessment report")

        fhdr = f.get("name") or f"Field {field_id}"
        _data_row("Field",           fhdr)
        _data_row("Location",        f"{st.session_state['lat']:.4f}, {st.session_state['lon']:.4f}")
        _data_row("Area",            f"{f.get('area_ha', '—')} ha")
        _data_row("Irrigation",      f.get("irrigation_type") or "—")
        _data_row("Soil condition",  f"{soil.get('soil_health_score', 0):.0f}/100 ({soil.get('risk_level', '—')})")
        _data_row("Degradation risk", f"{deg.get('overall_degradation_score', 0):.0f}/100 ({deg.get('risk_level', '—')})")

        if top3:
            _data_row("Recommended crop", top3[0]["crop_name"])
        if opt and opt.get("rotation"):
            seq = " → ".join(s["crop"] for s in opt["rotation"])
            _data_row("Rotation plan", seq)
            _data_row("Est. total margin",
                      f"Rs {opt.get('total_expected_margin_rs', 0):,.0f}")

        st.markdown('<hr>', unsafe_allow_html=True)
        _section("Key observations")
        drivers = deg.get("main_drivers", [])
        obs_pts = []
        if any("potassium" in d.lower() for d in drivers):
            obs_pts.append("Low potassium is the main nutrient limitation. Potassium supplementation recommended.")
        if any("rice" in d.lower() or "repeated" in d.lower() for d in drivers):
            obs_pts.append("Repeated cereal cultivation increases disease and nutrient-depletion risk.")
        if top3 and top3[0]["crop_name"] in ("Chickpea", "Soybean", "Groundnut", "Pigeon Pea"):
            obs_pts.append(f"{top3[0]['crop_name']} is a legume — it provides a rotation break and potential nitrogen benefit.")
        obs_pts.append("All economic values are demonstration estimates requiring local validation.")
        for o in obs_pts:
            st.markdown(
                f'<div style="font-size:13px;font-weight:500;color:{COLOR_TEXT_PRIMARY};padding:5px 0;border-bottom:1px solid {COLOR_BORDER_DEFAULT}">'
                f'&bull;&nbsp;{o}</div>',
                unsafe_allow_html=True,
            )

        # Downloadable report as JSON
        st.markdown('<hr>', unsafe_allow_html=True)
        report_dict = {
            "field": f,
            "location": {"lat": st.session_state["lat"], "lon": st.session_state["lon"]},
            "soil_assessment": soil,
            "degradation": deg,
            "crop_history": history,
            "top_recommendations": [{
                "crop": s["crop_name"], "score": s["final_score"],
                "level": s["suitability_level"]
            } for s in top3],
            "rotation": opt.get("rotation") if opt else None,
            "total_margin_rs": opt.get("total_expected_margin_rs") if opt else None,
            "disclaimer": (
                "Decision-support prototype. All outputs require regional calibration "
                "and agronomist validation before any operational use."
            ),
        }
        st.download_button(
            label="Download report (JSON)",
            data=json.dumps(report_dict, indent=2, default=str),
            file_name=f"soilcrop_report_field{field_id}.json",
            mime="application/json",
        )

    st.markdown('<hr>', unsafe_allow_html=True)
    col_back, _, col_restart = st.columns([1, 4, 1])
    if col_back.button("Back to Analysis"):
        st.session_state["step"] = 5
        st.rerun()
    if col_restart.button("New Field"):
        for k in ["step","field_id","field_data","history_entries",
                  "problems_entries","fert_entries","analysis","opt","climate"]:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state["step"] = 0
        st.rerun()

    st.markdown("""
    <div class="disclaimer">
      Decision-support prototype. Agronomic thresholds and economic values require
      local calibration and validation before field deployment.
      Not a substitute for qualified agronomist advice.
    </div>""", unsafe_allow_html=True)
