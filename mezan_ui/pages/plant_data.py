"""2 · Plant Data Intelligence - can I trust my operational data? Upload, AI-assisted classification, rule-based quality
checks, Isolation Forest anomaly review, statistical estimates with reviewer approval, gated ML challengers, annual
totals, audit trail. Every decision rule, refusal rule and reviewer control of the data-quality module is unchanged."""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from carbon_iq.dataquality import estimate as ES
from carbon_iq.dataquality import quality as DQ
from mezan_ai import anomaly as AN
from mezan_ai import classifier as C
from mezan_ai import imputation as IM
from mezan_platform import datasets as DSet
from .. import components as CP
from .. import state as S
from .. import theme as TH

DECISIONS = ["pending", "approve", "reject", "keep", "confirm_zero", "override_change"]
DEC_LABEL = {"pending": "Pending review", "approve": "Approve estimate", "reject": "Reject · keep gap open",
             "keep": "Keep reported value", "confirm_zero": "Confirm zero is real", "override_change": "Override change refusal"}
DEC_FROM = {v: k for k, v in DEC_LABEL.items()}
DEC_HELP = ("Approve estimate = use it in the baseline · Reject = leave the gap open · Keep reported value = a flagged outlier is "
            "real · Confirm zero = a suspected zero is real · Override change refusal = the flagged operating change did not happen "
            "(a labelled fallback estimate is used)")
ISSUE_TEXT = {
    "MISSING_ROW": "Missing monthly record", "DUPLICATE_CONFLICT": "Conflicting duplicate records",
    "DUPLICATE_IDENTICAL": "Identical duplicate (merged)", "OUTLIER": "Unusual consumption",
    "OPERATIONAL_CHANGE": "Change in operating conditions", "BLANK_OR_NONNUMERIC": "Blank or non-numeric value",
    "NEGATIVE_VALUE": "Negative value", "SUSPECTED_MISSING_ZERO": "Zero that looks like a missing reading",
    "LEGITIMATE_ZERO": "Genuine zero (intermittent use)", "UNIT_CONVERTED": "Unit converted to the standard unit",
    "SUSPECT_UNIT_SCALE": "Possible unit-scale error", "UNKNOWN_STREAM": "Unknown data stream", "UNKNOWN_UNIT": "Unknown unit",
    "ZERO_PRODUCTION": "Zero production", "PRODUCTION_ANOMALY": "Unusual production level",
    "LEVEL_CHANGE_BETWEEN_YEARS": "Level change between years", "TOO_FEW_MEASURED": "Too few measured months to estimate",
    "GAP_TOO_LONG": "Gap too long to estimate", "ESTIMATE_UNRELIABLE": "Estimate too unreliable to use",
    "NO_ELIGIBLE_METHOD": "No eligible estimation method", "UNRESOLVED": "Unresolved"}
STATUS_TEXT = {"missing": "Missing", "outlier": "Unusual value", "suspected_zero": "Suspected missing zero", "measured": "Measured",
               "converted": "Measured (unit converted)", "estimated": "Estimated"}
METHOD_SHORT = {"intensity": "Production intensity", "seasonal_history": "Seasonal history", "mean": "Mean of measured months",
                "ml_ridge": "Ridge regression (ML)", "ml_forest": "Random forest (ML)", "": "—", None: "—"}
SEV_TEXT = {"error": "Needs review", "warning": "Check", "info": "Information"}


def readable(code_text):
    code = str(code_text).split(":")[0].strip()
    return ISSUE_TEXT.get(code, code.replace("_", " ").capitalize())


def stream_label(s):
    return DQ.STREAMS.get(s, {}).get("label", str(s).replace("_", " "))


def stream_unit(s):
    return DQ.STREAMS.get(s, {}).get("unit", "")


def _bump(src):
    st.session_state["editor_ver"][src] = st.session_state["editor_ver"].get(src, 0) + 1


