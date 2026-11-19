"""Session state, cached computations and the plant-data workflow state. Presentation layer only.

Expensive work (Monte Carlo, optimisation, switching, value of information, ML) is cached on the APPLIED scenario
settings, so editing a setting never reruns a simulation; only 'Run analysis' changes the applied settings.
"""
from __future__ import annotations

import copy
import io
from dataclasses import asdict

import pandas as pd
import streamlit as st

from carbon_iq.dataquality import estimate as ES
from mezan_ai import anomaly as AN
from mezan_ai import classifier as C
from mezan_ai import explain as X
from mezan_ai import imputation as IM
from mezan_ai import insights as I
from mezan_ai import llm
from mezan_platform import analysis as A
from mezan_platform import datasets as DSet

PAGES = ["Executive Overview", "Plant Data", "Carbon & Emissions", "Investment Planner", "Decision Intelligence",
         "Reports & Evidence"]
PAGE_ICONS = {"Executive Overview": ":material/space_dashboard:", "Plant Data": ":material/fact_check:",
              "Carbon & Emissions": ":material/co2:", "Investment Planner": ":material/account_balance:",
              "Decision Intelligence": ":material/psychology:", "Reports & Evidence": ":material/verified:"}
PAGE_KEYS = {"Executive Overview": "overview", "Plant Data": "plant", "Carbon & Emissions": "emissions",
             "Investment Planner": "planner", "Decision Intelligence": "decision", "Reports & Evidence": "reports"}
PAGE_ALIAS = {"Overview": "Executive Overview", "Emissions": "Carbon & Emissions"}   # insight.page values -> page names
# percentage widgets (the engine keeps fractions)
PCT_KEYS = {"target_share": "set_target_pct", "alpha": "set_alpha_pct", "beta": "set_beta_pct", "discount_rate": "set_discount_pct"}


def page_name(p):
    return PAGE_ALIAS.get(p, p)


def go_to(page):
    st.session_state["nav"] = page_name(page)
FAC_KEYS = list(DSet.FACILITIES)


def init():
    ss = st.session_state
    ss.setdefault("applied", asdict(A.DEFAULTS))
    for k, v in asdict(A.DEFAULTS).items():
        ss.setdefault(f"set_{k}", v)
    ss.setdefault("set_budget_m", ss["set_budget"] / 1e6)
    for k, w in PCT_KEYS.items():
        ss.setdefault(w, round(100 * ss[f"set_{k}"], 2))
    if ss.get("nav") not in PAGES:
        ss["nav"] = page_name(ss.get("nav", PAGES[0])) if page_name(ss.get("nav", "")) in PAGES else PAGES[0]
    ss.setdefault("di_q", "invest")
    ss.setdefault("set_activity_basis", "reference")
    ss.setdefault("applied_activity_basis", "reference")
    for k in ("decisions", "ml_adopt", "anom_review", "class_map", "editor_ver", "ml_eval"):
        ss.setdefault(k, {})
    ss.setdefault("plant_src", "demo")
    ss.setdefault("upload", None)
    ss.setdefault("runs", 0)


def settings():
    return A.Settings(**st.session_state["applied"])


def pending_settings():
    ss = st.session_state
    d = {k: ss[f"set_{k}"] for k in asdict(A.DEFAULTS)}
    d["budget"] = round(float(ss["set_budget_m"]) * 1e6, 2)
    for k, w in PCT_KEYS.items():
        d[k] = round(float(ss[w]) / 100, 6)
    d["n"] = int(d["n"]); d["seed"] = int(d["seed"])
    return A.Settings(**d)


def settings_changed():
    ss = st.session_state
    return pending_settings() != settings() or ss["set_activity_basis"] != ss["applied_activity_basis"]


# ------------------------------------------------------------------ cached model runs
@st.cache_resource(show_spinner=False, max_entries=8)
def _analysis(skey, akey, alabel):
    return A.run(A.Settings(**dict(skey)), dict(akey) if akey else None, alabel)


@st.cache_resource(show_spinner=False, max_entries=8)
def _switching(skey, akey, alabel):
    return A.switching(_analysis(skey, akey, alabel))


