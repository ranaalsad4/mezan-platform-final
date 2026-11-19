"""Executive decision report (self-contained HTML, printable to PDF from any browser) and machine-readable exports.

Every number in the report is read from the analysis results passed in; nothing is recomputed or typed here.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import html
import json
import platform
from pathlib import Path

import numpy as np

from carbon_iq.assumptions import MODEL_VERSION, P
from mezan_ai.capabilities import CAPABILITIES, NOT_AI
from . import APP_NAME, APP_TAGLINE, APP_VERSION
from . import labels as LB

METHOD_REFS = [
    ("GHG Protocol Corporate Standard (WRI/WBCSD 2004)", "Scope 1 and 2 accounting", "https://ghgprotocol.org/corporate-standard"),
    ("IPCC (2006) Guidelines, Vol. 1 Ch. 3", "Uncertainty propagation", "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/1_Volume1/V1_3_Ch3_Uncertainties.pdf"),
    ("Rubin (1976), Biometrika 63(3)", "Missing-data mechanisms (theory)", "https://doi.org/10.1093/biomet/63.3.581"),
    ("Metropolis & Ulam (1949), JASA 44(247)", "Monte Carlo simulation", "https://doi.org/10.1080/01621459.1949.10483310"),
    ("Charnes & Cooper (1959), Management Science 6(1)", "Chance-constrained programming", "https://doi.org/10.1287/mnsc.6.1.73"),
    ("Pagnoncelli, Ahmed & Shapiro (2009), JOTA 142(2)", "Sample-average approximation of chance constraints", "https://doi.org/10.1007/s10957-009-9523-6"),
    ("Land & Doig (1960), Econometrica 28(3)", "Integer programming (branch and bound; cross-check solver)", "https://doi.org/10.2307/1910129"),
    ("Saltelli et al. (2008), Global Sensitivity Analysis: The Primer", "Sensitivity analysis", "https://doi.org/10.1002/9780470725184"),
    ("Howard (1966), IEEE Trans. SSC-2(1)", "Value of information", "https://doi.org/10.1109/TSSC.1966.300074"),
    ("Liu, Ting & Zhou (2008), ICDM", "Isolation Forest (anomaly detection)", "https://doi.org/10.1109/ICDM.2008.17"),
    ("Iglewicz & Hoaglin (1993), ASQC", "Robust (modified) z-score outlier rule", ""),
    ("Pedregosa et al. (2011), JMLR 12", "scikit-learn (ML library)", "https://jmlr.org/papers/v12/pedregosa11a.html"),
]
LIMITATIONS = [
    "Research prototype. Not a verified GHG inventory, not investment advice, not a production industrial system; not externally validated.",
    "Synthetic plant: all activity data, prices and project costs are hypothetical or transferred from public sources. No input is a measured factory observation.",
    "Ma'aden Rolling Company: energy and emissions are Ma'aden's 2025 reported figures; every investment number is a hypothetical Mezan scenario, not a Ma'aden value, plan or endorsement.",
    "Probabilities are model outputs on simulated futures under assumed input ranges; they are not guarantees and the ranges are not calibrated against observed outcomes.",
    "The ±% uncertainty of the baseline is model-based (first-order propagation of assumed input uncertainties), not a validated 95% confidence interval.",
    "Investment timing is partially implemented: one project (D, waste-heat recovery) and one price (natural gas).",
    "EVSI is calculated for one measurement only (motor-system audit). Other information values are EVPPI, an upper bound for any real measurement.",
    "AI/ML components (classification, anomaly flags, ML estimate challengers) were evaluated on synthetic data only.",
]


def _e(x):
    return html.escape(str(x))


def _sar(x):
    x = 0.0 if x is not None and abs(x) < 0.5 else x
    return "—" if x is None else (f"SAR {x / 1e6:,.2f} M" if abs(x) >= 1e6 else f"SAR {x:,.0f}")


def fmt_margin(se, p):
    """Margin above the tightened level in Monte Carlo standard errors; degenerate when every simulated future passes."""
    if p >= 1.0 - 1e-12:
        return "all futures pass"
    return "> 100 SE" if se > 100 else f"{se:,.1f} SE"


def settings_hash(settings, extra=None):
    blob = json.dumps(dict(settings=settings, extra=extra or {}), sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


def reproducibility(result, data_hash=None):
    import pandas, scipy, sklearn  # noqa: E401
    s = result["settings"]
    return dict(app=f"{APP_NAME} {APP_TAGLINE} v{APP_VERSION}", model_version=MODEL_VERSION, scenarios=s["n"], seed=s["seed"],
                basis=s["basis"], activity_basis=result["activity_basis"], settings_sha256=settings_hash(s),
                plant_data_sha256=data_hash, python=platform.python_version(), numpy=np.__version__, pandas=pandas.__version__,
                scipy=scipy.__version__, scikit_learn=sklearn.__version__,
                generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))


def results_json(result, voi=None, switching=None, discount=None, explanation=None, data_hash=None):
    """Machine-readable export of the analysis (no Scenarios object, no arrays)."""
    keep = {k: result[k] for k in ("settings", "model_version", "basis_label", "activity_basis", "totals", "target_t", "choice_names",
                                   "min_budget")}
    keep["recommended"] = result["recommended"]
    keep["portfolios"] = [{k: v for k, v in r.items() if k != "ids"} for r in result["table"]]
    keep["deterministic_optimum"] = ({k: v for k, v in result["det_best"].items() if k != "ids"} if result["det_best"] else None)
    keep["value_of_information"] = voi and dict(rule=voi["rule"], evpi=voi["evpi"], noise_floor=voi["noise_floor"],
                                                evppi=[{k: r[k] for k in ("information", "parameter", "evppi_sar", "collection_cost_sar",
                                                                         "net_value_sar", "decision_changes")} for r in voi["ranking"]],
                                                evsi_audit={k: v for k, v in voi["evsi_audit"].items()})
    keep["switch_points"] = switching
    keep["discount_rate_sweep"] = discount
    keep["explanation"] = explanation and dict(source=explanation["source"], label=explanation["label"],
                                               sections=explanation["sections"], llm_text=explanation["llm_text"])
    keep["reproducibility"] = reproducibility(result, data_hash)
    return json.dumps(keep, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


# ------------------------------------------------------------------ executive decision report
LOGO = Path(__file__).resolve().parents[1] / "assets" / "mezan_icon_256.png"
INK, PURPLE, GOLD, LAV, MUTED = "#211540", "#493581", "#D2B16B", "#F1EDF8", "#55506A"
PROJECT_NAMES = {"A": "Solar PV", "B": "Efficient motors and variable-speed drives", "C": "Compressed-air repairs",
                 "D": "Waste-heat recovery", "E": "Forklift electrification", "F": "Lower-carbon steel"}


def _names(portfolio):
    return [f"{i} — {PROJECT_NAMES.get(i, i)}" for i in portfolio.split("+")] if portfolio and portfolio != "(none)" else []


def report_model(result, facility, explanation, voi=None, switching=None, discount=None, data=None, anomalies=None,
                 data_hash=None, tornado=None):
    """Structured report content (sections of paragraphs, KPI rows and tables). Every value is read from the inputs."""
    s, rec, tot = result["settings"], result["recommended"], result["totals"]
    u12 = result["uncertainty_totals"]["Scope 1+2"][1]
    n = f"{s['n']:,}"
    secs = []
    secs.append(dict(title="Facility and reporting period", paras=[
        f"{facility['name']} · {facility['location']} · reporting year {facility['year']}.",
        f"Data basis: {result['activity_basis']}. Target convention: {result['basis_label']}. {facility['evidence']}",
        "Model status: research prototype (app v" + APP_VERSION + f", model {MODEL_VERSION}); model estimates, not verified factory "
        "outcomes; not externally validated; not investment advice."]))
    if rec:
        st_ = result["stats_recommended"]
        secs.append(dict(title="Recommended investment strategy", lead=f"Fund {rec['portfolio']}", bullets=_names(rec["portfolio"]),
                         kpis=[("Expected NPV", _sar(rec["e_npv"]), f"mean of {n} futures"),
                               ("NPV at base inputs", _sar(rec["npv_base_inputs"]), "deterministic"),
                               ("Capital required", _sar(rec["quoted_capex"]), f"quoted · budget {_sar(s['budget'])}"),
                               ("Carbon target met", f"{rec['p_target']:.2%}", f"of futures · required {s['alpha']:.0%}"),
                               ("Capex within budget", f"{rec['p_budget']:.2%}", f"of futures · required {s['beta']:.0%}")],
                         paras=[f"Primary rule D4: the highest expected-value portfolio whose quoted capital fits the budget and which "
                                f"passes the carbon test (≥ {result['a_eff']:.4f}) and, separately, the budget test (≥ {result['b_eff']:.4f}); "
                                f"required levels tightened for sampling error on {n} simulated futures (seed {s['seed']}). "
                                "Probabilities are modelled, not guaranteed, and are not one joint probability."]))
        secs.append(dict(title="Financial value and capital requirements", paras=[
            f"Expected NPV {_sar(rec['e_npv'])} averages all simulated futures; NPV at base inputs {_sar(rec['npv_base_inputs'])} uses the "
            f"most-likely value of every input. Quoted capital {_sar(rec['quoted_capex'])} of an available {_sar(s['budget'])}; "
            f"90th-percentile actual capital {_sar(st_['p90_capex'])}."]))
        secs.append(dict(title="Carbon impact", paras=[
            f"Scope 1 {tot['Scope 1']:,.0f} t, Scope 2 {tot['Scope 2']:,.0f} t, Scope 1+2 baseline {tot['Scope 1+2']:,.0f} tCO₂e/yr "
            f"(model-based range ±{u12:.1f}%, not a validated confidence interval). Required reduction {result['target_t']:,.0f} tCO₂e/yr "
            f"({s['target_share']:.0%}); expected reduction of the recommended portfolio {rec['e_t12']:,.0f} tCO₂e/yr. Scope 3 "
            f"({tot['Scope 3']:,.0f} t) is reported separately and is not part of the target."]))
        secs.append(dict(title="Risk assessment", kpis=[
            ("Downside NPV (5th pct)", _sar(st_["p5_npv"]), "1 in 20 futures is worse"),
            ("Average of worst 5%", _sar(st_["cvar5_npv"]), "CVaR(5%)"), ("P(NPV < 0)", f"{st_['p_loss']:.2%}", "share of futures"),
            ("Carbon test margin", fmt_margin(rec["margin_target_se"], rec["p_target"]), "above tightened level"),
            ("Budget test margin", fmt_margin(rec["margin_budget_se"], rec["p_budget"]), "above tightened level")]))
    else:
        mb = result["min_budget"]
        secs.append(dict(title="Recommended investment strategy", lead="No portfolio passes both risk requirements",
                         paras=[f"No portfolio passes both tests within {_sar(s['budget'])}; none is recommended and the budget is not raised."
                                + (f" The smallest budget that would make the primary rule feasible is about {_sar(mb['budget'])} ({mb['portfolio']})."
                                   if mb else "")]))
    alts = sorted([r for r in result["table"] if r["within_budget_quote"] and r["portfolio"] != "(none)"], key=lambda r: -r["e_npv"])[:8]
    secs.append(dict(title="Recommended and alternative portfolios", table=dict(
        head=["Portfolio", "Quoted capex", "Expected NPV", "NPV base inputs", "Carbon success", "Budget success", "Status"],
        rows=[[r["portfolio"] + (" ★" if rec and r["portfolio"] == rec["portfolio"] else ""), _sar(r["quoted_capex"]), _sar(r["e_npv"]),
               _sar(r["npv_base_inputs"]), f"{r['p_target']:.2%}", f"{r['p_budget']:.2%}",
               "passes both" if r["passes_carbon"] and r["passes_budget"] else "fails a test"] for r in alts],
        hl=[i for i, r in enumerate(alts) if rec and r["portfolio"] == rec["portfolio"]])))
    if tornado:
        secs.append(dict(title="Main uncertainties", paras=["Assumptions that move the value of the recommendation most (one-way, 5th to "
                                                            "95th percentile); value changes are not choice changes."],
                         table=dict(head=["Assumption", "NPV swing"], rows=[[LB.label(r["parameter"]), _sar(r["swing"])] for r in tornado[:5]])))
    if switching:
        rows = []
        for x in switching:
            for c in x["changes"]:
                rows.append([LB.label(x["parameter"]), "D1 deterministic", LB.fmt_value(x["parameter"], x["base"]),
                             LB.fmt_value(x["parameter"], c["threshold"]), f"{c['below']} ↔ {c['above']}"])
        if discount:
            for lab, key in (("D4 primary", "changes_D4"), ("D1 deterministic", "changes_D1")):
                for c in discount.get(key, [])[:1]:
                    rows.append(["Real discount rate", lab, f"{s['discount_rate']:.1%}", f"{c['threshold']:.2%}", f"{c['below']} ↔ {c['above']}"])
        robust = [LB.label(x["parameter"]) for x in switching if x["robust"]]
        secs.append(dict(title="Conditions that could change the decision", table=dict(
            head=["Input", "Rule", "Current", "Switch point", "Change"], rows=rows),
            paras=["D1 thresholds mark where the deterministic optimum changes; they are warnings, not confirmed changes of the "
                   "risk-constrained recommendation. Only the discount-rate sweep re-runs D4."
                   + (f" No switch within the tested range: {', '.join(robust)}." if robust else "")]))
    if voi:
        worth = [r for r in voi["ranking"] if r["net_value_sar"] is not None and r["net_value_sar"] > 0]
        ea = voi["evsi_audit"]
        rec_txt = (f"Collect: {worth[0]['information']} (upper-bound value exceeds the assumed cost)." if worth else
                   "None of the assessed measurements is economically justified under the assumed costs; this does not imply that no "
                   "other data collection (for example firm quotations) is useful.")
        secs.append(dict(title="Information-collection recommendations", paras=[
            rec_txt, f"Rule {voi['rule']} (carbon chance constraint), not exactly the primary rule D4. EVPI {_sar(voi['evpi'])} is the most any "
                     f"information could be worth. EVSI of the {ea['measurement']}: {_sar(ea['evsi'])} vs cost {_sar(ea['cost'])} (the only "
                     "measurement with EVSI)."],
            table=dict(head=["Information", "EVPPI (upper bound)", "Assumed cost", "Upper-bound net value", "Could change decision"],
                       rows=[[r["information"], _sar(r["evppi_sar"]), _sar(r["collection_cost_sar"]) if r["collection_cost_sar"] else "not collectable",
                              _sar(r["net_value_sar"]) if r["net_value_sar"] is not None else "—", "yes" if r["decision_changes"] else "no"]
                             for r in voi["ranking"]])))
    if explanation:
        secs.append(dict(title="Explanation", tag=explanation["label"],
                         paras=([explanation["llm_text"]] if explanation["source"] == "llm" else
                                [f"{sec['title']}. {sec['text']} [{sec['evidence']}]" for sec in explanation["sections"]])
                         + ([f"Note: {explanation['rejected']}"] if explanation.get("rejected") else [])))
    dq = []
    if data:
        dq.append(data)
    if data_hash:
        dq.append(f"Plant data SHA-256 {data_hash} (original upload kept unchanged).")
    if anomalies is not None:
        dq.append(f"Isolation Forest: {anomalies['n_flagged']} reporting-year month(s) flagged at score ≥ {anomalies['threshold']:.2f} "
                  "(advisory; scores are not probabilities)." if anomalies.get("applied") else
                  "Isolation Forest not applied: " + anomalies.get("reason", ""))
    if dq:
        secs.append(dict(title="Data quality and lineage", paras=dq))
    secs.append(dict(title="Relevant limitations", bullets=list(LIMITATIONS)))
    secs.append(dict(title="Supporting evidence: AI and calculation components", paras=[NOT_AI],
                     table=dict(head=["Capability", "Technique", "Status"], rows=[[c["name"], c["technique"], c["status"]] for c in CAPABILITIES])))
    secs.append(dict(title="Key assumptions", table=dict(head=["Input", "Value", "Evidence", "Source"], rows=[
        [LB.label(k), f"{P[k].value} {P[k].unit}", P[k].evidence, str(P[k].source)[:140]]
        for k in ("tariff", "gas_price_usd", "discount_rate", "ef_grid", "pv_capex_kw", "b_saving_frac", "c_saving_frac", "cost_submeter")])))
    secs.append(dict(title="Method references", bullets=[f"{a} — {b}" + (f" — {u}" if u else "") for a, b, u in METHOD_REFS]))
    secs.append(dict(title="Reproducibility", table=dict(head=["Item", "Value"],
                                                         rows=[[k, str(v)] for k, v in reproducibility(result, data_hash).items()])))
    return dict(title="Executive Decision Report", facility=facility, settings=s, sections=secs,
                generated=dt.datetime.now(dt.timezone.utc).strftime("%d %B %Y, %H:%M UTC"))


def _logo_b64():
    return base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""


REPORT_CSS = f""".mzr{{font-family:Inter,'Segoe UI',Arial,Helvetica,sans-serif;color:#1A1530;line-height:1.5;max-width:980px;margin:0 auto;
font-size:14px}}
.mzr .band{{background:{INK};color:#fff;padding:22px 26px;border-radius:14px;border-bottom:4px solid {GOLD};display:flex;gap:16px;align-items:center}}
.mzr .band img{{width:58px;height:58px;border-radius:12px}}
.mzr .band .k{{color:{GOLD};font-weight:700;letter-spacing:.12em;font-size:11px;text-transform:uppercase}}
.mzr .band .t{{font-size:24px;font-weight:800;margin:2px 0;color:#fff}}
.mzr .band .s{{color:#D9D1EC;font-size:13px}}
.mzr .status{{background:#FCF5E8;border-left:4px solid #A8670F;padding:9px 13px;border-radius:6px;font-size:12.5px;margin:14px 0}}
.mzr h2{{color:{INK};font-size:17px;margin:26px 0 8px;padding-bottom:5px;border-bottom:2px solid {LAV};break-after:avoid}}
.mzr h2 span{{color:{GOLD};margin-right:6px}}
.mzr .lead{{font-size:19px;font-weight:800;color:{INK};margin:4px 0}}
.mzr .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:10px 0}}
.mzr .kpi{{background:{LAV};border-radius:10px;padding:10px 12px;break-inside:avoid}}
.mzr .kpi .a{{font-size:11px;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:.04em}}
.mzr .kpi .b{{font-size:19px;font-weight:800;color:{INK};margin-top:2px}}
.mzr .kpi .c{{font-size:11.5px;color:{MUTED}}}
.mzr table{{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0}}
.mzr th{{background:{INK};color:#fff;text-align:left;font-weight:700;padding:7px 9px}}
.mzr td{{padding:6px 9px;border-bottom:1px solid #E3DEEE;vertical-align:top}}
.mzr tr:nth-child(even) td{{background:#FAF8FD}}
.mzr tr.hl td{{background:#FBF3DD;font-weight:700}}
.mzr .tag{{display:inline-block;font-size:11px;font-weight:700;padding:2px 9px;border-radius:10px;background:{LAV};color:{INK}}}
.mzr .foot{{color:{MUTED};font-size:11.5px;margin-top:26px;border-top:1px solid #E3DEEE;padding-top:8px}}
.mzr section{{break-inside:auto}}
@media print{{.mzr .band,.mzr th,.mzr .kpi,.mzr tr.hl td{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}"""


def report_body_html(model):
    """Report body scoped under .mzr (safe to embed in the app without nested scrolling)."""
    f = model["facility"]
    H = [f"<style>{REPORT_CSS}</style><div class='mzr'>"]
    lg = _logo_b64()
    H.append(f"<div class='band'>{f'<img alt="Mezan logo" src="data:image/png;base64,{lg}">' if lg else ''}<div>"
             f"<div class='k'>{_e(model['title'])}</div><div class='t'>MEZAN | ميزان</div>"
             f"<div class='s'>{_e(APP_TAGLINE)} · {_e(f['name'])} · reporting year {f['year']} · {_e(model['generated'])}</div></div></div>")
    H.append("<div class='status'><b>Status:</b> research prototype; model estimates, not verified factory outcomes; not externally "
             "validated; not investment advice.</div>")
    for i, sec in enumerate(model["sections"], 1):
        H.append(f"<section><h2><span>{i:02d}</span>{_e(sec['title'])}</h2>")
        if sec.get("tag"):
            H.append(f"<p><span class='tag'>{_e(sec['tag'])}</span></p>")
        if sec.get("lead"):
            H.append(f"<div class='lead'>{_e(sec['lead'])}</div>")
        if sec.get("bullets"):
            H.append("<ul>" + "".join(f"<li>{_e(b)}</li>" for b in sec["bullets"]) + "</ul>")
        if sec.get("kpis"):
            H.append("<div class='kpis'>" + "".join(f"<div class='kpi'><div class='a'>{_e(a)}</div><div class='b'>{_e(b)}</div>"
                                                   f"<div class='c'>{_e(c)}</div></div>" for a, b, c in sec["kpis"]) + "</div>")
        for p_ in sec.get("paras", []):
            H.append(f"<p>{_e(p_)}</p>")
        if sec.get("table") and sec["table"]["rows"]:
            t = sec["table"]
            H.append("<table><tr>" + "".join(f"<th>{_e(h)}</th>" for h in t["head"]) + "</tr>")
            for j, r in enumerate(t["rows"]):
                H.append(f"<tr class='{'hl' if j in t.get('hl', []) else ''}'>" + "".join(f"<td>{_e(c)}</td>" for c in r) + "</tr>")
            H.append("</table>")
        H.append("</section>")
    H.append(f"<div class='foot'>Generated by {_e(APP_NAME)} {_e(APP_TAGLINE)} v{APP_VERSION} · every number is read from the analysis "
             "run identified in the Reproducibility section.</div></div>")
    return "\n".join(H)


def executive_html(result, facility, explanation, voi=None, switching=None, discount=None, data=None, anomalies=None,
                   classification=None, data_hash=None, tornado=None):
    m = report_model(result, facility, explanation, voi, switching, discount, data, anomalies, data_hash, tornado)
    fav = _logo_b64()
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Mezan — Executive Decision Report</title>"
            + (f"<link rel='icon' href='data:image/png;base64,{fav}'>" if fav else "")
            + "<style>body{background:#F8F9FC;margin:0;padding:28px 18px}@page{size:A4;margin:16mm}</style></head><body>"
            + report_body_html(m) + "</body></html>")


def executive_pdf(result, facility, explanation, voi=None, switching=None, discount=None, data=None, anomalies=None,
                  data_hash=None, tornado=None):
    """Multi-page A4 PDF (ReportLab platypus: automatic page breaks, repeated table headers, branded header and page numbers)."""
    import io
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    m = report_model(result, facility, explanation, voi, switching, discount, data, anomalies, data_hash, tornado)
    font, bold = "Helvetica", "Helvetica-Bold"
    for reg, bd in (("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
                    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf")):
        try:
            pdfmetrics.registerFont(TTFont("MzSans", reg)); pdfmetrics.registerFont(TTFont("MzSansB", bd))
            font, bold = "MzSans", "MzSansB"
            break
        except Exception:  # noqa: BLE001 - fall back to the standard fonts (subscripts written as CO2e)
            continue
    sub = (lambda t: t) if font == "MzSans" else (lambda t: t.replace("₂", "2").replace("★", "*").replace("↔", "<->").replace("≥", ">="))
    ink, pur, gold, lav, mut = (colors.HexColor(c) for c in (INK, PURPLE, GOLD, LAV, MUTED))
    st = dict(
        body=ParagraphStyle("b", fontName=font, fontSize=9.2, leading=13, textColor=colors.HexColor("#1A1530"), alignment=TA_LEFT),
        h2=ParagraphStyle("h", fontName=bold, fontSize=12.5, leading=16, textColor=ink, spaceBefore=10, spaceAfter=4),
        lead=ParagraphStyle("l", fontName=bold, fontSize=14, leading=18, textColor=ink, spaceAfter=4),
        cell=ParagraphStyle("c", fontName=font, fontSize=8, leading=10.2),
        cellh=ParagraphStyle("ch", fontName=bold, fontSize=8, leading=10.2, textColor=colors.white),
        title=ParagraphStyle("t", fontName=bold, fontSize=17, leading=22, textColor=colors.white),
        small=ParagraphStyle("s", fontName=font, fontSize=8, leading=10.5, textColor=mut))
    P_ = lambda t, s_="body": Paragraph(html.escape(sub(str(t))), st[s_])  # noqa: E731
    W = A4[0] - 32 * mm
    story = []
    logo = Image(str(LOGO), 15 * mm, 15 * mm) if LOGO.exists() else Spacer(1, 1)
    band = Table([[logo, [Paragraph(f"<font color='{GOLD}' size=8>{html.escape(m['title'].upper())}</font>", st["body"]),
                          Paragraph("MEZAN", st["title"]),
                          Paragraph(f"<font color='#D9D1EC' size=8.5>{html.escape(sub(APP_TAGLINE))} · {html.escape(sub(facility['name']))} · "
                                    f"reporting year {facility['year']} · {html.escape(m['generated'])}</font>", st["body"])]]],
                 colWidths=[20 * mm, W - 20 * mm])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ink), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("LINEBELOW", (0, 0), (-1, -1), 3, gold), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                              ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [band, Spacer(1, 6), P_("Status: research prototype; model estimates, not verified factory outcomes; not externally "
                                     "validated; not investment advice.", "small"), Spacer(1, 4)]
    for i, sec in enumerate(m["sections"], 1):
        block = [Paragraph(f"<font color='{GOLD}'>{i:02d}</font>  {html.escape(sub(sec['title']))}", st["h2"])]
        if sec.get("tag"):
            block.append(P_(sec["tag"], "small"))
        if sec.get("lead"):
            block.append(P_(sec["lead"], "lead"))
        if sec.get("bullets"):
            block.append(ListFlowable([ListItem(P_(b), leftIndent=10) for b in sec["bullets"]], bulletType="bullet", start="•",
                                      leftIndent=10))
        if sec.get("kpis"):
            k = sec["kpis"]
            cells = [[Paragraph(f"<font size=7 color='{MUTED}'>{html.escape(sub(a.upper()))}</font><br/><font size=12><b>"
                                f"{html.escape(sub(b))}</b></font><br/><font size=7 color='{MUTED}'>{html.escape(sub(c))}</font>", st["body"])
                      for a, b, c in k]]
            kt = Table(cells, colWidths=[W / len(k)] * len(k))
            kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), lav), ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
                                    ("INNERGRID", (0, 0), (-1, -1), 2, colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            block += [kt, Spacer(1, 4)]
        for p_ in sec.get("paras", []):
            block.append(P_(p_))
        story.append(KeepTogether(block[:3]))
        story += block[3:]
        if sec.get("table") and sec["table"]["rows"]:
            t = sec["table"]
            data_ = [[Paragraph(html.escape(sub(h)), st["cellh"]) for h in t["head"]]]
            data_ += [[Paragraph(html.escape(sub(str(c))), st["cell"]) for c in r] for r in t["rows"]]
            tb = Table(data_, repeatRows=1, colWidths=[W / len(t["head"])] * len(t["head"]))
            sty = [("BACKGROUND", (0, 0), (-1, 0), ink), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                   ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#E3DEEE")),
                   ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF8FD")])]
            sty += [("BACKGROUND", (0, j + 1), (-1, j + 1), colors.HexColor("#FBF3DD")) for j in t.get("hl", [])]
            tb.setStyle(TableStyle(sty))
            if len(t["rows"]) <= 14 and not sec.get("paras") and not sec.get("kpis"):
                story[-1] = KeepTogether(block[:3] + [Spacer(1, 3), tb])
            else:
                story += [Spacer(1, 3), tb]
        story.append(Spacer(1, 4))

    def deco(c, d):
        c.saveState()
        c.setFillColor(ink); c.rect(0, A4[1] - 9 * mm, A4[0], 9 * mm, stroke=0, fill=1)
        c.setFillColor(gold); c.rect(0, A4[1] - 9.8 * mm, A4[0], 0.8 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont(bold, 8); c.drawString(16 * mm, A4[1] - 6 * mm, "MEZAN  ·  Executive Decision Report")
        c.setFont(font, 7.5); c.setFillColor(mut)
        c.drawString(16 * mm, 9 * mm, sub(f"{facility['name']} · research prototype · not investment advice"))
        c.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Page {d.page}")
        c.restoreState()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Mezan — Executive Decision Report", author=APP_NAME, subject=facility["name"])
    doc.build(story, onFirstPage=deco, onLaterPages=deco)
    return buf.getvalue()