def _bulk_approve(src, base, include_outliers=False, override=False):
    store = st.session_state["decisions"].setdefault(src, {})
    t = base.table[base.table.decision == "pending"]
    for _, r in t.iterrows():
        if r.refusal:
            if override and str(r.refusal).startswith("OPERATIONAL_CHANGE") and r.fallback_estimate == r.fallback_estimate:
                store[(r.period, r.stream)] = "override_change"
            continue
        if r.status == "outlier" and not include_outliers:
            continue
        store[(r.period, r.stream)] = "approve"
    _bump(src)


def _reset(src):
    for k in ("decisions", "ml_adopt", "anom_review"):
        st.session_state[k].pop(src, None)
    _bump(src)


def _ai_eval():
    f = TH.ROOT / "outputs" / "ai" / "ai_evaluation.json"
    return json.loads(f.read_text()) if f.exists() else None


# ------------------------------------------------------------------ 1 operational data
def source_selector():
    ss = st.session_state
    c = st.columns([3, 1], vertical_alignment="bottom")
    c[0].radio("Dataset", list(DSet.SOURCES), key="plant_src", horizontal=True, format_func=lambda k: DSet.SOURCES[k])
    c[1].download_button("CSV template", DSet.template_csv(), "mezan_plant_data_template.csv", key="tmpl_dl",
                         icon=":material/download:", use_container_width=True)
    if ss["plant_src"] == "upload":
        with st.container(border=True):
            up = st.file_uploader("Upload monthly records (CSV, long format)", type="csv", key="uploader",
                                  help="Columns: site, period (YYYY-MM), stream or description, value, unit [, record_id, source, note].")
            st.caption("Streams and units: " + " · ".join(f"{c_['label']} ({c_['unit']})" for c_ in DQ.STREAMS.values())
                       + ". Rows without a recognised stream are classified by Mezan and confirmed by you. Include the previous "
                         "year to enable seasonal estimates, change detection and ML anomaly detection.")
        if up is not None:
            text = up.getvalue().decode("utf-8", errors="replace")
            if (ss["upload"] or {}).get("text") != text:
                ss["upload"] = dict(name=up.name, text=text)
                for k in ("decisions", "ml_adopt", "anom_review", "class_map"):
                    ss[k].pop("upload", None)
                st.rerun()


