"""Mezan visual identity (app v3.1): deep royal purple, secondary purple, gold, soft lavender, off-white. Logo assets,
CSS, chart styling and formatting helpers. Presentation only - no calculations."""
import base64
import functools
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# brand palette (brief): deep royal purple, secondary purple, gold, soft lavender, off-white background
INK, PURPLE, GOLD, LAV, BG = "#211540", "#493581", "#D2B16B", "#F1EDF8", "#F8F9FC"
LAV2, LINE, PURPLE_LT = "#E2DAF2", "#E3DEEE", "#9C8BC9"
TEXT, MUTED = "#1A1530", "#55506A"
GOLD_DK = "#7A5C14"                      # gold for text on light backgrounds (contrast ≥ 4.5:1)
OK, WARN, BAD, GREY = "#2E7D5B", "#A8670F", "#B23A2E", "#B5AFC6"   # status colours only
SEQ = [PURPLE, GOLD, PURPLE_LT, "#6B6880", "#C9A4A0", INK]
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"

TONES = {"neutral": (INK, "#FFFFFF", LINE), "brand": ("#FFFFFF", INK, INK), "ok": (OK, "#EEF7F2", "#BFE0CF"),
         "warn": (WARN, "#FCF5E8", "#EBCF9C"), "bad": (BAD, "#FBEDEB", "#EDBDB6"), "gold": (GOLD_DK, "#FBF6EA", "#E8D6A8")}


@functools.lru_cache(maxsize=None)
def logo_b64(size=128):
    f = ASSETS / f"mezan_icon_{size}.png"
    return base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


def logo_img(px=40, size=128, extra=""):
    b = logo_b64(size)
    return (f'<img src="data:image/png;base64,{b}" alt="Mezan logo" width="{px}" height="{px}" '
            f'style="display:block;flex:none;{extra}">') if b else ""


FAVICON = str(ASSETS / "favicon.png")