@st.cache_resource(show_spinner=False, max_entries=8)
def _discount(skey, akey):
    return A.discount_switch(A.Settings(**dict(skey)), activity=dict(akey) if akey else None)


@st.cache_resource(show_spinner=False, max_entries=8)
def _voi(skey, akey, alabel):
    return A.value_of_information(_analysis(skey, akey, alabel))


@st.cache_resource(show_spinner=False, max_entries=8)
def _tornado(skey, akey, alabel):
    return A.tornado(_analysis(skey, akey, alabel))


@st.cache_resource(show_spinner=False, max_entries=8)
def _explanation(skey, akey, alabel, data_text, llm_desc):
    r = _analysis(skey, akey, alabel)
    return X.explain(r, _voi(skey, akey, alabel), _switching(skey, akey, alabel), _discount(skey, akey),
                     _tornado(skey, akey, alabel)[1], data_text)


def keys(ctx):
    s = settings()
    act = ctx.get("activity_used")
    return s.key(), (tuple(sorted(act.items())) if act else None), ctx.get("activity_label")


def result(ctx):
    return _analysis(*keys(ctx))


def switching(ctx):
    return _switching(*keys(ctx))


def discount(ctx):
    k = keys(ctx)
    return _discount(k[0], k[1])


def voi(ctx):
    return _voi(*keys(ctx))


def tornado(ctx):
    return _tornado(*keys(ctx))


def explanation(ctx):
    return _explanation(*keys(ctx), ctx.get("data_text", ""), llm.describe())


# ------------------------------------------------------------------ plant data
@st.cache_resource(show_spinner=False, max_entries=8)
def _base_ledger(src_key, csv_text, year, site, name):
    return ES.Ledger(pd.read_csv(io.StringIO(csv_text), dtype={"period": str}), year, site, source_name=name)


@st.cache_resource(show_spinner=False, max_entries=8)
def _classify(src_key, csv_text):
    raw = pd.read_csv(io.StringIO(csv_text), dtype={"period": str})
    return C.classify(raw)


@st.cache_resource(show_spinner=False, max_entries=8)
def _anomalies(src_key, raw_hash, _ledger, year):
    return AN.detect(_ledger.cells, _ledger.hist_cells, year)


@st.cache_resource(show_spinner=False, max_entries=8)
def _challengers(src_key, raw_hash, _ledger):
    return IM.challengers(_ledger)


def raw_for(src):
    """(raw dataframe, display name, truth labels or None)."""
    if src == "demo":
        return DSet.demo_raw(), "SYNTHETIC demo records", None
    if src == "severe":
        return DSet.severe_raw(), "SYNTHETIC severe-gap records", None
    if src == "unlabelled":
        raw, truth = DSet.unlabelled_raw()
        return raw, "SYNTHETIC unlabelled ERP export", truth
    up = st.session_state.get("upload")
    if up is None:
        return None, None, None
    return pd.read_csv(io.StringIO(up["text"]), dtype={"period": str}), up["name"], None


