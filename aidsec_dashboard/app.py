"""AidSec Lead Management Dashboard"""
import streamlit as st
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

st.set_page_config(page_title="AidSec Lead Dashboard", page_icon="🛡️", layout="wide")


# ── Authentication gate ───────────────────────────────────────────
def _check_auth():
    app_pw = os.getenv("APP_PASSWORD", "")
    if not app_pw:
        return True

    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        '<div style="max-width:400px;margin:80px auto;text-align:center;">'
        '<div style="font-family:JetBrains Mono,monospace;font-size:1.8rem;font-weight:700;margin-bottom:4px;">'
        '<span style="color:#00d4aa;">Aid</span><span style="color:#e8eaed;">Sec</span></div>'
        '<div style="color:#b8bec6;font-size:0.85rem;margin-bottom:32px;">Lead Management Dashboard</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        pw = st.text_input("Passwort", type="password", placeholder="Team-Passwort eingeben...")
        submitted = st.form_submit_button("Anmelden", type="primary")

    if submitted:
        if pw == app_pw:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Falsches Passwort.")
    return False


if not _check_auth():
    st.stop()

# ── Global Stylesheet ──────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --aidsec-teal: #00d4aa;
    --aidsec-teal-dim: #00d4aa33;
    --aidsec-amber: #f0a500;
    --aidsec-surface: #1a1f2e;
    --aidsec-border: #2a3040;
    --aidsec-bg: #0e1117;
    --aidsec-text: #e8eaed;
    --aidsec-text-dim: #b8bec6;
    --status-offen: #3498db;
    --status-pending: #f39c12;
    --status-gewonnen: #2ecc71;
    --status-verloren: #e74c3c;
}

html, body, [class*="st-"] {
    font-family: 'DM Sans', sans-serif !important;
    line-height: 1.5;
}

/* ── Metric cards ─────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--aidsec-surface);
    border: 1px solid var(--aidsec-border);
    border-left: 3px solid var(--aidsec-teal);
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600;
    font-size: 1.5rem !important;
    color: var(--aidsec-text) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--aidsec-text-dim) !important;
    font-weight: 500;
}

/* ── Sidebar ──────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #141926 0%, #0e1117 100%);
    border-right: 1px solid var(--aidsec-border);
}
section[data-testid="stSidebar"] [data-testid="stMetric"] {
    padding: 8px 10px;
    border-left-width: 2px;
}
section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    font-size: 1.2rem !important;
}
section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
}

/* sidebar page-link nav styling */
section[data-testid="stSidebar"] .stPageLink a {
    border-radius: 6px !important;
    padding: 6px 10px !important;
    margin-bottom: 1px;
    transition: background 0.15s ease;
    text-decoration: none !important;
    color: var(--aidsec-text) !important;
    font-weight: 500;
}
section[data-testid="stSidebar"] .stPageLink a:hover {
    background: var(--aidsec-teal-dim) !important;
}
section[data-testid="stSidebar"] .stPageLink a[aria-current="page"],
section[data-testid="stSidebar"] .stPageLink a[data-active="true"] {
    background: var(--aidsec-teal-dim) !important;
    font-weight: 600;
}

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stFormSubmitButton"],
button[kind="primary"] {
    background: var(--aidsec-teal) !important;
    color: #0e1117 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
    text-shadow: none !important;
}
.stButton > button[kind="primary"]:hover,
button[kind="primary"]:hover {
    background: #00e8bb !important;
    box-shadow: 0 0 16px var(--aidsec-teal-dim) !important;
}
.stButton > button {
    border-radius: 6px !important;
    border: 1px solid var(--aidsec-border) !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    border-color: var(--aidsec-teal) !important;
    color: var(--aidsec-teal) !important;
}

/* ── Download buttons ─────────────────────────────────── */
.stDownloadButton > button {
    border-radius: 6px !important;
    border: 1px solid var(--aidsec-border) !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover {
    border-color: var(--aidsec-teal) !important;
}

/* ── Tabs ─────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--aidsec-border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
    padding: 8px 20px;
    font-weight: 500;
    color: var(--aidsec-text-dim);
}
.stTabs [aria-selected="true"] {
    color: var(--aidsec-teal) !important;
    border-bottom: 2px solid var(--aidsec-teal) !important;
    font-weight: 600;
}

/* ── Containers / cards ───────────────────────────────── */
[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--aidsec-border) !important;
    border-radius: 8px !important;
    background: var(--aidsec-surface) !important;
}