CSS = f"""
<style>
:root {{ --mz-ink:{INK}; --mz-purple:{PURPLE}; --mz-gold:{GOLD}; --mz-lav:{LAV}; --mz-bg:{BG}; }}
html, body, [data-testid="stAppViewContainer"], .stApp {{background:{BG};}}
.block-container {{padding-top: 2.6rem; padding-bottom: 3rem; max-width: 1440px;}}
header[data-testid="stHeader"] {{background: transparent; height: 2.2rem;}}
h1, h2, h3, h4 {{color:{INK}; letter-spacing:-0.01em;}}
p, li {{color:{TEXT};}}

/* ---------------- sidebar ---------------- */
section[data-testid="stSidebar"] {{background:{INK}; width: 268px !important; min-width: 268px !important;}}
section[data-testid="stSidebar"] > div {{padding-top: 0.6rem;}}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{color:#D9D1EC;}}
.mz-sb-brand {{display:flex; align-items:center; gap:10px; padding:4px 2px 14px 2px; border-bottom:1px solid #3A2C63; margin-bottom:12px;}}
.mz-sb-brand .t1 {{color:#fff; font-weight:800; font-size:1.06rem; letter-spacing:.04em; white-space:nowrap;}}
.mz-sb-brand .t1 span {{color:{GOLD}; font-weight:600;}}
.mz-sb-brand .t2 {{color:#C9BFE3; font-size:.72rem; line-height:1.25; margin-top:2px;}}
.mz-sb-label {{color:#A99CCB !important; font-size:.68rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; margin:6px 0 4px 2px;}}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] label p {{color:#A99CCB !important; font-size:.68rem; font-weight:700;
  letter-spacing:.12em; text-transform:uppercase;}}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {{background:#FFFFFF !important; border:1px solid {GOLD} !important; border-radius:10px !important;}}
section[data-testid="stSidebar"] [data-baseweb="select"] * {{color:{INK} !important; -webkit-text-fill-color:{INK} !important; opacity:1 !important; font-weight:600;}}
section[data-testid="stSidebar"] [data-baseweb="select"] svg {{fill:{INK} !important;}}
.mz-fac {{background:#2C1D55; border:1px solid #45357A; border-radius:12px; padding:10px 12px; margin:8px 0 14px 0;}}
.mz-fac .n {{color:#fff; font-weight:700; font-size:.88rem; line-height:1.3;}}
.mz-fac .m {{color:#C9BFE3; font-size:.76rem; margin-top:3px;}}
.mz-fac .s {{display:inline-block; margin-top:7px; font-size:.7rem; font-weight:700; padding:2px 9px; border-radius:999px;}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button {{justify-content:flex-start; width:100%; border-radius:10px;
  border:1px solid transparent; background:transparent; min-height:42px; padding:6px 12px; transition:background .12s;}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button > div {{justify-content:flex-start; width:100%;}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button p {{color:#E4DDF4 !important; font-size:.93rem; font-weight:600; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis;}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button [data-testid="stIconMaterial"] {{color:#B7A9DA; font-size:1.25rem;}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button:hover {{background:#2F2059; border-color:#45357A;}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"] {{background:{LAV}; border-color:{GOLD}; box-shadow: inset 4px 0 0 {GOLD};}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"] p {{color:{INK} !important; font-weight:800;}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"] [data-testid="stIconMaterial"] {{color:{PURPLE};}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] {{margin-bottom:-6px;}}
.mz-sb-foot {{color:#9F93C2 !important; font-size:.7rem; line-height:1.4; border-top:1px solid #3A2C63; padding-top:10px; margin-top:16px;}}
/* icon rail when space is limited: labels hidden visually but kept for screen readers (no word breaking) */
@media (min-width: 768px) and (max-width: 1180px) {{
  section[data-testid="stSidebar"] {{width: 84px !important; min-width: 84px !important;}}
  section[data-testid="stSidebar"] [class*="st-key-nav_"] button, section[data-testid="stSidebar"] [class*="st-key-nav_"] button > div {{justify-content:center; padding:6px;}}
  section[data-testid="stSidebar"] [class*="st-key-nav_"] button p,
  .mz-sb-brand .txt, .mz-fac, .mz-sb-foot, .mz-sb-label,
  section[data-testid="stSidebar"] [data-testid="stSelectbox"] label {{position:absolute !important; width:1px; height:1px; overflow:hidden;
    clip:rect(0 0 0 0); white-space:nowrap;}}
  section[data-testid="stSidebar"] [data-testid="stSelectbox"] {{display:none;}}
  .mz-sb-brand {{justify-content:center;}}
}}

/* ---------------- global header ---------------- */
.mz-top {{display:flex; align-items:center; justify-content:space-between; gap:16px; background:{INK}; border-radius:14px;
  padding:12px 18px; border-bottom:3px solid {GOLD}; min-height:64px;}}
.mz-top .brand {{display:flex; align-items:center; gap:12px; min-width:0;}}
.mz-top .t1 {{color:#fff; font-weight:800; font-size:1.18rem; letter-spacing:.04em; white-space:nowrap;}}
.mz-top .t1 span {{color:{GOLD}; font-weight:600;}}
.mz-top .t2 {{color:#CFC4EA; font-size:.8rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}
.mz-top .chips {{display:flex; flex-wrap:wrap; gap:6px; justify-content:flex-end;}}
.mz-chip {{display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:999px; font-size:.74rem; font-weight:700;
  white-space:nowrap;}}
[class*="st-key-cfg_pop"] button {{min-height:64px; border-radius:14px; border:2px solid {GOLD}; background:#FFFFFF;}}
[class*="st-key-cfg_pop"] button p {{color:{INK}; font-weight:800; font-size:.9rem; line-height:1.2; white-space:normal; text-align:left;}}
[data-testid="stPopoverBody"] {{min-width: min(860px, 92vw); max-width: 92vw;}}
.mz-stale {{display:flex; align-items:center; gap:10px; background:#FCF5E8; border:1px solid #EBCF9C; border-left:5px solid {WARN};
  border-radius:10px; padding:10px 14px; color:{TEXT}; font-size:.92rem; margin:10px 0 2px;}}

/* ---------------- page structure ---------------- */
.mz-head {{margin:18px 0 6px;}}
.mz-head .q {{color:{GOLD_DK}; font-weight:700; font-size:.78rem; letter-spacing:.1em; text-transform:uppercase;}}
.mz-head .t {{display:flex; align-items:center; gap:10px; color:{INK}; font-weight:800; font-size:1.7rem; line-height:1.2; margin:2px 0 4px;}}
.mz-head .s {{color:{MUTED}; font-size:1rem; max-width:980px;}}
.mz-sec {{margin:26px 0 8px; padding-top:14px; border-top:1px solid {LINE};}}
.mz-sec .t {{color:{INK}; font-weight:800; font-size:1.14rem; display:flex; align-items:center; gap:8px;}}
.mz-sec .s {{color:{MUTED}; font-size:.9rem; margin-top:2px;}}
.mz-cards {{display:grid; grid-template-columns:repeat(auto-fit, minmax(176px, 1fr)); gap:12px; margin:10px 0 6px;}}
.mz-card {{border-radius:12px; padding:12px 14px; border:1px solid {LINE}; background:#fff; min-width:0;}}
.mz-card .l {{font-size:.76rem; font-weight:700; color:{MUTED}; text-transform:uppercase; letter-spacing:.05em; line-height:1.25;}}
.mz-card .v {{font-size:1.42rem; font-weight:800; color:{INK}; margin-top:4px; line-height:1.15; overflow-wrap:anywhere;}}
.mz-card .d {{font-size:.8rem; color:{MUTED}; margin-top:4px; line-height:1.3;}}
.mz-hero {{background:{INK}; border-radius:16px; padding:20px 22px; color:#fff; border-left:6px solid {GOLD};}}
.mz-hero .k {{color:{GOLD}; font-weight:700; font-size:.76rem; letter-spacing:.12em; text-transform:uppercase;}}
.mz-hero .p {{font-size:1.5rem; font-weight:800; margin:6px 0 10px; line-height:1.25; color:#fff;}}
.mz-hero .pills {{display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px;}}
.mz-hero .pill {{background:#33235F; border:1px solid #4E3D86; border-radius:10px; padding:6px 10px; font-size:.86rem; color:#fff;}}
.mz-hero .pill b {{color:{GOLD}; margin-right:4px;}}
.mz-hero .grid {{display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:10px;}}
.mz-hero .grid div .a {{color:#BFB3DD; font-size:.74rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em;}}
.mz-hero .grid div .b {{font-size:1.25rem; font-weight:800; color:#fff; margin-top:2px;}}
.mz-hero .grid div .c {{color:#CFC4EA; font-size:.78rem;}}
.mz-hero .foot {{color:#CFC4EA; font-size:.8rem; margin-top:12px;}}
.mz-ins {{border-radius:10px; border:1px solid {LINE}; background:#fff; padding:10px 12px; margin:6px 0; display:flex; gap:10px;}}
.mz-ins .bar {{flex:none; width:4px; border-radius:4px;}}
.mz-ins .txt {{font-size:.92rem; color:{TEXT}; line-height:1.45;}}
.mz-grp {{font-weight:800; color:{INK}; font-size:.92rem; margin:12px 0 2px; display:flex; align-items:center; gap:8px;}}
.mz-label {{display:inline-block; font-size:.7rem; font-weight:700; padding:1px 8px; border-radius:10px; margin-right:6px; white-space:nowrap;
  vertical-align:middle;}}
.mz-note {{color:{MUTED}; font-size:.84rem;}}
.mz-explain {{color:{MUTED}; font-size:.86rem; margin:-4px 0 10px;}}
.mz-flow {{display:flex; gap:0; margin:8px 0; overflow-x:auto;}}
.mz-flow .st {{flex:1 1 0; min-width:92px; position:relative; padding:0 6px; text-align:center;}}
.mz-flow .st .dot {{width:30px; height:30px; border-radius:15px; margin:0 auto; display:flex; align-items:center; justify-content:center;
  font-weight:800; font-size:.82rem; position:relative; z-index:2;}}
.mz-flow .st:not(:last-child)::after {{content:""; position:absolute; top:15px; left:calc(50% + 15px); right:calc(-50% + 15px); height:3px;
  background:{LINE}; z-index:1;}}
.mz-flow .st.done:not(:last-child)::after {{background:{OK};}}
.mz-flow .st .n {{font-size:.8rem; font-weight:700; color:{INK}; margin-top:6px; line-height:1.25;}}
.mz-flow .st .m {{font-size:.72rem; color:{MUTED}; margin-top:2px; line-height:1.25;}}
.mz-proj {{border:1px solid {LINE}; border-radius:12px; background:#fff; padding:12px 14px; height:100%;}}
.mz-proj.inrec {{border:2px solid {GOLD}; background:#FFFDF7;}}
.mz-proj .h {{display:flex; justify-content:space-between; gap:8px; align-items:flex-start;}}
.mz-proj .h .nm {{font-weight:800; color:{INK}; font-size:1rem; line-height:1.25;}}
.mz-proj table {{width:100%; border-collapse:collapse; margin-top:8px; font-size:.84rem;}}
.mz-proj td {{padding:3px 0; border-bottom:1px dashed {LINE}; color:{TEXT};}}
.mz-proj td:last-child {{text-align:right; font-weight:700;}}
.mz-thr {{border:1px solid {LINE}; border-radius:12px; background:#fff; padding:12px 14px; margin:8px 0;}}
.mz-thr .h {{display:flex; justify-content:space-between; gap:8px; flex-wrap:wrap; font-weight:800; color:{INK};}}
.mz-thr .track {{position:relative; height:12px; background:{LAV}; border-radius:6px; margin:22px 0 22px;}}
.mz-thr .seg {{position:absolute; top:0; height:12px; border-radius:6px;}}
.mz-thr .mk {{position:absolute; top:-6px; width:3px; height:24px; border-radius:2px;}}
.mz-thr .ml {{position:absolute; font-size:.72rem; font-weight:700; white-space:nowrap; transform:translateX(-50%);}}
.mz-thr .row {{display:flex; flex-wrap:wrap; gap:16px; font-size:.85rem; color:{TEXT};}}
.mz-arch {{display:grid; grid-template-columns:repeat(auto-fit, minmax(240px,1fr)); gap:12px; margin:8px 0;}}
.mz-layer {{border-radius:12px; padding:14px; border:1px solid {LINE}; background:#fff;}}
.mz-layer .k {{font-size:.72rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase;}}
.mz-layer .t {{font-weight:800; color:{INK}; font-size:1.02rem; margin:2px 0 6px;}}
.mz-layer ul {{margin:0; padding-left:1.1rem; font-size:.86rem;}}
.mz-layer li {{margin:2px 0;}}
.mz-layer .r {{font-size:.8rem; color:{MUTED}; margin-top:8px; border-top:1px dashed {LINE}; padding-top:6px;}}
.mz-ans {{border:1px solid {LINE}; border-left:6px solid {GOLD}; border-radius:12px; background:#fff; padding:16px 18px; margin:10px 0;}}
.mz-ans .q {{color:{GOLD_DK}; font-size:.76rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase;}}
.mz-ans .a {{color:{INK}; font-size:1.18rem; font-weight:800; line-height:1.35; margin:4px 0 8px;}}
.mz-ans .n {{display:inline-block; background:{LAV}; color:{INK}; border-radius:10px; padding:6px 12px; font-weight:800; font-size:1rem; margin:2px 0 6px;}}
.mz-ans .act {{background:#F4FAF6; border:1px solid #BFE0CF; border-radius:10px; padding:8px 12px; font-size:.9rem; margin-top:8px;}}
.mz-ans .m {{color:{MUTED}; font-size:.82rem; margin-top:8px;}}
.mz-next b {{white-space:nowrap;}}
.mz-next {{display:flex; align-items:center; gap:10px; background:{LAV}; border:1px solid {LAV2}; border-radius:12px; padding:12px 14px;
  font-size:.93rem; color:{INK}; margin-top:6px;}}
[class*="st-key-dq_"] button {{min-height:92px; border-radius:14px; border:1px solid {LINE}; background:#fff; flex-direction:column;
  align-items:flex-start; justify-content:flex-start; text-align:left; padding:12px 14px; box-shadow:0 1px 2px rgba(33,21,64,.05);}}
[class*="st-key-dq_"] button > div {{flex-direction:column; align-items:flex-start; gap:6px; width:100%;}}
[class*="st-key-dq_"] button p {{white-space:normal !important; overflow:visible !important; text-overflow:clip !important; font-weight:700; color:{INK}; font-size:.93rem; line-height:1.3; text-align:left;}}
[class*="st-key-dq_"] button [data-testid="stIconMaterial"] {{color:{PURPLE}; font-size:1.5rem; margin-bottom:4px;}}
[class*="st-key-dq_"] button:hover {{border-color:{PURPLE};}}
[class*="st-key-dq_"] button[kind="primary"] {{background:{INK}; border:2px solid {GOLD};}}
[class*="st-key-dq_"] button[kind="primary"] p {{color:#fff;}}
[class*="st-key-dq_"] button[kind="primary"] [data-testid="stIconMaterial"] {{color:{GOLD};}}
div[data-testid="stMetric"] {{background:#fff; border:1px solid {LINE}; border-radius:12px; padding:10px 14px;}}
div[data-testid="stMetricValue"] {{font-size:1.35rem; color:{INK}; font-weight:800;}}
div[data-testid="stMetricLabel"] p {{color:{MUTED}; font-weight:700; white-space:normal;}}
div[data-testid="stExpander"] details {{border-radius:10px; border-color:{LINE}; background:#fff;}}
div[data-testid="stExpander"] details summary p {{font-weight:700; color:{INK};}}
div[data-testid="stVerticalBlockBorderWrapper"] {{border-color:{LINE} !important; border-radius:12px !important;}}
div[data-testid="stDataFrame"] {{border:1px solid {LINE}; border-radius:10px;}}
.stTabs [data-baseweb="tab-list"] {{gap:6px; border-bottom:1px solid {LINE};}}
.stTabs [data-baseweb="tab"] {{font-weight:700; padding:6px 12px;}}
button[kind="primary"] {{background:{PURPLE}; border-color:{PURPLE};}}
button[kind="primary"]:hover {{background:{INK}; border-color:{INK};}}
.main button[kind="primary"] p, [data-testid="stDownloadButton"] button[kind="primary"] p, [data-testid="stPopoverBody"] button[kind="primary"] p,
[data-testid="stDownloadButton"] button[kind="primary"] [data-testid="stIconMaterial"] {{color:#FFFFFF !important;}}
[data-testid="stMain"] button[kind="primary"] p, [data-testid="stMain"] button[kind="primary"] [data-testid="stIconMaterial"] {{color:#FFFFFF;}}
@media (max-width: 900px) {{
  .mz-top {{flex-direction:column; align-items:flex-start;}} .mz-top .chips {{justify-content:flex-start;}}
  .mz-head .t {{font-size:1.4rem;}} .mz-card .v {{font-size:1.2rem;}} .mz-hero .p {{font-size:1.25rem;}}
}}
</style>
"""