def classification_step(pc):
    src, cl, raw = pc["src"], pc["classification"], pc["raw"]
    confirmed = st.session_state["class_map"].get(src) is not None
    TH.section(st, TH.label("ml", "AI-assisted") + "Stream classification",
               "Unlabelled utility, fuel-card and ERP records are matched to Mezan's energy and production streams before any check runs.")
    TH.cards(st, [("Records", f"{len(cl)}", pc["name"], "neutral"),
                  ("Assigned by rules", int((cl.method == "rule").sum()), "keywords + unit compatibility", "neutral"),
                  ("Assigned by ML text model", int((cl.method == "ml").sum()), "TF-IDF + logistic regression", "gold"),
                  ("Need a reviewer", int((cl.method == "unresolved").sum()), "never guessed", "warn" if (cl.method == "unresolved").any() else "ok")])
    if pc.get("truth") is not None:
        ok = int((cl.proposed_stream == pc["truth"]).sum())
        st.info(f"Demo check against the known synthetic labels: {ok} of {len(cl)} proposals are correct; "
                f"{int((cl.method == 'unresolved').sum())} are left for the reviewer; "
                f"{int(((cl.proposed_stream != pc['truth']) & (cl.method != 'unresolved')).sum())} are wrong.")
    view = pd.DataFrame({"Period": raw.period, "Description": raw.get("description", raw.get("stream", "")), "Unit": raw.unit,
                         "Value": pd.to_numeric(raw.value, errors="coerce").round(1), "Stream": cl.proposed_stream,
                         "Assigned by": cl.method_label, "ML probability": cl.ml_probability.round(2), "Evidence": cl.evidence})
    order = cl.method.map({"unresolved": 0, "ml": 1, "rule": 2, "provided": 3}).sort_values(kind="stable").index
    view = view.loc[order]
    if confirmed:
        mp = st.session_state["class_map"][src]
        view["Stream"] = [mp.get(i, "") for i in view.index]
    ed = st.data_editor(view, key=f"cls_ed_{src}_{st.session_state['editor_ver'].get(src, 0)}", height=320, width="stretch",
                        disabled=[c for c in view.columns if c != "Stream"],
                        column_config={"Stream": st.column_config.SelectboxColumn("Stream (confirm)", options=[""] + list(DQ.STREAMS)),
                                       "ML probability": st.column_config.NumberColumn("ML probability", format="%.2f",
                                                                                       help="Model output, not a calibrated confidence.")})
    st.caption("Rules decide first; the text model proposes a stream only when rules cannot, and only among streams whose unit "
               "matches. Unassigned records are set aside — their months count as missing, never as zero.")
    c = st.columns([1.4, 1, 2.6])
    if c[0].button("Confirm stream assignments", type="primary", key="cls_confirm", icon=":material/check:"):
        st.session_state["class_map"][src] = {i: s for i, s in ed["Stream"].items()}
        st.rerun()
    if confirmed and c[1].button("Edit again", key="cls_reset"):
        st.session_state["class_map"].pop(src, None)
        _bump(src)
        st.rerun()
    if confirmed and pc.get("set_aside") is not None and len(pc["set_aside"]):
        st.warning(f"{len(pc['set_aside'])} record(s) have no stream and were set aside (their months count as missing, never zero).")