/* ── Expanders ────────────────────────────────────────── */
.streamlit-expanderHeader {
    font-weight: 500 !important;
    border-radius: 6px;
}
details {
    border: 1px solid var(--aidsec-border) !important;
    border-radius: 8px !important;
}

/* ── Inputs / selects ─────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stMultiSelect > div > div {
    border-color: var(--aidsec-border) !important;
    border-radius: 6px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--aidsec-teal) !important;
    box-shadow: 0 0 0 1px var(--aidsec-teal) !important;
}

/* ── Dataframes ───────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--aidsec-border);
    border-radius: 8px;
    overflow: hidden;
}

/* ── Progress bar ─────────────────────────────────────── */
.stProgress > div > div > div {
    background: var(--aidsec-teal) !important;
}

/* ── Title and headers ────────────────────────────────── */
h1 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}
h2, h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
}

/* ── Dividers ─────────────────────────────────────────── */
hr {
    border-color: var(--aidsec-border) !important;
    opacity: 0.5;
}

/* ── Checkbox ─────────────────────────────────────────── */
.stCheckbox label span[data-checked="true"] {
    background-color: var(--aidsec-teal) !important;
    border-color: var(--aidsec-teal) !important;
}

/* ── Status badge utility classes ─────────────────────── */
.status-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}
.badge-offen { background: #3498db35; color: #7ec8e3; border: 1px solid #3498db55; }
.badge-pending { background: #f39c1235; color: #f7c56e; border: 1px solid #f39c1255; }
.badge-gewonnen { background: #2ecc7135; color: #7ee2a8; border: 1px solid #2ecc7155; }
.badge-verloren { background: #e74c3c35; color: #f09a92; border: 1px solid #e74c3c55; }

/* ── Grade badge utility ──────────────────────────────── */
.grade-badge {
    display: inline-block;
    width: 32px;
    height: 32px;
    line-height: 32px;
    text-align: center;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 0.85rem;
}
.grade-A { background: #2ecc7140; color: #58d68d; border: 1px solid #2ecc7166; }
.grade-B { background: #f1c40f40; color: #f5d657; border: 1px solid #f1c40f66; }
.grade-C { background: #e67e2240; color: #eb984e; border: 1px solid #e67e2266; }
.grade-D { background: #e74c3c40; color: #ec7063; border: 1px solid #e74c3c66; }
.grade-F { background: #c0392b40; color: #e06050; border: 1px solid #c0392b66; }

/* ── LLM status badge ─────────────────────────────────── */
.llm-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.8rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.llm-online { background: #2ecc7135; color: #58d68d; border: 1px solid #2ecc7155; }
.llm-offline { background: #e74c3c35; color: #ec7063; border: 1px solid #e74c3c55; }

/* ── Lead row styling ─────────────────────────────────── */
.lead-row {
    padding: 6px 12px;
    border-radius: 6px;
    border-left: 3px solid transparent;
    margin-bottom: 2px;
    font-size: 0.9rem;
    transition: background 0.1s ease;
}
.lead-row:hover { background: var(--aidsec-surface); }
.lead-row-even { background: #1a1f2e40; }
.lead-row .lead-firma { font-weight: 600; color: var(--aidsec-text); }
.lead-row .lead-meta { color: var(--aidsec-text-dim); font-size: 0.85rem; }
.lead-row .lead-status {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}

/* ── Email preview card ───────────────────────────────── */
.email-preview {
    background: var(--aidsec-surface);
    border: 1px solid var(--aidsec-border);
    border-radius: 8px;
    padding: 16px 20px;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.7;
}
.email-preview .ep-to { color: var(--aidsec-teal); font-weight: 600; }
.email-preview .ep-subject { font-weight: 600; font-size: 1.05rem; margin-bottom: 8px; }
.email-preview .ep-body { color: var(--aidsec-text); white-space: pre-wrap; }

/* ── Pipeline column headers ──────────────────────────── */
.pipeline-header {
    padding: 8px 0 4px 0;
    margin-bottom: 8px;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.02em;
}
.pipeline-header-offen { border-bottom: 3px solid var(--status-offen); color: var(--status-offen); }
.pipeline-header-pending { border-bottom: 3px solid var(--status-pending); color: var(--status-pending); }
.pipeline-header-gewonnen { border-bottom: 3px solid var(--status-gewonnen); color: var(--status-gewonnen); }
.pipeline-header-verloren { border-bottom: 3px solid var(--status-verloren); color: var(--status-verloren); }

/* ── Scrollbar refinement ─────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--aidsec-border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--aidsec-teal); }

/* ══════════════════════════════════════════════════════════
   RESPONSIVE / MOBILE  (≤ 768 px)
   ══════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
    /* Stack horizontal column blocks vertically */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 100% !important;
        flex-basis: 100% !important;
    }

    /* Larger touch targets for buttons */
    .stButton > button,
    .stDownloadButton > button {
        min-height: 44px !important;
        font-size: 0.95rem !important;
        padding: 10px 16px !important;
    }

    /* Full-width buttons on mobile */
    .stButton, .stDownloadButton {
        width: 100% !important;
    }
    .stButton > button,
    .stDownloadButton > button {
        width: 100% !important;
    }

    /* Bigger form inputs for thumbs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stDateInput > div > div > input {
        min-height: 44px !important;
        font-size: 1rem !important;
    }

    /* Reduce main-area padding */
    .main .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 1rem !important;
    }

    /* Metric cards: more compact */
    [data-testid="stMetric"] {
        padding: 8px 10px !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }

    /* Tabs: scrollable, no wrap */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 14px !important;
        white-space: nowrap !important;
        font-size: 0.88rem !important;
    }

    /* Dataframes scroll horizontally */
    [data-testid="stDataFrame"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }

    /* Scale titles down */
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.15rem !important; }
    h3 { font-size: 1.0rem !important; }

    /* Lead rows: tighter on mobile */
    .lead-row {
        padding: 8px 10px !important;
        font-size: 0.85rem !important;
    }

    /* Pipeline columns stack vertically by default (handled above) */
    .pipeline-header {
        font-size: 0.9rem !important;
    }

    /* Expanders: make summaries tappable */
    .streamlit-expanderHeader {
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
    }

    /* Email preview: reduce padding */
    .email-preview {
        padding: 12px 14px !important;
    }
}

/* Tablet tweaks (769 – 1024 px) */
@media (min-width: 769px) and (max-width: 1024px) {
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 48% !important;
        flex-basis: 48% !important;
    }
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── Page callables ─────────────────────────────────────────────────

def pg_dashboard():
    from views.dashboard import render
    render()

def pg_leads():
    if st.session_state.get("selected_lead_id"):
        from views.lead_detail import render as render_detail
        render_detail(st.session_state["selected_lead_id"])
    else:
        from views.leads import render
        render()

def pg_kampagnen():
    from views.kampagnen import render
    render()

def pg_import():
    from views.import_leads import render
    render()

def pg_ranking():
    from views.ranking import render
    render()

def pg_agenten():
    from views.agenten import render
    render()

def pg_email():
    from views.email import render
    render()

def pg_marketing():
    from views.marketing_ideen import render
    render()

def pg_settings():
    from views.einstellungen import render
    render()


# ── Sidebar brand header ──────────────────────────────────────────
SIDEBAR_HEADER = """
<div style="text-align:center; padding: 8px 0 4px 0; margin-bottom:4px;">
    <div style="font-family:'JetBrains Mono',monospace; font-size:1.6rem; font-weight:700; letter-spacing:0.04em;">
        <span style="color:#00d4aa;">Aid</span><span style="color:#e8eaed;">Sec</span>
    </div>
    <div style="font-size:0.78rem; color:#b8bec6; text-transform:uppercase; letter-spacing:0.12em; margin-top:2px;">
        Lead Management
    </div>
    <div style="height:1px; background: linear-gradient(90deg, transparent, #00d4aa44, transparent); margin-top:10px;"></div>
</div>
"""

SIDEBAR_FOOTER = """
<div style="text-align:center; padding:12px 0 4px 0; margin-top:8px;">
    <div style="height:1px; background: linear-gradient(90deg, transparent, #2a304088, transparent); margin-bottom:10px;"></div>
    <div style="font-size:0.78rem; color:#6b728099; font-family:'JetBrains Mono',monospace; letter-spacing:0.05em;">
        v2.1 &middot; AidSec Dashboard
    </div>
</div>
"""


@st.cache_data(ttl=120)
def _get_sidebar_stats():
    try:
        from cache_helpers import cached_dashboard_kpis
        kpis = cached_dashboard_kpis()
        s = kpis["status"]
        k = kpis["kategorie"]
        fu = kpis["followups"]
        return {
            "total": s["total"],
            "offene": s["offen"],
            "pending": s["pending"],
            "gewonnen": s["gewonnen"],
            "verloren": s["verloren"],
            "anwalt": k["anwalt"],
            "praxis": k["praxis"],
            "wordpress": k["wordpress"],
            "follow_ups": fu["overdue"] + fu["today"],
        }
    except Exception:
        return {
            "total": 0, "offene": 0, "pending": 0, "gewonnen": 0,
            "verloren": 0, "anwalt": 0, "praxis": 0, "wordpress": 0,
            "follow_ups": 0,
        }


# ── Navigation (st.navigation API — no auto-detection) ────────────

_PAGES = [
    st.Page(pg_dashboard, title="Dashboard", icon="📊", default=True, url_path="dashboard"),
    st.Page(pg_leads, title="Leads", icon="📋", url_path="leads"),
    st.Page(pg_kampagnen, title="Kampagnen", icon="🎯", url_path="kampagnen"),
    st.Page(pg_import, title="Import", icon="📥", url_path="import-leads"),
    st.Page(pg_ranking, title="Ranking", icon="🔍", url_path="ranking"),
    st.Page(pg_agenten, title="Agenten", icon="🤖", url_path="agenten"),
    st.Page(pg_email, title="E-Mail", icon="📧", url_path="email"),
    st.Page(pg_marketing, title="Marketing Ideen", icon="💡", url_path="marketing-ideen"),
    st.Page(pg_settings, title="Einstellungen", icon="⚙️", url_path="einstellungen"),
]

pg = st.navigation(_PAGES, position="hidden")


# ── Sidebar layout ────────────────────────────────────────────────

st.sidebar.markdown(SIDEBAR_HEADER, unsafe_allow_html=True)

for p in _PAGES:
    st.sidebar.page_link(p)

st.sidebar.markdown("---")

stats = _get_sidebar_stats()

sc1, sc2 = st.sidebar.columns(2)
sc1.metric("Total", stats["total"])
sc2.metric("Offen", stats["offene"])
sc1, sc2 = st.sidebar.columns(2)
sc1.metric("Pending", stats["pending"])
sc2.metric("Gewonnen", stats["gewonnen"])
sc1, sc2 = st.sidebar.columns(2)
sc1.metric("Verloren", stats["verloren"])
sc2.metric("Anwälte", stats["anwalt"])
sc1, sc2 = st.sidebar.columns(2)
sc1.metric("Praxen", stats["praxis"])
sc2.metric("WordPress", stats["wordpress"])

if stats.get("follow_ups", 0) > 0:
    st.sidebar.markdown(
        f'<div style="text-align:center;margin-top:8px;">'
        f'<span style="background:#f0a50030;color:#f0a500;border:1px solid #f0a50044;'
        f'padding:4px 12px;border-radius:16px;font-size:0.8rem;font-weight:600;'
        f'font-family:JetBrains Mono,monospace;">'
        f'📅 {stats["follow_ups"]} Follow-up{"s" if stats["follow_ups"] != 1 else ""}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

if os.getenv("APP_PASSWORD", ""):
    if st.sidebar.button("🚪 Abmelden", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

st.sidebar.markdown(SIDEBAR_FOOTER, unsafe_allow_html=True)


# ── Execute selected page ─────────────────────────────────────────
pg.run()
