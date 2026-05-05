import streamlit as st
import asyncio
import concurrent.futures
import sys
from dataclasses import dataclass, field
from typing import List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Pull secrets from Streamlit Cloud when env vars aren't set locally
import os
if not os.getenv("SERPER_API_KEY"):
    try:
        os.environ["SERPER_API_KEY"] = st.secrets["SERPER_API_KEY"]
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass

from scraper import JobSearcher
from classifier import JobClassifier

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="PulseHire",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Data class that scraper expects ─────────────────────────────────────────
@dataclass
class Prefs:
    location: str = "United States"
    seniority: List[str] = field(default_factory=lambda: ["mid-level", "senior"])
    remote_preference: str = "any"

# ── CSS injection ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

/* ── hide Streamlit chrome ── */
#MainMenu, footer { visibility: hidden; }
[data-testid="stToolbar"]  { display: none; }
[data-testid="stDecoration"] { display: none; }
.stDeployButton { display: none; }

/* ── root vars ── */
:root {
  --bg:        #1a1a1e;
  --purple:    #bb55ff;
  --purple-lt: #d4aaff;
  --purple-dk: #7722cc;
  --card-bg:   rgba(255,255,255,0.035);
  --card-br:   rgba(160,80,255,0.22);
  --text:      #e8e8f0;
  --muted:     #7a7a99;
  --font-h:    'Orbitron', monospace;
  --font-b:    'Share Tech Mono', monospace;
}