# ------------------------------------------------------------------ 3 anomaly detection
def anomaly_step(pc):
    src, an, base = pc["src"], pc["anomalies"], pc["base"]
    TH.section(st, TH.label("ml", "Machine learning") + "AI-powered anomaly detection · Isolation Forest (machine learning)",
               "Machine learning identifies unusual combinations of energy consumption and operational activity.", anchor="anomaly")
    rules = base.cells[base.cells.status == "outlier"]
    with st.container(border=True):
        k = st.columns([1.15, 1], gap="large")
        with k[0]:
            if not an["applied"]:
                st.markdown(TH.label("ml", "Isolation Forest · not applied"), unsafe_allow_html=True)
                st.info("ML was not applied: " + an["reason"])
            else:
                TH.cards(st, [("Method", "Isolation Forest", f"{len(an.get('features', []))} month-level features · {AN.N_TREES} trees", "neutral"),
                              ("Months scored", f"{an['n_months']}", f"{an['n_months_imputed']} with one feature at its median", "neutral"),
                              ("Flagged in reporting year", f"{an['n_flagged']}", f"score ≥ {an['threshold']:.2f}",
                               "warn" if an["n_flagged"] else "ok")])
                sc = an["scores"].sort_values("period")
                cur = [p.startswith(str(pc["year"])) for p in sc.period]
                fig = go.Figure(go.Bar(x=sc.period, y=sc.anomaly_score,
                                       marker_color=[TH.BAD if f_ and c_ else (TH.PURPLE if c_ else TH.LAV2) for f_, c_ in zip(sc.flagged, cur)],
                                       hovertemplate="%{x}<br>isolation score %{y:.3f}<extra></extra>"))
                fig.add_hline(y=an["threshold"], line_dash="dash", line_color=TH.BAD, annotation_text=f"flag threshold {an['threshold']:.2f}",
                              annotation_position="top left", annotation_font=dict(size=11, color=TH.BAD))
                fig.update_yaxes(range=[0.3, max(0.72, float(sc.anomaly_score.max()) + 0.05)], title="isolation score")
                fig.update_xaxes(title="month (grey = previous year, purple = reporting year, red = flagged)", tickangle=-45)
                CP.chart(TH.style_fig(fig, 300, "Isolation score by month", legend=None),
                         "Higher = more unusual combination of intensities. Scores rank months; they are not probabilities.", key="an_scores")
        with k[1]:
            st.markdown("**Rule-based checks** · robust z-score of energy intensity and unit-scale rule")
            if len(rules):
                st.dataframe(pd.DataFrame({"Period": rules.period, "Data stream": rules.stream.map(stream_label),
                                           "Finding": rules.issues.map(lambda x: "; ".join(readable(i) for i in x
                                                                                           if i.startswith(("OUTLIER", "SUSPECT"))))}),
                             hide_index=True, width="stretch")
            else:
                st.caption("No rule-based outliers.")
            ev = _ai_eval()
            if ev:
                a = ev["anomaly"]
                t = f"{an.get('threshold', AN.THRESHOLD):.2f}"
                st.markdown(f"**How the two compare** · on {a['facilities']} synthetic test plants the rules detected "
                            f"{a['rule_detection_rate']:.1%} of injected anomalies and the Isolation Forest {a['if_detection_rate_' + t]:.1%} "
                            f"({a['if_false_alarms_per_year_' + t]:.2f} false alarms per plant-year); together "
                            f"{a['combined_detection_rate_' + t]:.1%}. Synthetic evidence only.")
        if an["applied"] and an["n_flagged"]:
            review = st.session_state["anom_review"].setdefault(src, {})
            cmp = AN.compare_with_rules(an, base.cells)
            st.markdown("**Flagged periods — investigate, then confirm or dismiss.** Original records are never changed by a flag.")
            view = pd.DataFrame({"Period": cmp.period, "Isolation score": cmp.anomaly_score.round(3), "Why it was flagged": cmp.drivers,
                                 "Also found by rules": cmp.rule_based_issues.map(lambda x: readable(x) if x else "no"),
                                 "Review": [review.get(p, "pending") for p in cmp.period]})
            ed = st.data_editor(view, key=f"an_ed_{src}_{st.session_state['editor_ver'].get(src, 0)}", hide_index=True, width="stretch",
                                disabled=[c_ for c_ in view.columns if c_ != "Review"],
                                column_config={"Review": st.column_config.SelectboxColumn("Review", options=["pending", "confirmed", "dismissed"],
                                                                                          required=True),
                                               "Isolation score": st.column_config.NumberColumn(format="%.3f", help="Not a probability.")})
            moved = False
            for p, v in zip(ed.Period, ed.Review):
                if review.get(p, "pending") != v:
                    review[p] = v
                    moved = True
            if moved:
                st.rerun()
            with st.expander("Features used and how a flag is explained"):
                st.markdown("Features per month: " + ", ".join(an.get("features", [])) + ". A flag lists the two features furthest from "
                            "their median in robust standard deviations. Confirmed flags are recorded in the audit trail; to change a "
                            "value use the estimate decisions below. The baseline is approved only when every flag has been reviewed.")
                st.dataframe(an["flags"].drop(columns=["why"], errors="ignore"), hide_index=True, width="stretch")