KIND_STYLE = {   # value provenance and producer labels
    "measured": ("Measured", "#1F5B45", "#E2F1EA"),
    "estimated": ("Estimated (approved)", "#7A4E0E", "#FBEFD9"),
    "hypothetical": ("Hypothetical", BAD, "#FBE9E3"),
    "synthetic": ("Synthetic", PURPLE, LAV2),
    "external": ("External source", "#2F4E8A", "#E6ECF7"),
    "reported": ("Reported (company)", "#1F5B45", "#E2F1EA"),
    "calculated": ("Calculated", PURPLE, LAV),
    "ml": ("Machine learning", GOLD_DK, "#FBF1DA"),
    "ai": ("AI-generated (language model)", GOLD_DK, "#FBF1DA"),
    "rule": ("Rule-based", "#3B3550", "#ECEAF2"),
    "stat": ("Statistical estimate", "#7A4E0E", "#FBEFD9"),
    "engine": ("Calculation engine", PURPLE, LAV),
    "partial": ("Partially implemented", WARN, "#FBEFD9"),
    "optional": ("Optional", "#2F4E8A", "#E6ECF7"),
}
KIND_FROM_INSIGHT = {"Calculation engine": "engine", "Rule-based check": "rule", "ML flag": "ml", "Statistical estimate": "stat",
                     "ML classification": "ml"}
