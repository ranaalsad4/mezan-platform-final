"""Build the labelled training corpus for the record-classification model (mezan_ai/data/record_descriptions.csv).

The corpus is CURATED and SYNTHETIC: description templates written for typical Saudi industrial records (utility bills,
fuel cards, ERP purchase lines, logistics statements; English and Arabic), expanded with random account numbers,
line names, vendors and months. Each template has an id so the model can be evaluated on templates it never saw
(grouped cross-validation in tools/evaluate_ai.py). It is not company data.

    python tools/build_classifier_corpus.py
"""
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "mezan_ai" / "data" / "record_descriptions.csv"

TEMPLATES = {
    "electricity": [
        "SEC electricity bill account {acct}", "Saudi Electricity Company invoice {mon}", "Grid power import main meter {m}",
        "Electric energy consumption MDB-{n}", "Utility electricity kWh reading {mon}", "Power purchase - national grid",
        "Main incomer energy meter {m}", "Electricity charges {site} plant", "كهرباء فاتورة الشركة السعودية للكهرباء {mon}",
        "استهلاك الطاقة الكهربائية {site}", "Grid electricity substation {n} reading", "Monthly power bill SEC {acct}",
    ],
    "natural_gas": [
        "Natural gas supply Aramco {mon}", "Fuel gas to furnace line {n}", "Methane delivery meter {m}", "NG consumption burner {n}",
        "Gas invoice - process heating {site}", "Pipeline gas offtake {mon}", "Reheat furnace gas meter {m}",
        "غاز طبيعي توريد أرامكو {mon}", "استهلاك الغاز للأفران {site}", "Natural gas sales gas statement {acct}",
        "Burner fuel gas GJ {mon}", "Process heat gas supply contract {acct}",
    ],
    "diesel_forklift": [
        "Forklift fleet fuel card {acct}", "Diesel material handling vehicles {mon}", "Fuel card statement forklifts {site}",
        "Forklift diesel refuelling bay {n}", "MHE diesel issue {mon}", "Yard vehicles diesel fuel card",
        "ديزل الرافعات الشوكية {mon}", "وقود معدات المناولة {site}", "Lift truck diesel dispensing {n}",
        "Forklifts fuel consumption warehouse {n}", "Diesel for loaders and forklifts {mon}", "Fleet fuel - handling equipment",
    ],
    "diesel_genset": [
        "Standby generator diesel {mon}", "Genset fuel top-up DG-{n}", "Emergency generator diesel delivery {site}",
        "Backup power DG set fuel {mon}", "Diesel for generator {n} test run", "DG set fuel tank refill {m}",
        "ديزل المولد الاحتياطي {mon}", "وقود مولدات الطوارئ {site}", "Generator fuel log {n}",
        "Standby power diesel genset {mon}", "Emergency power fuel purchase {acct}", "Diesel generator runtime fuel {m}",
    ],
    "production": [
        "Finished output tonnes {mon}", "Production finished fabricated steel {site}", "Shipped tonnage line {n}",
        "Good output from line {n}", "Monthly production report {mon}", "Fabrication output tonnes {site}",
        "الإنتاج النهائي بالطن {mon}", "كمية الإنتاج {site}", "Finished goods production {mon}",
        "Net production weight line {n}", "Despatched finished products {mon}", "Output tonnage ERP production order {acct}",
    ],
    "operating_hours": [
        "Plant operating hours {mon}", "Run hours line {n}", "Production line running time {site}",
        "Operating time shift log {mon}", "Machine hours main line {n}", "Plant uptime hours {mon}",
        "ساعات التشغيل {mon}", "ساعات تشغيل خط الإنتاج {n}", "Operating hours MES report {acct}",
        "Line run time {mon}", "Shift operating hours {site}", "Total operating hours plant {mon}",
    ],
    "steel_purchased": [
        "Steel coil purchase {vendor}", "Purchased steel plate receipt PO {acct}", "Raw material steel delivery {mon}",
        "Hot rolled coil receipt {vendor}", "Steel sections purchase order {acct}", "Incoming steel tonnage {mon}",
        "مشتريات الحديد {vendor}", "استلام لفائف الصلب {mon}", "Rebar and plate purchases {vendor}",
        "Steel raw material goods receipt {acct}", "Purchased structural steel {mon}", "Steel billet purchase {vendor}",
    ],
    "freight": [
        "Inbound road freight tonne-km {mon}", "Logistics truck haulage {vendor}", "Transport of raw materials {mon}",
        "Trucking inbound tkm statement {acct}", "Road haulage raw steel {vendor}", "Freight carrier inbound shipments {mon}",
        "نقل بري للمواد الخام {mon}", "شحن بالشاحنات {vendor}", "Inbound logistics tonne kilometre {acct}",
        "Haulage services raw material {mon}", "Supplier delivery transport {vendor}", "Road transport statement {mon}",
    ],
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "2025-03", "2026-07", "Q2", "FY25"]
SITES = ["Riyadh", "Jubail", "Dammam", "2nd Industrial City", "Plant 1", "PLANT-01", "Sudair", "Yanbu"]
VENDORS = ["Hadeed", "supplier A", "vendor 1047", "Al-Rajhi Steel", "local mill", "Jubail Steel Co", "carrier 22", "Bahri Logistics"]


def fill(t, rng):
    return t.format(acct=f"{rng.randint(1000, 9999)}-{rng.randint(10, 999)}", mon=rng.choice(MONTHS), m=f"M{rng.randint(1, 40)}",
                    n=rng.randint(1, 12), site=rng.choice(SITES), vendor=rng.choice(VENDORS))


def build(per_template=6, seed=7):
    rng = random.Random(seed)
    rows = []
    for stream, temps in TEMPLATES.items():
        for j, t in enumerate(temps):
            for _ in range(per_template):
                rows.append(dict(description=fill(t, rng), stream=stream, template=f"{stream}#{j}"))
    return rows


if __name__ == "__main__":
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["description", "stream", "template"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} labelled descriptions -> {OUT}")
