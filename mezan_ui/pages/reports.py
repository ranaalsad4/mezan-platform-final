"""6 · Reports & Evidence - can I explain, verify and defend this investment recommendation?
Executive decision report (HTML and PDF), exports, AI capability and evidence register, assumptions, sources, lineage,
reproducibility and documents. Every export is generated from the current analysis run."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from carbon_iq.assumptions import P
from mezan_ai import llm
from mezan_ai.capabilities import CAPABILITIES, NOT_AI
from mezan_platform import report as R
from .. import components as CP
from .. import state as S
from .. import theme as TH

ROOT = Path(__file__).resolve().parents[2]
DOCS = [("AI and ML methodology", "docs/AI_ML_METHODOLOGY.md"),
        ("A6 mathematical validation report", "docs/Mezan_A6_Mathematical_Validation_Report.docx"),
        ("A5 carbon and financial methodology", "docs/Mezan_A5_Carbon_Financial_Methodology.docx"),
        ("A4 missing-data report", "docs/Mezan_A4_Missing_Data_Report.docx"),
        ("A2 validation report", "docs/Mezan_A2_Validation_Report.docx"),
        ("A3 benchmark report", "docs/Mezan_A3_Benchmark_Report.docx"),
        ("MRC source-to-variable register", "docs/v2/Mezan_MRC_Source_Register.xlsx"),
        ("Data model workbook", "Mezan_Data_Model.xlsx")]
EVIDENCE_TEXT = {"external": "External published source", "derived": "Derived from cited values", "hypothetical": "Hypothetical assumption"}


def _mark():
    st.session_state["report_downloaded"] = True


def assumptions_df():
    return pd.DataFrame([{"Key": k, "Value": x.value, "Unit": x.unit, "Evidence": x.evidence, "Status": x.status,
                          "Distribution": str(x.dist) if x.dist else "fixed", "Published": x.published, "Geography": x.geography,
                          "Source / rationale": x.source, "URL": x.url} for k, x in P.items()])


def capability_matrix(ev, pc):
    """Capability register with live evaluation results (outputs/ai/ai_evaluation.json) and current status."""
    what = {"A": "Assigns unlabelled export records to energy and production streams", "B": "Flags months whose combination of energy "
            "intensities is unusual", "C": "Offers ML estimates for missing months when they beat the statistical estimator",
            "D": "Explains the recommendation in plain language from engine outputs", "E": "Selects and words the most important findings"}
    res = {}
    if ev:
        c, a, i = ev["classification"], ev["anomaly"], ev["imputation"]
        res["A"] = (f"Grouped CV: hybrid {c['hybrid_grouped_cv_accuracy']:.1%}, ML alone {c['ml_grouped_cv_accuracy']:.1%}; demo export "
                    f"{c['demo_export']['correct']}/{c['demo_export']['records']} correct, {c['demo_export']['wrong']} wrong")
        res["B"] = (f"Detection {a['if_detection_rate_0.55']:.1%} at {a['if_false_alarms_per_year_0.55']:.2f} false alarms/plant-year; "
                    f"with rules {a['combined_detection_rate_0.55']:.1%} (rules alone {a['rule_detection_rate']:.1%})")
        res["C"] = (f"Error vs truth: statistical {i['statistical_mape']:.2%}, gated policy {i['gated_policy_mape']:.2%}"
                    + (f"; back-test ridge {i['backtest_error_mean']['ridge']:.2%}, forest {i['backtest_error_mean']['forest']:.2%}"
                       if "backtest_error_mean" in i else ""))
    res["D"] = "Number-verification guard tested (invented figures rejected); live language model not evaluated"
    res["E"] = "Tested: insights change when results change"
    evals = {"A": "Synthetic grouped cross-validation + unseen demo export", "B": "60 synthetic plants, 40 injected anomalies",
             "C": "30 synthetic plants, removed values with known truth", "D": "Unit tests with a mocked model", "E": "Unit tests"}
    rows = [{"Capability": c["name"], "What it does": what[c["id"]], "Underlying method": c["technique"], "Implementation status": c["status"],
             "Evaluation performed": evals[c["id"]], "Current result": res.get(c["id"], "—"), "Limitations": c["limits"],
             "Evidence": c["evidence"]} for c in CAPABILITIES]
    rows.append({"Capability": "Language-model configuration (live)", "What it does": "Optional rewriting of the verified fact sheet",
                 "Underlying method": "OpenAI-compatible or Anthropic API via MEZAN_LLM_* environment variables",
                 "Implementation status": "Optional · " + llm.describe(), "Evaluation performed": "Not evaluated against a live endpoint",
                 "Current result": "Rule-based narrative in use" if not llm.config()["enabled"] else "Configured; outputs number-checked",
                 "Limitations": "Not required; the platform is fully usable without it", "Evidence": "mezan_ai/llm.py, tests/test_ai.py"})
    return pd.DataFrame(rows)


def render(fac, pc, ctx):
    res = S.result(ctx)
    TH.page_header(st, "Can I explain, verify and defend this investment recommendation?", "Reports & Evidence",
                   "Generate an executive-ready investment report supported by traceable data, transparent assumptions and "
                   "reproducible analysis.")
    with st.spinner("Preparing the report from the current run…"):
        sw, disc, v, ex = S.switching(ctx), S.discount(ctx), S.voi(ctx), S.explanation(ctx)
        tor = S.tornado(ctx)[1]
    data_hash = pc["ledger"].raw_hash if pc.get("ledger") is not None else None
    args = (res, fac, ex, v, sw, disc)
    kw = dict(data=ctx.get("data_text"), anomalies=pc.get("anomalies"), data_hash=data_hash, tornado=tor)
    html = R.executive_html(*args, **kw)
    rec = res["recommended"]
    TH.cards(st, [("Report covers", rec["portfolio"] if rec else "No feasible portfolio", f"{fac['name']} · {fac['year']}", "brand"),
                  ("Settings fingerprint", R.settings_hash(res["settings"])[:12], f"{res['settings']['n']:,} futures · seed {res['settings']['seed']}",
                   "neutral"),
                  ("Data basis", "Approved operational" if ctx.get("activity_used") else "Reference data", "activity data used", "neutral")])

    TH.section(st, "Report exports", "Every export is generated from the analysis run shown on screen.")
    c = st.columns(3, gap="small")
    c[0].download_button("Executive Decision Report (HTML)", html, "Mezan_Executive_Decision_Report.html", "text/html", key="dl_report",
                         type="primary", on_click=_mark, icon=":material/summarize:", use_container_width=True)
    try:
        pdf = R.executive_pdf(*args, **kw)
        c[1].download_button("Executive Decision Report (PDF)", pdf, "Mezan_Executive_Decision_Report.pdf", "application/pdf",
                             key="dl_pdf", type="primary", on_click=_mark, icon=":material/picture_as_pdf:", use_container_width=True)
    except Exception as e:  # noqa: BLE001 - never show a broken button; the HTML report prints to PDF
        c[1].caption(f"PDF export unavailable here ({type(e).__name__}); open the HTML report and print it to PDF.")
    c[2].download_button("Analysis results (JSON)", R.results_json(res, v, sw, disc, ex, data_hash), "mezan_results.json",
                         "application/json", key="dl_json", on_click=_mark, icon=":material/data_object:", use_container_width=True)
    c = st.columns(3, gap="small")
    port = pd.DataFrame([{k: v_ for k, v_ in r.items() if k != "ids"} for r in res["table"]])
    c[0].download_button("Portfolio comparison (CSV)", port.to_csv(index=False), "mezan_portfolios.csv", key="dl_port",
                         icon=":material/table_view:", use_container_width=True)
    c[1].download_button("Assumptions register (CSV)", assumptions_df().to_csv(index=False), "mezan_assumptions.csv", key="dl_ass",
                         icon=":material/list_alt:", use_container_width=True)
    if pc.get("ledger") is not None:
        c[2].download_button("Data lineage and audit records (CSV)", pc["ledger"].lineage().to_csv(index=False), "mezan_lineage.csv",
                             key="dl_lin_top", icon=":material/history:", use_container_width=True)
    st.caption("The PDF is generated directly (A4, automatic page breaks, repeated table headers). The HTML report opens in any browser "
               "and can also be printed to PDF.")

    tabs = st.tabs(["Executive report", "AI capability and evidence", "Assumptions", "Sources and references", "Limitations",
                    "Data lineage", "Reproducibility", "Documents"])
    with tabs[0]:
        st.html(R.report_body_html(R.report_model(*args, **kw)))
    with tabs[1]:
        f = ROOT / "outputs" / "ai" / "ai_evaluation.json"
        ev = json.loads(f.read_text()) if f.exists() else None
        st.markdown("Exactly what AI and machine learning contribute — and what they do not. Status terms: **Implemented** (runs in the "
                    "app), **Optional** (off unless configured), **Evaluated** (synthetic evaluation in tools/evaluate_ai.py), "
                    "**Partially implemented**, and **not externally validated** (applies to everything).")
        st.dataframe(capability_matrix(ev, pc), hide_index=True, width="stretch", height=330,
                     column_config={c_: st.column_config.TextColumn(c_, width="medium") for c_ in ("What it does", "Underlying method",
                                                                                                  "Current result", "Limitations")})
        st.info(NOT_AI)
        if ev:
            a, i, cl = ev["anomaly"], ev["imputation"], ev["classification"]
            TH.cards(st, [("Classification · held-out templates", f"{cl['hybrid_grouped_cv_accuracy']:.1%}",
                           f"ML alone {cl['ml_grouped_cv_accuracy']:.1%}", "neutral"),
                          ("Anomaly detection · rules + IF", f"{a['combined_detection_rate_0.55']:.1%}", f"rules alone {a['rule_detection_rate']:.1%}",
                           "neutral"),
                          ("Estimate error · gated ML policy", f"{i['gated_policy_mape']:.2%}", f"statistical {i['statistical_mape']:.2%}", "neutral"),
                          ("Evidence type", "Synthetic", "known truth; not real plants", "warn")])
            st.download_button("AI evaluation results (JSON)", f.read_text(), "mezan_ai_evaluation.json", key="dl_ai",
                               icon=":material/download:")
            with st.expander("Full evaluation results"):
                st.json(ev)
    with tabs[2]:
        a = assumptions_df()
        flt = st.multiselect("Evidence type", sorted(a.Evidence.unique()), key="ass_flt", placeholder="All",
                             format_func=lambda x: EVIDENCE_TEXT.get(x, x))
        if flt:
            a = a[a.Evidence.isin(flt)]
        st.dataframe(a.astype({"Value": str}), hide_index=True, width="stretch", height=480,
                     column_config={"URL": st.column_config.LinkColumn("URL", display_text="open")})
        st.caption("External = cited source; derived = computed from cited values; hypothetical = illustrative case assumption. No input is "
                   "a measured factory observation.")
    with tabs[3]:
        st.markdown("**Methodological foundations** — these support the methods used, not Mezan's synthetic or scenario results.")
        st.dataframe(pd.DataFrame(R.METHOD_REFS, columns=["Reference", "Supports", "Link"]), hide_index=True, width="stretch",
                     column_config={"Link": st.column_config.LinkColumn("Link", display_text="open")})
        st.markdown("**Sources of numerical inputs** (from the assumption register)")
        src = assumptions_df()
        src = src[src.URL.astype(str).str.startswith("http")][["Key", "Value", "Unit", "Evidence", "Source / rationale", "URL"]]
        st.dataframe(src.astype({"Value": str}), hide_index=True, width="stretch",
                     column_config={"URL": st.column_config.LinkColumn("URL", display_text="open")})
    with tabs[4]:
        for x in R.LIMITATIONS:
            st.markdown(f"- {x}")
    with tabs[5]:
        if pc.get("ledger") is not None:
            st.markdown(f"Source: **{pc['name']}** · reporting year {pc['year']} · SHA-256 `{pc['ledger'].raw_hash}`")
            lin = pc["ledger"].lineage()
            st.dataframe(lin[["period", "stream", "status", "method", "estimate", "decision", "decided_by", "final_value", "final_label"]],
                         hide_index=True, width="stretch", height=360)
            st.download_button("Lineage (CSV)", lin.to_csv(index=False), "mezan_lineage.csv", key="dl_lin")
            st.download_button("Audit events (CSV)", pd.DataFrame(pc["ledger"].events).to_csv(index=False), "mezan_audit_events.csv",
                               key="dl_aud")
        else:
            st.info("No plant data loaded.")
        st.caption(ctx.get("basis_note", ""))
    with tabs[6]:
        st.dataframe(pd.DataFrame([(k, str(v_)) for k, v_ in R.reproducibility(res, data_hash).items()], columns=["Item", "Value"]),
                     hide_index=True, width="stretch")
        st.caption("Same settings + same seed + same data hash ⇒ identical results. The saved report run (outputs/results.json) is "
                   "regenerated with `python run_all.py`; the AI evaluation with `python tools/evaluate_ai.py`.")
    with tabs[7]:
        cols = st.columns(2)
        j = 0
        for title, rel in DOCS:
            f = ROOT / rel
            if f.exists():
                cols[j % 2].download_button(title, f.read_bytes(), f.name, key=f"doc_{f.name}", icon=":material/description:",
                                            use_container_width=True)
                j += 1
    CP.next_action("Share the PDF with the investment committee, together with the AI capability register.")