SEV_COLOR = {"action": BAD, "warning": WARN, "info": PURPLE}


def inject(st):
    st.markdown(CSS, unsafe_allow_html=True)


def label(kind, text=None):
    t, fg, bg = KIND_STYLE.get(kind, (kind, TEXT, LAV))
    return f'<span class="mz-label" style="color:{fg};background:{bg}">{text or t}</span>'


def chip(text, fg=INK, bg=GOLD):
    return f'<span class="mz-chip" style="color:{fg};background:{bg}">{text}</span>'


def status_tone(status):
    s = (status or "").lower()
    if s.startswith("approved") or s in ("complete", "passes", "yes"):
        return "ok"
    if "blocked" in s or "invalid" in s or "no data" in s or "fail" in s:
        return "bad"
    return "warn"


def tone_chip(text, tone):
    fg, bg, _ = TONES.get(tone, TONES["neutral"])
    return chip(text, fg, bg)


def topbar_html(facility, basis, run_text, stale=False):
    chips = (chip(facility, INK, GOLD) + chip(basis, "#EDE8F7", "#3B2A6B")
             + (chip("Results out of date", "#fff", WARN) if stale else chip(run_text, "#EDE8F7", "#3B2A6B")))
    return (f'<div class="mz-top"><div class="brand">{logo_img(44, 128, "border-radius:10px")}<div class="txt">'
            f'<div class="t1">MEZAN <span>| ميزان</span></div><div class="t2">AI-Assisted Industrial Investment Platform</div></div></div>'
            f'<div class="chips">{chips}</div></div>')