def plant_context(src):
    """Everything the pages need about the selected plant-data source, with the reviewer's decisions applied."""
    ss = st.session_state
    raw, name, truth = raw_for(src)
    ctx = dict(src=src, name=name, raw=raw, truth=truth, ledger=None, base=None, classification=None, problem=None,
               status="No data", anomalies=None, activity=None, annual=None, set_aside=None)
    if raw is None:
        return ctx
    if C.needs_classification(raw):
        csv_text = raw.to_csv(index=False)
        cl = _classify(src, csv_text)
        ctx["classification"] = cl
        mapping = ss["class_map"].get(src)
        if mapping is None:
            ctx["status"] = "Awaiting stream classification"
            return ctx
        mapped, aside = C.apply_mapping(raw, pd.Series(mapping))
        ctx["set_aside"] = aside
        raw = mapped
    try:
        unknown = __import__("carbon_iq.dataquality.quality", fromlist=["validate_schema"]).validate_schema(raw)
        years = sorted({int(str(x)[:4]) for x in raw["period"].dropna()})
        sites = sorted(raw["site"].dropna().astype(str).unique())
    except Exception as e:  # noqa: BLE001
        ctx.update(problem=f"File not usable: {e}", status="Invalid file")
        return ctx
    year = ss.get(f"year_{src}", years[-1]) if years else None
    year = year if year in years else years[-1]
    site = ss.get(f"site_{src}", sites[0]) if sites else None
    site = site if site in sites else sites[0]
    ctx.update(years=years, sites=sites, year=year, site=site, unknown=unknown)
    base = _base_ledger(src, raw.to_csv(index=False), year, site, name)
    L = copy.deepcopy(base)
    adopt = ss["ml_adopt"].get(src, {})
    if adopt:
        ch = _challengers(src, base.raw_hash, base)
        for (per, stm), on in adopt.items():
            if on:
                row = ch[(ch.period == per) & (ch.stream == stm)]
                if len(row) and row.iloc[0].gate_passed:
                    IM.adopt(L, row.iloc[0].to_dict(), "plant-data reviewer")
    for (per, stm), dec in ss["decisions"].get(src, {}).items():
        if dec == "pending" or (adopt.get((per, stm)) and dec == "approve"):
            continue
        try:
            L.decide(site, per, stm, dec, "plant-data reviewer")
        except (ValueError, KeyError):
            pass
    an = _anomalies(src, base.raw_hash, base, year)
    review = ss["anom_review"].get(src, {})
    for per, dec in review.items():
        if dec != "pending":
            L.events.append(dict(time=ES._now(), action=f"ml_flag_{dec}", by="plant-data reviewer", detail=f"Isolation Forest flag {per}"))
    act, prob, ann = A.data_from_ledger(L)
    flagged = list(an["flags"].period) if an.get("applied") else []
    pending_flags = [p for p in flagged if review.get(p, "pending") == "pending"]
    if act is None:
        status = "Blocked"
    elif pending_flags:
        status = "Awaiting anomaly review"
    else:
        status = "Approved"
    ctx.update(base=base, ledger=L, anomalies=an, activity=act, problem=prob, annual=ann, status=status,
               pending_flags=pending_flags, anomaly_review=review)
    return ctx


def data_text(pc):
    if pc["ledger"] is None:
        return f"Plant data: {pc['status'].lower()}."
    t = pc["ledger"].table
    n_est = int(t.decision.isin(["approved", "change_overridden"]).sum())
    n_pend = int((t.decision == "pending").sum())
    return (f"Plant data ({pc['name']}, {pc['year']}): baseline status {pc['status']}; {n_est} approved estimate(s), "
            f"{n_pend} record(s) pending review; original records kept unchanged (sha256 {pc['ledger'].raw_hash[:12]}…).")


def analysis_context(pc):
    """Decide which activity data the applied analysis uses (approved plant data only when approved)."""
    ss = st.session_state
    want = ss["applied_activity_basis"]
    ctx = dict(activity_used=None, activity_label=None, basis_note="Reference activity data (assumption register, model v1.3).")
    if want == "plant":
        if pc.get("status") == "Approved" and pc.get("activity"):
            ctx.update(activity_used=pc["activity"], activity_label=pc["name"],
                       basis_note=f"Approved plant data: {pc['name']} ({pc['year']}).")
        else:
            ctx["basis_note"] = (f"Approved plant data requested, but the plant-data baseline is '{pc.get('status')}'. Results use the "
                                 "reference activity data until the baseline is approved.")
            ctx["fallback"] = True
    ctx["data_text"] = data_text(pc)
    return ctx


def all_insights(pc, ctx):
    data = I.data_insights(pc.get("ledger"), pc.get("anomalies"), pc.get("classification"),
                           pc.get("problem") if pc.get("ledger") is not None else None)
    if pc.get("classification") is not None and st.session_state["class_map"].get(pc["src"]) is not None:
        data = [i for i in data if i.kind != "ML classification"]
    res = result(ctx)
    dec = I.decision_insights(res, voi(ctx), switching(ctx), discount(ctx), tornado(ctx)[1])
    return I.rank(data + dec)
