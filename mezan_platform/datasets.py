"""Facilities and datasets available in the platform, with their evidentiary status.

Two facilities (unchanged from v2.1):
  SYN  synthetic Saudi metal-fabrication plant - all data are HYPOTHETICAL (made-up test data).
  MRC  Ma'aden Rolling Company - 2025 energy and emissions REPORTED by Ma'aden (external company information). The
       investment scenario is HYPOTHETICAL; it is not a Ma'aden value, plan or endorsement.

Plant-data sources for the synthetic plant (monthly records for the data-quality workflow):
  demo        degraded copy of a known synthetic truth (carbon_iq.dataquality.synth.demo_incomplete)
  severe      six consecutive months of electricity missing (estimation must be refused)
  unlabelled  the same records as 'demo' exported WITHOUT stream labels, as a utility/ERP export would arrive: only a
              free-text description and a unit. Used to demonstrate record classification; the true labels are kept
              separately so the classification accuracy can be shown honestly.
  upload      a user CSV (long format)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from carbon_iq.dataquality import synth as DS

FACILITIES = {
    "SYN": dict(name="Synthetic Saudi metal-fabrication plant", short="Synthetic plant", location="Riyadh region (hypothetical)",
                status="Synthetic (hypothetical)", year=2026,
                evidence="All activity data, prices and project costs are hypothetical or transferred from public sources. "
                         "No value is a measured factory observation."),
    "MRC": dict(name="Ma'aden Rolling Company (MRC)", short="Ma'aden Rolling Co.", location="Ras Al-Khair, Saudi Arabia",
                status="Reported company data + hypothetical scenario", year=2025,
                evidence="2025 energy and Scope 1/2 emissions are Ma'aden's reported figures (Sustainability Data Book 2025, "
                         "PDF page 5). Every investment number is a hypothetical Mezan scenario: not a Ma'aden value, plan or "
                         "endorsement."),
}
SOURCES = {
    "demo": "Monthly records with gaps and errors (synthetic)",
    "unlabelled": "Unlabelled utility/ERP export (synthetic, needs classification)",
    "severe": "Severe gap: 6 months of electricity missing (synthetic)",
    "upload": "Upload a CSV",
}

# Export wording deliberately different from the classifier's training templates (no leakage into the demo check).
_EXPORT_TEXT = {
    "production": ["Finished output - fabrication shop", "Monthly output weighbridge", "Fabricated products output"],
    "operating_hours": ["Plant run time (MES)", "Main line running time", "Operating time - shift log"],
    "electricity": ["SEC account 3004-118 energy charge", "Grid supply - main incomer", "Electricity invoice SEC"],
    "natural_gas": ["Fuel gas to reheat furnace", "Aramco sales gas offtake", "Furnace burner gas meter"],
    "diesel_forklift": ["Fuel card - yard forklifts", "MHE diesel dispensing", "Diesel issued to warehouse trucks"],
    "diesel_genset": ["Standby DG set refuel", "Emergency generator fuel", "Genset test-run diesel"],
    "steel_purchased": ["Hot-rolled coil receipt (Hadeed)", "Steel plate goods receipt", "Purchased steel sections"],
    "freight": ["Inbound haulage statement", "Road transport of raw steel", "Trucking - inbound t-km"],
}
EXPORT_UNITS = {"electricity": "kWh"}           # the ERP exports electricity in kWh (converted exactly by quality.UNITS)


def demo_raw():
    return DS.demo_incomplete()[0]


def severe_raw():
    return DS.demo_severe()


def unlabelled_raw(seed=11):
    """(export without stream labels, true stream per row). Two rows carry an ambiguous description on purpose."""
    raw = demo_raw().copy()
    rng = np.random.default_rng(seed)
    truth = raw["stream"].copy()
    desc = [str(rng.choice(_EXPORT_TEXT[s])) for s in truth]
    amb = raw.index[(truth == "diesel_forklift") & raw.period.isin(["2026-01", "2026-02"])]
    for i in amb:
        desc[raw.index.get_loc(i)] = "Diesel purchase - site"        # cannot be decided from text: reviewer must choose
    out = raw.drop(columns=["stream"]).copy()
    out.insert(3, "description", desc)
    for s, u in EXPORT_UNITS.items():
        m = (truth == s) & (out["unit"] == "MWh")
        out.loc[m, "value"] = out.loc[m, "value"] * 1000
        out.loc[m, "unit"] = u
    out["source"] = "SYNTHETIC unlabelled ERP export"
    return out, truth


def template_csv():
    return ("record_id,site,period,stream,description,value,unit,source,note\n"
            "R00001,PLANT-01,2026-01,electricity,SEC monthly bill,864.0,MWh,utility bill,\n"
            "R00002,PLANT-01,2026-01,,Fuel gas to reheat furnace,3050,GJ,gas meter,\n")