def sidebar_brand_html():
    return (f'<div class="mz-sb-brand">{logo_img(40, 128, "border-radius:9px")}<div class="txt"><div class="t1">MEZAN <span>| ميزان</span>'
            f'</div><div class="t2">AI-Assisted Industrial<br>Investment Platform</div></div></div>')


def page_header(st, eyebrow, title, sub=None, icon=None):
    """eyebrow = management question; title = page title; sub = one-sentence purpose."""
    st.markdown(f'<div class="mz-head"><div class="q">{eyebrow}</div><div class="t">{title}</div>'
                + (f'<div class="s">{sub}</div>' if sub else "") + "</div>", unsafe_allow_html=True)


def section(st, title, sub=None, anchor=None):
    a = f' id="{anchor}"' if anchor else ""
    st.markdown(f'<div class="mz-sec"{a}><div class="t">{title}</div>' + (f'<div class="s">{sub}</div>' if sub else "") + "</div>",
                unsafe_allow_html=True)


def cards_html(items):
    """items: (label, value, detail, tone)."""
    out = []
    for it in items:
        lab, val, det, tone = (list(it) + [None, "neutral"])[:4]
        fg, bg, bd = TONES.get(tone or "neutral", TONES["neutral"])
        vcol = INK if tone in (None, "neutral") else fg
        out.append(f'<div class="mz-card" style="background:{bg};border-color:{bd}"><div class="l" style="{"color:#CFC4EA" if tone == "brand" else ""}">{lab}</div>'
                   f'<div class="v" style="color:{vcol if tone != "brand" else "#fff"}">{val}</div>'
                   + (f'<div class="d" style="{"color:#CFC4EA" if tone == "brand" else ""}">{det}</div>' if det else "") + "</div>")
    return '<div class="mz-cards">' + "".join(out) + "</div>"