# ------------------------------------------------------------------ 5 ML estimate assistance
def ml_step(pc):
    src, base = pc["src"], pc["base"]
    TH.section(st, TH.label("ml", "Machine learning") + TH.label("stat", "Statistical benchmark") + "Machine-learning estimate assistance",
               "Compare machine-learning estimates with statistical estimates to determine which performs better under back-testing.")
    ev = _ai_eval()
    if ev and "backtest_error_mean" in ev["imputation"]:
        im = ev["imputation"]
        b = im["backtest_error_mean"]
        sel = im.get("selected_model_counts", {})
        true = {r["selected_model"]: r for r in im.get("true_error_by_selected_model", [])}
        TH.cards(st, [("Statistical benchmark", f"{im['statistical_mape']:.2%}", f"error vs known truth · back-test {b['statistical']:.2%}", "neutral"),
                      ("Ridge regression", f"{b['ridge']:.2%}", f"mean back-test error · chosen for {sel.get('ridge', 0)} gaps"
                       + (f" · true error {true['ridge']['ml_ape']:.2%} vs {true['ridge']['stat_ape']:.2%} statistical" if "ridge" in true else ""),
                       "ok" if "ridge" in true and true["ridge"]["ml_ape"] < true["ridge"]["stat_ape"] else "neutral"),
                      ("Random forest", f"{b['forest']:.2%}", f"mean back-test error · chosen for {sel.get('forest', 0)} gaps"
                       + (f" · true error {true['forest']['ml_ape']:.2%} vs {true['forest']['stat_ape']:.2%} statistical" if "forest" in true else ""),
                       "warn" if "forest" in true and true["forest"]["ml_ape"] >= true["forest"]["stat_ape"] else "neutral"),
                      ("Gated policy (used)", f"{im['gated_policy_mape']:.2%}", f"ML only where the gate passes ({im['gate_pass_share']:.0%} of gaps)",
                       "gold")])
        st.caption(f"Synthetic evaluation: {im['facilities']} facilities, {im['gaps_with_both']} removed values with known truth. ML helped "
                   "overall, mostly through ridge regression; where the random forest was chosen it did slightly worse than the "
                   "statistical method — one reason the gate and reviewer choice stay in place. Not yet evaluated on real plant data.")
    done = st.session_state["ml_eval"].get(src)
    if not done and st.button("Back-test ML challengers on this dataset", key="ml_eval_btn", icon=":material/model_training:"):
        st.session_state["ml_eval"][src] = True
        done = True
    if not done:
        st.caption(f"An ML estimate can be used only if its back-test error is below {IM.GATE_RATIO:.0%} of the statistical method's, it "
                   "does not bypass a refusal rule, and a reviewer chooses it. Nothing is replaced automatically.")
        return
    with st.spinner("Back-testing ridge regression and random forest…"):
        ch = S._challengers(src, base.raw_hash, base)
    if not len(ch):
        st.info("No pending gaps: nothing to estimate.")
        return
    adopt = st.session_state["ml_adopt"].setdefault(src, {})
    f = lambda x: x if (x == x and x is not None) else None  # noqa: E731
    view = pd.DataFrame({"Period": ch.period, "Data stream": ch.stream.map(stream_label),
                         "Statistical estimate": ch.statistical_estimate.round(1),
                         "Statistical error": ch.statistical_backtest_error.map(f), "Ridge error": ch.ridge_error.map(f),
                         "Forest error": ch.forest_error.map(f), "Best ML": ch.ml_model, "ML estimate": ch.ml_estimate.round(1),
                         "Eligible": ch.gate_passed.map(lambda x: "Eligible" if x else "Not eligible"), "Reason": ch.gate_reason,
                         "Use ML estimate": [bool(adopt.get((p, s_), False)) for p, s_ in zip(ch.period, ch.stream)]})
    pc_cfg = {c: st.column_config.NumberColumn(c, format="percent", help="Leave-one-out back-test error on measured months")
              for c in ("Statistical error", "Ridge error", "Forest error")}
    ed = st.data_editor(view, key=f"ml_ed_{src}_{st.session_state['editor_ver'].get(src, 0)}", hide_index=True, width="stretch",
                        disabled=[c for c in view.columns if c != "Use ML estimate"], column_config=pc_cfg)
    changed = False
    for (p, s_lab, use), ok, s_ in zip(zip(ed.Period, ed["Data stream"], ed["Use ML estimate"]), ch.gate_passed, ch.stream):
        val = bool(use) and bool(ok)
        if bool(use) and not ok:
            st.warning(f"{p} {s_lab}: the evidence gate did not pass, so the ML estimate cannot be used.")
        if adopt.get((p, s_), False) != val:
            adopt[(p, s_)] = val
            changed = True
    if changed:
        st.rerun()
    st.caption(f"{int(ch.gate_passed.sum())} of {len(ch)} gaps pass the evidence gate on this dataset. Ticking 'Use ML estimate' is the "
               "reviewer's approval; it is written to the audit trail.")