/* ── app background ── */
.stApp, .stApp > div { background: #1a1a1e !important; color: var(--text); }

/* ── orbs ── */
.orb {
  position: fixed; border-radius: 50%;
  filter: blur(60px); pointer-events: none; z-index: 0;
}
.orb-1 { width:380px;height:160px; background:rgba(148,50,220,.22);  top:-40px;    left:-80px;   animation:d1 18s ease-in-out infinite alternate; }
.orb-2 { width:320px;height:140px; background:rgba(148,50,220,.25);  top:22%;      right:-60px;  animation:d2 22s ease-in-out infinite alternate; }
.orb-3 { width:420px;height:180px; background:rgba(120,40,200,.20);  bottom:18%;   left:-100px;  animation:d3 15s ease-in-out infinite alternate; }
.orb-4 { width:360px;height:150px; background:rgba(160,60,240,.28);  bottom:-30px; right:-60px;  animation:d4 20s ease-in-out infinite alternate; }
@keyframes d1 { from{transform:translate(0,0)}  to{transform:translate(30px,40px)}  }
@keyframes d2 { from{transform:translate(0,0)}  to{transform:translate(-25px,35px)} }
@keyframes d3 { from{transform:translate(0,0)}  to{transform:translate(40px,-30px)} }
@keyframes d4 { from{transform:translate(0,0)}  to{transform:translate(-35px,-25px)}}

/* ── content above orbs ── */
.block-container {
  position: relative; z-index: 2;
  padding: 1.25rem 2rem 6rem !important;
  max-width: 1060px !important;
}

/* ── PulseHire header ── */
.ph-header {
  display:flex; align-items:center; justify-content:space-between;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid rgba(160,80,255,.2);
  margin-bottom: 1.75rem;
}
.ph-logo {
  font-family:var(--font-h); font-size:2rem; font-weight:900;
  letter-spacing:.14em; text-transform:uppercase;
}
.ph-logo .pulse { color:#d4aaff; }
.ph-logo .hire  { color:#bb55ff; text-shadow:0 0 20px rgba(187,85,255,.55); }
.ph-sub { font-family:var(--font-b); font-size:.65rem; color:var(--muted); letter-spacing:.12em; margin-top:.3rem; }
.live-wrap { display:flex; align-items:center; gap:.5rem;
  font-family:var(--font-h); font-size:.6rem; letter-spacing:.18em; color:#44ff88; }
.live-dot {
  width:9px; height:9px; background:#44ff88; border-radius:50%;
  box-shadow:0 0 10px #44ff88;
  animation: blink 1.3s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.15} }

/* ── stat cards ── */
.stat-row { display:flex; gap:1rem; margin-bottom:1.75rem; }
.stat-card {
  flex:1; background:var(--card-bg);
  border:1px solid var(--card-br); border-radius:10px;
  padding:1rem 1.25rem; backdrop-filter:blur(6px);
}
.stat-num {
  font-family:var(--font-h); font-size:1.75rem; font-weight:900;
  color:#c880ff; line-height:1;
  text-shadow:0 0 18px rgba(200,128,255,.4);
}
.stat-label {
  font-family:var(--font-b); font-size:.62rem;
  color:var(--muted); letter-spacing:.14em;
  text-transform:uppercase; margin-top:.35rem;
}

/* ── section labels ── */
.sec-label {
  font-family:var(--font-h); font-size:.6rem;
  letter-spacing:.28em; color:rgba(160,80,255,.75);
  text-transform:uppercase; padding-bottom:.5rem;
  border-bottom:1px solid rgba(160,80,255,.12);
  margin:1.5rem 0 1rem;
}

/* ── gradient divider ── */
.grad-div {
  height:1px; margin:2rem 0 1.5rem;
  background:linear-gradient(90deg,transparent,rgba(187,85,255,.45),transparent);
}

/* ── job cards ── */
.job-card {
  background:var(--card-bg); border:1px solid var(--card-br);
  border-radius:10px; padding:1.2rem 1.25rem 1.2rem 1.5rem;
  margin-bottom:.875rem; position:relative; overflow:hidden;
  transition:border-color .2s, box-shadow .2s;
}
.job-card::before {
  content:''; position:absolute; left:0;top:0;bottom:0; width:3px;
  background:linear-gradient(180deg,#bb55ff,#7722cc); opacity:0;
  transition:opacity .25s;
}
.job-card:hover { border-color:rgba(187,85,255,.45); box-shadow:0 4px 28px rgba(148,50,220,.14); }
.job-card:hover::before { opacity:1; }

.card-top { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:.7rem; }
.card-title { font-family:var(--font-h); font-size:.92rem; font-weight:700; color:#e8e8f0; letter-spacing:.02em; }
.card-company { font-family:var(--font-b); font-size:.76rem; color:var(--muted); margin-top:.22rem; }
.card-badges { display:flex; gap:.35rem; flex-shrink:0; margin-left:1rem; margin-top:.1rem; }

.badge {
  font-family:var(--font-h); font-size:.52rem; letter-spacing:.1em;
  font-weight:700; padding:.2rem .5rem; border-radius:4px;
}
.b-hot  { background:rgba(255,60,100,.18);  color:#ff6b9d; border:1px solid rgba(255,60,100,.3);  }
.b-new  { background:rgba(40,200,120,.16);  color:#44dd88; border:1px solid rgba(40,200,120,.28); }
.b-rem  { background:rgba(40,120,255,.16);  color:#66aaff; border:1px solid rgba(40,120,255,.28); }
.b-phdr { background:rgba(255,180,0,.12);   color:#ffcc44; border:1px solid rgba(255,180,0,.22);  }
.b-phdo { background:rgba(255,140,0,.10);   color:#ffaa33; border:1px solid rgba(255,140,0,.2);   }
.b-nphd { background:rgba(40,200,120,.12);  color:#55cc88; border:1px solid rgba(40,200,120,.22); }

.skill-tags { display:flex; flex-wrap:wrap; gap:.35rem; margin-bottom:.85rem; }
.skill-tag {
  font-family:var(--font-b); font-size:.62rem;
  padding:.18rem .55rem; border-radius:999px;
  background:rgba(160,80,255,.1); border:1px solid rgba(160,80,255,.26);
  color:#bb88ff;
}

.card-meta { display:flex; align-items:center; gap:1.25rem;
  font-family:var(--font-b); font-size:.68rem; color:var(--muted); }
.card-meta-sep { color:rgba(160,80,255,.3); }
.card-link {
  margin-left:auto; color:#bb55ff; text-decoration:none;
  font-family:var(--font-h); font-size:.58rem; letter-spacing:.1em;
  border:1px solid rgba(187,85,255,.35); padding:.25rem .75rem; border-radius:6px;
  transition:all .2s;
}
.card-link:hover { background:rgba(187,85,255,.15); border-color:#bb55ff; }

/* ── bottom nav ── */
.bottom-nav {
  position:fixed; bottom:0; left:0; right:0;
  background:rgba(16,16,22,.94); backdrop-filter:blur(14px);
  border-top:1px solid rgba(160,80,255,.2);
  display:flex; justify-content:space-around; align-items:center;
  padding:.7rem 0; z-index:100;
}
.nav-item { display:flex; flex-direction:column; align-items:center; gap:.2rem;
  font-family:var(--font-h); font-size:.48rem; letter-spacing:.14em;
  color:var(--muted); cursor:pointer; }
.nav-item.active { color:#bb77ff; }
.nav-icon { font-size:1rem; }

/* ── Streamlit widget overrides ── */
/* sidebar */
[data-testid="stSidebar"] { background:rgba(16,16,22,.97) !important; border-right:1px solid rgba(160,80,255,.2) !important; }
[data-testid="stSidebar"] * { font-family:var(--font-b); }
[data-testid="stSidebar"] label { color:var(--muted) !important; font-size:.7rem !important; letter-spacing:.1em; text-transform:uppercase; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 { font-family:var(--font-h) !important; color:var(--purple-lt) !important; }

/* text input */
[data-testid="stTextInput"] input {
  background:rgba(255,255,255,.04) !important;
  border:1.5px solid rgba(160,80,255,.4) !important;
  border-radius:8px !important; color:#d4aaff !important;
  font-family:var(--font-b) !important; font-size:.88rem !important;
  padding:.7rem 1rem !important;
}
[data-testid="stTextInput"] input::placeholder { color:rgba(160,80,255,.45) !important; }
[data-testid="stTextInput"] input:focus { border-color:#bb55ff !important; box-shadow:0 0 0 2px rgba(187,85,255,.15) !important; }
[data-testid="stTextInput"] label { display:none !important; }

/* selectbox */
[data-testid="stSelectbox"] > div > div {
  background:rgba(255,255,255,.04) !important;
  border:1.5px solid rgba(160,80,255,.3) !important;
  border-radius:8px !important;
  font-family:var(--font-b) !important; color:#d4aaff !important;
}

/* multiselect */
[data-testid="stMultiSelect"] > div > div {
  background:rgba(255,255,255,.04) !important;
  border:1.5px solid rgba(160,80,255,.3) !important;
  border-radius:8px !important;
  font-family:var(--font-b) !important; color:#d4aaff !important;
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
  background:rgba(160,80,255,.2) !important; border-color:rgba(187,85,255,.4) !important;
  font-family:var(--font-b) !important;
}

/* radio */
[data-testid="stRadio"] label { font-family:var(--font-b) !important; color:var(--muted) !important; font-size:.78rem !important; }
[data-testid="stRadio"] input:checked + div { color:#bb55ff !important; }

/* checkbox */
.stCheckbox label { font-family:var(--font-b) !important; color:var(--muted) !important; font-size:.78rem !important; }

/* SCAN button — targets the main scan button only via class we add */
div[data-testid="stButton"].scan-btn > button,
div[data-testid="stButton"] > button {
  background:linear-gradient(135deg,#6611bb,#aa33ee) !important;
  color:#fff !important; font-family:var(--font-h) !important;
  font-size:.65rem !important; font-weight:700 !important;
  letter-spacing:.15em !important; border:none !important;
  border-radius:8px !important; width:100% !important;
  padding:.72rem 1rem !important; text-transform:uppercase;
  box-shadow:0 0 18px rgba(170,51,238,.35) !important;
  transition:all .2s !important;
}
div[data-testid="stButton"] > button:hover {
  background:linear-gradient(135deg,#7722cc,#bb44ff) !important;
  box-shadow:0 0 28px rgba(187,85,255,.55) !important;
  transform:translateY(-1px);
}

/* pills / chip overrides */
[data-testid="stPills"] { font-family:var(--font-h) !important; }
[data-testid="stPills"] label { font-size:.6rem !important; letter-spacing:.1em !important; }

/* spinner */
div[data-testid="stSpinner"] > div { border-top-color:#bb55ff !important; }

/* expander */
details > summary {
  font-family:var(--font-h) !important; font-size:.65rem !important;
  letter-spacing:.12em !important; color:var(--muted) !important;
  background:rgba(255,255,255,.02) !important;
  border:1px solid rgba(160,80,255,.2) !important; border-radius:8px !important;
}
details { background:rgba(255,255,255,.02) !important; border:1px solid rgba(160,80,255,.15) !important; border-radius:8px !important; }

/* no-results state */
.no-results {
  background:var(--card-bg); border:1px solid var(--card-br);
  border-radius:10px; padding:3rem; text-align:center;
  font-family:var(--font-b); color:var(--muted); font-size:.85rem;
}
.no-results .nr-icon { font-size:2.5rem; margin-bottom:1rem; }

/* warning banner */
.api-warn {
  background:rgba(255,200,0,.08); border:1px solid rgba(255,200,0,.3);
  color:#ffcc55; border-radius:8px; padding:.875rem 1rem;
  font-family:var(--font-b); font-size:.78rem; margin-bottom:1.25rem;
}
</style>
""", unsafe_allow_html=True)

# ── Orbs (rendered once, position:fixed so they stay) ────────────────────────
st.markdown("""
<div class="orb orb-1"></div>
<div class="orb orb-2"></div>
<div class="orb orb-3"></div>
<div class="orb orb-4"></div>
""", unsafe_allow_html=True)

# ── US States ────────────────────────────────────────────────────────────────
US_STATES = [
    "All States (US)", "Alabama", "Alaska", "Arizona", "Arkansas", "California",
    "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii",
    "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma",
    "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming", "Washington DC",
]
STATE_ABBREVS = {
    "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
    "Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA",
    "Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS",
    "Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA",
    "Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT",
    "Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM",
    "New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK",
    "Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC",
    "South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT",
    "Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI",
    "Wyoming":"WY","Washington DC":"DC",
}
FOREIGN_INDICATORS = {
    "copenhagen","denmark","london","england","berlin","germany","paris","france",
    "toronto","canada","amsterdam","netherlands","stockholm","sweden","sydney",
    "australia","singapore","india","bangalore","mumbai","delhi","dubai","uae",
    "ireland","dublin","barcelona","spain","rome","italy","tokyo","japan",
    "beijing","shanghai","china","brazil","mexico","zürich","switzerland",
    "oslo","norway","helsinki","finland","brussels","belgium",
}

def _is_us_location(loc: str) -> bool:
    loc = (loc or "").lower()
    if not loc or "remote" in loc or "anywhere" in loc:
        return True
    if "united states" in loc or ", us" in loc or " usa" in loc:
        return True
    words = loc.replace(",", " ").replace(".", " ").split()
    if any(w.upper() in STATE_ABBREVS.values() for w in words):
        return True
    if any(fi in loc for fi in FOREIGN_INDICATORS):
        return False
    return True  # neutral/unknown — keep

def filter_by_state(jobs, state: str):
    if state == "All States (US)":
        return [j for j in jobs if _is_us_location(j.get("location", ""))]
    abbrev = STATE_ABBREVS.get(state, "").lower()
    state_lower = state.lower()
    def matches(loc):
        loc = (loc or "").lower()
        if not loc or "remote" in loc or "anywhere" in loc:
            return True
        return (state_lower in loc
                or (abbrev and f", {abbrev}" in loc)
                or (abbrev and f" {abbrev}" in loc)
                or (abbrev and loc.endswith(f" {abbrev}")))
    return [j for j in jobs if matches(j.get("location", ""))]

# ── Session state ────────────────────────────────────────────────────────────
if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "searched" not in st.session_state:
    st.session_state.searched = False

# ── Sidebar: preferences ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ SCAN SETTINGS")
    location = st.selectbox("State", US_STATES, index=0)
    seniority = st.multiselect(
        "Seniority",
        ["entry-level", "mid-level", "senior", "lead", "director"],
        default=["mid-level", "senior"],
    )
    remote_pref = st.radio(
        "Arrangement",
        ["any", "remote", "hybrid", "onsite"],
        format_func=lambda x: x.upper(),
    )
    st.divider()
    st.markdown(
        '<div style="font-family:\'Share Tech Mono\',monospace;font-size:.7rem;color:#7a7a99;line-height:1.6">'
        "Searches Google Jobs, Greenhouse & Lever boards for AI/ML roles at healthcare startups. "
        "Claude filters every listing for relevance."
        "</div>",
        unsafe_allow_html=True,
    )

# ── API key warning ──────────────────────────────────────────────────────────
import os
if not os.getenv("SERPER_API_KEY") or not os.getenv("ANTHROPIC_API_KEY"):
    st.markdown(
        '<div class="api-warn">⚠ <strong>API keys missing.</strong> '
        'Edit <code>.env</code> with your <code>SERPER_API_KEY</code> and '
        '<code>ANTHROPIC_API_KEY</code>, then restart.</div>',
        unsafe_allow_html=True,
    )

# ── Header ───────────────────────────────────────────────────────────────────
total_jobs = len(st.session_state.jobs)
st.markdown(
    """
    <div class="ph-header">
      <div>
        <div class="ph-logo">
          <span class="pulse">PULSE</span><span class="hire">HIRE</span>
        </div>
        <div class="ph-sub">AI · HEALTHCARE · STARTUPS · REAL-TIME</div>
      </div>
      <div class="live-wrap">
        <div class="live-dot"></div>
        LIVE SCAN
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Stat cards ────────────────────────────────────────────────────────────────
phd_count  = sum(1 for j in st.session_state.jobs if j.get("requires_phd") or j.get("phd_preferred"))
nophd_count = total_jobs - phd_count
disp_total = total_jobs if st.session_state.searched else 847
disp_new   = nophd_count if st.session_state.searched else 214
disp_phd   = phd_count   if st.session_state.searched else 63

st.markdown(
    f"""
    <div class="stat-row">
      <div class="stat-card">
        <div class="stat-num">{disp_total}</div>
        <div class="stat-label">Active Jobs</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{disp_new}</div>
        <div class="stat-label">No PhD Required</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{disp_phd}</div>
        <div class="stat-label">PhD Required/Preferred</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Search bar ────────────────────────────────────────────────────────────────
col_search, col_btn = st.columns([5, 1])
with col_search:
    _ = st.text_input("q", placeholder="> search AI health roles...", label_visibility="collapsed", key="query_input")
with col_btn:
    scan_clicked = st.button("SCAN")

# ── Filter chips ──────────────────────────────────────────────────────────────
CHIP_OPTIONS = ["ALL", "REMOTE", "SEED", "SERIES A", "NLP/LLM", "IMAGING AI", "$200K+", "NO PhD", "PhD ONLY"]
try:
    selected_chips = st.pills(
        "Filter",
        options=CHIP_OPTIONS,
        default=["ALL"],
        selection_mode="multi",
        label_visibility="collapsed",
    )
    if not selected_chips:
        selected_chips = ["ALL"]
except AttributeError:
    selected_chips = st.multiselect(
        "FILTERS",
        CHIP_OPTIONS,
        default=["ALL"],
        label_visibility="collapsed",
    ) or ["ALL"]

# ── Run search ────────────────────────────────────────────────────────────────
def run_full_search(prefs: Prefs):
    async def _inner():
        searcher = JobSearcher()
        classifier = JobClassifier()
        raw = await searcher.search(prefs)
        return await classifier.filter_and_classify(raw)

    def _in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_inner())
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_in_thread).result(timeout=180)


if scan_clicked:
    prefs = Prefs(
        location=location or "United States",
        seniority=seniority or ["mid-level", "senior"],
        remote_preference=remote_pref or "any",
    )
    with st.spinner("SCANNING HEALTHCARE AI ROLES..."):
        try:
            st.session_state.jobs = run_full_search(prefs)
            st.session_state.searched = True
        except Exception as e:
            st.error(f"Search failed: {e}")

# ── Filter logic ──────────────────────────────────────────────────────────────
def apply_chips(jobs, chips):
    if "ALL" in chips or not chips:
        return jobs
    out = list(jobs)
    if "REMOTE" in chips:
        out = [j for j in out if j.get("remote") or "remote" in (j.get("location") or "").lower()]
    if "SEED" in chips:
        out = [j for j in out if "seed" in (j.get("company_stage") or "").lower()]
    if "SERIES A" in chips:
        out = [j for j in out if "series a" in (j.get("company_stage") or "").lower()]
    if "NLP/LLM" in chips:
        out = [j for j in out if any(k in (j.get("skills") or "").lower() for k in ["nlp","llm","language model","gpt","bert","transformer"])]
    if "IMAGING AI" in chips:
        out = [j for j in out if any(k in (j.get("skills") or "").lower() for k in ["imaging","radiology","vision","dicom","segmentation","pathology"])]
    if "$200K+" in chips:
        out = [j for j in out if "200" in (j.get("salary") or "") or "200k" in (j.get("description") or "").lower()]
    if "NO PhD" in chips:
        out = [j for j in out if not j.get("requires_phd") and not j.get("phd_preferred")]
    if "PhD ONLY" in chips:
        out = [j for j in out if j.get("requires_phd") or j.get("phd_preferred")]
    return out

visible = apply_chips(st.session_state.jobs, selected_chips)
visible = filter_by_state(visible, location)

# ── Card renderer ─────────────────────────────────────────────────────────────
def _esc(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

COLORS = ["#2563eb","#7c3aed","#db2777","#9333ea","#0891b2","#059669","#4f46e5","#be185d"]
def _color(name):
    h = 0
    for c in str(name):
        h = (h * 31 + ord(c)) & 0xffffffff
    return COLORS[abs(h) % len(COLORS)]

def card_html(j, idx):
    company = j.get("company") or "Unknown"
    init = "".join(w[0] for w in company.split() if w)[:2].upper() or "?"
    color = _color(company)
    skills = [s.strip() for s in (j.get("skills") or "").split(",") if s.strip()]

    # Badges
    badges = ""
    if idx < 3:
        badges += '<span class="badge b-hot">HOT</span>'
    if j.get("posted_date", "").lower() in ("today", "1 day ago", "just now", "12 hours ago"):
        badges += '<span class="badge b-new">NEW</span>'
    loc = (j.get("location") or "").lower()
    if j.get("remote") or "remote" in loc:
        badges += '<span class="badge b-rem">REMOTE</span>'
    if j.get("requires_phd"):
        badges += '<span class="badge b-phdr">PhD REQ</span>'
    elif j.get("phd_preferred"):
        badges += '<span class="badge b-phdo">PhD PREF</span>'
    else:
        badges += '<span class="badge b-nphd">NO PhD</span>'

    stage = j.get("company_stage", "")
    stage_str = f" · {stage.upper()}" if stage and stage != "unknown" else ""
    meta = f"{_esc(j.get('posted_date','Recently'))}{stage_str}"
    skill_tags = "".join(f'<span class="skill-tag">{_esc(s)}</span>' for s in skills[:8])
    url = j.get("url") or "#"

    return f"""
<div class="job-card">
  <div class="card-top">
    <div>
      <div class="card-title">{_esc(j.get('title','Untitled Role'))}</div>
      <div class="card-company">
        <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:{color};font-family:var(--font-h);font-size:.55rem;font-weight:900;color:#fff;margin-right:.4rem">{init}</span>
        {_esc(company)} &nbsp;·&nbsp; {_esc(j.get('location','Location TBD'))}
      </div>
    </div>
    <div class="card-badges">{badges}</div>
  </div>
  {"<div class='skill-tags'>" + skill_tags + "</div>" if skill_tags else ""}
  <div class="card-meta">
    <span>{meta}</span>
    <a href="{_esc(url)}" target="_blank" rel="noopener" class="card-link">VIEW →</a>
  </div>
</div>"""

# ── Render results ────────────────────────────────────────────────────────────
if not st.session_state.searched:
    st.markdown(
        '<div class="no-results"><div class="nr-icon">🔍</div>'
        'Set your preferences in the sidebar and click <strong>SCAN</strong> to find AI healthcare jobs.</div>',
        unsafe_allow_html=True,
    )
elif not visible:
    st.markdown(
        '<div class="no-results"><div class="nr-icon">📭</div>'
        'No jobs match the current filters. Try adjusting your chips or running a new scan.</div>',
        unsafe_allow_html=True,
    )
else:
    top, rest = visible[:6], visible[6:]

    st.markdown('<div class="sec-label">// TOP MATCHES</div>', unsafe_allow_html=True)
    for i, j in enumerate(top):
        st.markdown(card_html(j, i), unsafe_allow_html=True)

    if rest:
        st.markdown('<div class="grad-div"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-label">// TRENDING</div>', unsafe_allow_html=True)
        for i, j in enumerate(rest):
            st.markdown(card_html(j, i + 6), unsafe_allow_html=True)

# ── Bottom nav ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="bottom-nav">
      <div class="nav-item active">
        <div class="nav-icon">📡</div>FEED
      </div>
      <div class="nav-item">
        <div class="nav-icon">🔍</div>SEARCH
      </div>
      <div class="nav-item">
        <div class="nav-icon">💾</div>SAVED
      </div>
      <div class="nav-item">
        <div class="nav-icon">👤</div>PROFILE
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