def cards(st, items):
    st.markdown(cards_html(items), unsafe_allow_html=True)


def insight_html(i):
    kind = KIND_FROM_INSIGHT.get(i.kind, "engine")
    return (f'<div class="mz-ins"><div class="bar" style="background:{SEV_COLOR.get(i.severity, PURPLE)}"></div>'
            f'<div class="txt">{label(kind, i.kind)}{i.text}</div></div>')


def sar(x, digits=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    x = float(x)
    if abs(x) < 0.5:
        x = 0.0
    if abs(x) >= 1e6:
        return f"SAR {x / 1e6:,.{digits}f} M"
    return f"SAR {x:,.0f}"


def pct(x, d=1):
    return "—" if x is None else f"{100 * float(x):.{d}f}%"


def tonnes(x):
    return "—" if x is None else f"{float(x):,.0f} t"


def style_fig(fig, height=340, title=None, legend="top"):
    """Consistent chart frame: title left, legend on its own row below the title (or below the plot), generous margins
    and automargins so labels are never clipped."""
    top = 18 + (34 if title else 0) + (30 if legend == "top" else 0)
    fig.update_layout(font=dict(family=FONT, size=13, color=TEXT), paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(t=top, b=52 if legend == "bottom" else 40, l=12, r=24), height=height, colorway=SEQ,
                      hoverlabel=dict(bgcolor="white", bordercolor=PURPLE, font=dict(family=FONT, size=13, color=TEXT)),
                      legend=(dict(orientation="h", yanchor="bottom", y=1.0, x=0, xanchor="left", font=dict(size=12)) if legend == "top"
                              else dict(orientation="h", yanchor="top", y=-0.18, x=0, font=dict(size=12))))
    if legend is None:
        fig.update_layout(showlegend=False)
    if title:
        fig.update_layout(title=dict(text=title, x=0, xanchor="left", y=1, yanchor="top", yref="container", pad=dict(t=10, l=4),
                                     font=dict(size=15, color=INK)))
    fig.update_xaxes(showgrid=False, linecolor="#D9D3E6", automargin=True, title_font=dict(size=12, color=MUTED), tickfont=dict(size=12))
    fig.update_yaxes(gridcolor="#EEEAF5", zerolinecolor="#D9D3E6", automargin=True, title_font=dict(size=12, color=MUTED),
                     tickfont=dict(size=12))
    fig.update_traces(selector=dict(type="bar"), cliponaxis=False, textfont=dict(size=12))
    return fig