# ------------------------------------------------------------------ page
def render(fac, pc, ctx):
    ss = st.session_state
    TH.page_header(st, "Can I trust my operational data?", "Plant Data Intelligence",
                   "Transform incomplete operational records into reliable, reviewable investment inputs.")
    TH.section(st, "Operational data", "Upload or select electricity, fuel, production and operational records for your facility.")
    source_selector()
    if pc["raw"] is None:
        st.info("Upload a CSV or choose one of the synthetic datasets to start.")
        CP.next_action("Download the CSV template, fill in twelve or more months of records and upload it.")
        return
    if pc["problem"] and pc["ledger"] is None and pc["status"] == "Invalid file":
        st.error(pc["problem"])
        return
    if pc["classification"] is not None:
        classification_step(pc)
        if pc["ledger"] is None:
            st.info("Confirm the stream assignments to run the data-quality checks.")
            return
    src, L, base = pc["src"], pc["ledger"], pc["base"]
    c = st.columns([1, 1, 2.4], vertical_alignment="bottom")
    c[0].selectbox("Reporting year", pc["years"][::-1], key=f"year_{src}")
    c[1].selectbox("Site", pc["sites"], key=f"site_{src}")
    c[2].markdown(TH.label("synthetic" if src != "upload" else "measured", "Synthetic dataset" if src != "upload" else "Uploaded records")
                  + f'<span class="mz-note">{pc["name"]} · {len(base.raw)} records · SHA-256 {base.raw_hash[:16]}… · original kept '
                    "unchanged</span>", unsafe_allow_html=True)
    if pc.get("unknown"):
        st.warning("Ignored unknown streams: " + ", ".join(pc["unknown"]))

    # 2 data quality assessment
    TH.section(st, TH.label("rule", "Rule-based") + "Data quality assessment",
               "Identify missing, inconsistent or unusual records that could distort emissions calculations.")
    pend = int((L.table.decision == "pending").sum())
    complete = base.cells.status.isin(["measured", "converted"]).mean()
    TH.cards(st, [("Records checked", f"{len(base.raw)}", f"{len(base.cells)} stream-months in {pc['year']}", "neutral"),
                  ("Data completeness", f"{complete:.0%}", "measured or unit-converted", "ok" if complete >= 0.95 else "warn"),
                  ("Issues requiring review", f"{pend}", "missing, unusual or suspect records", "warn" if pend else "ok"),
                  ("Baseline approval", pc["status"], "gaps resolved and ML flags reviewed" if pc["status"] == "Approved"
                   else "see readiness below", TH.status_tone(pc["status"]))])
    CP.intelligence([i for i in S.all_insights(pc, ctx) if i.page in ("Plant Data", "Emissions")], "Mezan Intelligence · data",
                    groups=["Machine-learning findings", "Data-quality warnings"])
    sev = base.issues[base.issues.severity != "info"].copy()
    if len(sev):
        sev_view = pd.DataFrame({"Period": sev.period, "Data stream": sev.stream.map(stream_label), "Finding": sev.code.map(readable),
                                 "Severity": sev.severity.map(SEV_TEXT).fillna(sev.severity),
                                 "Detail": sev.detail.map(lambda d: d.split(":", 1)[1].strip() if ":" in str(d) else "")})
        flt = st.multiselect("Filter findings", sorted(sev_view.Finding.unique()), key=f"flt_{src}", placeholder="All findings")
        if flt:
            sev_view = sev_view[sev_view.Finding.isin(flt)]
        st.dataframe(sev_view, hide_index=True, width="stretch", height=min(380, 38 + 35 * len(sev_view)))
    for _, w in base.table[base.table.warning != ""].iterrows():
        st.warning(f"**{w.period} · {stream_label(w.stream)}** — {readable(w.warning)}. {w.warning}"
                   + (f" → estimation refused: {readable(w.refusal)} ({w.refusal})" if w.refusal else ""))
    with st.expander("Technical evidence: original codes and status by stream"):
        st.dataframe(base.issues, hide_index=True, width="stretch")
        st.dataframe(DQ.summary(base.cells), width="stretch")

    anomaly_step(pc)

    # 4 missing-data estimation
    TH.section(st, TH.label("stat", "Statistical estimate") + "Missing-data estimation",
               "Estimate missing operational values using available evidence, with uncertainty and human approval.", anchor="estimates")
    gaps = base.table[base.table.decision == "pending"].copy()
    b = st.columns(4)
    if b[0].button("Approve all eligible estimates", key="bulk_approve", icon=":material/done_all:", use_container_width=True):
        _bulk_approve(src, base); st.rerun()
    if b[1].button("…and replace flagged outliers", key="bulk_outliers", use_container_width=True):
        _bulk_approve(src, base, include_outliers=True); st.rerun()
    if b[2].button("…and override change refusals", key="bulk_override", use_container_width=True,
                   help="Reviewer states the flagged operational change did not happen; labelled in the lineage."):
        _bulk_approve(src, base, include_outliers=True, override=True); st.rerun()
    if b[3].button("Reset all decisions", key="reset_dec", icon=":material/restart_alt:", use_container_width=True):
        _reset(src); st.rerun()
    if len(gaps):
        store = ss["decisions"].setdefault(src, {})
        adopt = ss["ml_adopt"].get(src, {})
        cur = L.table.set_index(["period", "stream"])
        get = lambda col: [cur.at[(p, s_), col] for p, s_ in zip(gaps.period, gaps.stream)]  # noqa: E731
        est, lo, hi, meth = get("estimate"), get("low95"), get("high95"), get("method")
        units = [stream_unit(s_) for s_ in gaps.stream]
        view = pd.DataFrame({
            "Period": gaps.period.values, "Data source": [stream_label(s_) for s_ in gaps.stream],
            "Detected issue": ["; ".join(readable(i) for i in x) for x in gaps.issues],
            "Proposed estimate": [f"{e:,.1f} {u}" if e == e and e is not None else "refused" for e, u in zip(est, units)],
            "Uncertainty range (95%)": [f"{a:,.0f} – {z:,.0f} {u}" if a == a and a is not None else "—" for a, z, u in zip(lo, hi, units)],
            "Estimation method": [METHOD_SHORT.get(m, m) for m in meth],
            "Refusal": [readable(r) + f" ({r.split(':')[0]})" if r else "" for r in gaps.refusal],
            "Review decision": [DEC_LABEL["approve"] if adopt.get((p, s_)) else DEC_LABEL[store.get((p, s_), "pending")]
                                for p, s_ in zip(gaps.period, gaps.stream)]})
        view["_s"] = gaps.stream.values
        ed = st.data_editor(view.drop(columns="_s"), hide_index=True, width="stretch", key=f"dec_ed_{src}_{ss['editor_ver'].get(src, 0)}",
                            disabled=[c_ for c_ in view.columns if c_ != "Review decision"],
                            column_config={"Review decision": st.column_config.SelectboxColumn("Review decision", options=list(DEC_LABEL.values()),
                                                                                               required=True, width="medium"),
                                           "Refusal": st.column_config.TextColumn("Refusal", width="medium"),
                                           "Detected issue": st.column_config.TextColumn("Detected issue", width="medium")})
        changed = False
        for p, s_, d in zip(ed.Period, view["_s"], ed["Review decision"]):
            d = DEC_FROM.get(d, d)
            if store.get((p, s_), "pending") != d and not (adopt.get((p, s_)) and d == "approve"):
                store[(p, s_)] = d
                changed = True
        if changed:
            st.rerun()
        st.caption(DEC_HELP + ".")
        with st.expander("How estimates and ranges are produced"):
            st.markdown("\n".join(f"- **{METHOD_SHORT[k]}** — {v}" for k, v in ES.METHOD_TEXT.items()))
            st.markdown(f"Ranges are 95% prediction intervals from leave-one-out back-tests, widened by a factor calibrated on synthetic "
                        f"hold-out data ({ES.CAL_MONTHLY:.3f}); re-fit on real data before relying on them. Estimation is refused when "
                        "too few months are measured, a gap is too long, an operating change is detected or the best estimate is too "
                        "unreliable. A missing value is never replaced by zero.")
    else:
        st.success("No gaps, outliers or suspected zeros found.")

    ml_step(pc)

    # 6 annual totals and readiness
    TH.section(st, "Annual totals and baseline readiness",
               "Consolidate reviewed operational records into annual values ready for emissions accounting.")
    ann = pc["annual"]
    tv = pd.DataFrame({"Data stream": ann.stream.map(stream_label), "Unit": ann.unit, "Measured months": ann.n_measured,
                       "Estimated months": ann.n_estimated, "Unresolved months": ann.n_unresolved,
                       "Measured total": ann.measured_total.round(1), "Estimated total": ann.estimated_total.round(1),
                       "Annual total": ann.total.round(1), "Status": ann.complete.map(lambda x: "Approved" if x else "Blocked · unresolved gaps")})
    st.dataframe(CP.highlight_status(tv), hide_index=True, width="stretch")
    if pc["status"] == "Approved":
        st.success("Plant-data baseline approved: every gap is resolved and every ML flag reviewed. Choose **Approved operational data** "
                   "under Advanced simulation settings and run the analysis to use it.")
    elif pc["status"] == "Awaiting anomaly review":
        st.warning(f"All gaps resolved, but {len(pc['pending_flags'])} Isolation Forest flag(s) still need a review decision "
                   "(see [anomaly detection](#anomaly)).")
    else:
        st.error(f"Baseline blocked — {pc['problem']}. Missing data are not counted as zero.")
        blk = L.table[(L.table.decision == "pending")]
        if len(blk):
            st.markdown("**Records blocking approval:** " + ", ".join(f"{r.period} {stream_label(r.stream)}" for _, r in blk.iterrows())
                        + " — review them in [Missing-data estimation](#estimates).")

    # 7 audit trail
    TH.section(st, "Audit trail", "Track original records, estimates, approvals and changes to ensure accountability.")
    ev = pd.DataFrame(L.events)
    if len(ev):
        ev = ev.iloc[::-1].rename(columns={"time": "Time (UTC)", "action": "Action", "by": "By", "detail": "Detail"})
        ev["Action"] = ev["Action"].astype(str).str.replace("_", " ").str.capitalize()
    st.dataframe(ev, hide_index=True, width="stretch", height=240)
    lin = L.lineage()
    c = st.columns([1, 1, 3])
    c[0].download_button("Data lineage (CSV)", lin.to_csv(index=False), "mezan_lineage.csv", key="lin_dl", icon=":material/download:",
                         use_container_width=True)
    c[1].download_button("Audit events (CSV)", pd.DataFrame(L.events).to_csv(index=False), "mezan_audit_events.csv", key="aud_dl",
                         icon=":material/download:", use_container_width=True)
    with st.expander("Full lineage: original value, estimate, decision and final value for every stream-month"):
        st.dataframe(lin[["period", "stream", "status", "method", "estimate", "decision", "decided_by", "final_value", "final_label"]],
                     hide_index=True, width="stretch", height=360)
    if pc["status"] == "Approved":
        CP.next_action("The operational baseline is approved — see what it means for the carbon footprint.", "Carbon & Emissions")
    else:
        CP.next_action("Resolve the highlighted records, review the ML flags, then approve the baseline. Until then the analysis "
                       "uses the reference data.")
