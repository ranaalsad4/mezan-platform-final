"""Human-readable names for model inputs and portfolios (presentation only)."""
from carbon_iq.assumptions import P, PROJECTS

PARAM_LABELS = {
    "c_saving_frac": "Compressed-air savings (share of compressed-air electricity)",
    "b_saving_frac": "Motor-system savings (share of motor electricity)",
    "tariff": "Electricity tariff",
    "pv_capex_kw": "Solar PV capital cost",
    "pv_yield": "Solar PV specific yield",
    "gas_price_usd": "Natural-gas price",
    "c_capex": "Compressed-air project cost",
    "b_capex": "Motor-system project cost",
    "pv_degradation": "Solar PV degradation",
    "ef_grid": "Grid emission factor",
    "ef_steel_alt": "Lower-carbon steel factor",
    "discount_rate": "Discount rate",
    "elec_mwh": "Electricity use",
    "gas_gj": "Natural-gas use",
}
SHORT = {"A": "Solar PV", "B": "Efficient motors + VSDs", "C": "Compressed-air repairs", "D": "Waste-heat recovery",
         "E": "Forklift electrification", "F": "Lower-carbon steel"}


def label(key):
    return PARAM_LABELS.get(key, key.replace("_", " "))


def unit(key):
    return P[key].unit if key in P else ""


def portfolio_names(code):
    if not code or code in ("(none)", "none feasible", "infeasible"):
        return code or "none"
    return ", ".join(f"{i} {SHORT[i]}" for i in code.split("+"))


def project_name(i):
    return PROJECTS[i]


def fmt_value(key, x, digits=1):
    u = unit(key)
    if u.startswith("of ") or u in ("fraction", "real, per year"):
        return f"{x:.{digits}%}"
    if u == "SAR/kWh":
        return f"{x:.3f} SAR/kWh"
    if u == "USD/MMBtu":
        return f"{x:.2f} USD/MMBtu"
    if u == "SAR":
        return f"SAR {x:,.0f}"
    return f"{x:,.4g} {u}".strip()


def fmt_pair(key, a, b):
    """Format two values of the same input with enough precision that they read differently (e.g. 19.90% vs 20.0%)."""
    close = b and abs(a - b) / abs(b) < 0.01
    for d in ((2, 3) if close else (1, 2, 3)):
        fa, fb = fmt_value(key, a, d), fmt_value(key, b, d)
        if fa != fb:
            return fa, fb
    return fa, fb
