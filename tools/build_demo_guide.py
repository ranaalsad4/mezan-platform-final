"""Mezan_Phase_B_Demo_Guide.pdf - short visual demo instructions and backup sequence (HTML rendered to PDF with Chromium).
    python tools/build_demo_guide.py [out.pdf]
Reads docs/phase_b/demo_script.json and docs/phase_b/screenshots/*.png (run tools/phase_b_content.py and the capture script first).
"""
import base64
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
S = json.load(open(HERE / "docs" / "phase_b" / "demo_script.json", encoding="utf-8"))
R = json.load(open(HERE / "outputs" / "results.json"))
SHOTS = HERE / "docs" / "phase_b" / "screenshots"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "outputs" / "phase_b" / "Mezan_Phase_B_Demo_Guide.pdf"
e = html.escape


def img(i):
    b = base64.b64encode((SHOTS / f"demo_step{i}.png").read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b}">'


css = """
@page { size: A4 landscape; margin: 12mm 14mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; color: #1F2D2A; font-size: 11pt; margin: 0; }
h1 { color: #1F4E46; font-size: 24pt; margin: 0 0 4px; } h2 { color: #1F4E46; font-size: 15pt; margin: 0 0 6px; }
.sub { color: #555; font-size: 10pt; margin-bottom: 10px; }
.page { page-break-after: always; } .page:last-child { page-break-after: auto; }
.grid { display: grid; grid-template-columns: 68% 32%; gap: 14px; align-items: start; }
img { width: 100%; border: 1px solid #C9D1DB; border-radius: 4px; max-height: 168mm; object-fit: contain; object-position: top; }
.say { background: #F3F5F8; border-left: 4px solid #1F4E46; padding: 8px 10px; margin: 6px 0; font-size: 11.5pt; }
.point { color: #1F4E46; font-weight: 600; margin-top: 8px; } .time { color: #B03A2E; font-weight: 700; }
.warn { background: #FFF4D6; border-left: 4px solid #C9A227; padding: 6px 10px; font-size: 10pt; margin-top: 10px; }
table { border-collapse: collapse; width: 100%; font-size: 10pt; } td, th { border: 1px solid #C9D1DB; padding: 4px 6px; vertical-align: top; }
th { background: #1F4E46; color: white; text-align: left; } code { font-family: Consolas, monospace; font-size: 9.5pt; }
ol li, ul li { margin-bottom: 4px; }
"""
D4 = next(d for d in R["decision_scenarios"] if d["id"] == "D4")
PV = next(x for x in R["pv_capex_scenarios"] if x["id"] == "P1")
TS = json.load(open(HERE / "outputs" / "test_summary.json"))
pv_txt = (f"At SAR {PV['pv_capex_kw']:,.0f}/kWp no portfolio meets both 90% requirements within SAR 5M (needs SAR {PV['joint_min_budget'] / 1e6:.2f} M)"
          if PV["joint"] == "none feasible" else f"At SAR {PV['pv_capex_kw']:,.0f}/kWp the primary rule chooses {PV['joint']}")
pages = [f"""<div class="page"><h1>Mezan — live demo guide</h1>
<div class="sub">Phase B1 · 2–3 minutes · synthetic Saudi metal-fabrication plant · model v{R['meta']['model_version']}, {R['meta']['scenarios']:,} scenarios,
seed {R['meta']['seed']} · <b>modelled results, not verified savings</b></div>
<div class="grid"><div><h2>Run order</h2><table><tr><th>Time</th><th>Step</th><th>Click</th></tr>
{''.join(f"<tr><td class='time'>{e(s['time'])}</td><td>{e(s['step'])}</td><td>{e(s['screen'])}</td></tr>" for s in S['steps'])}</table>
<div class="warn">Message to land: Mezan recommends <b>{e(D4['portfolio'])}</b> and shows how sure we can be — and which data are worth
collecting first. Everything is modelled on a hypothetical plant; the next step is a pilot with real records.</div></div>
<div><h2>Pre-flight (15 minutes before)</h2><ol>{''.join(f'<li>{e(x)}</li>' for x in S['preflight'])}</ol>
<h2>If something fails</h2><ul>{''.join(f'<li>{e(x)}</li>' for x in S['backup'])}</ul></div></div></div>"""]
for i, s in enumerate(S["steps"], start=1):
    pages.append(f"""<div class="page"><h2><span class="time">{e(s['time'])}</span> &nbsp; {e(s['step'])}</h2>
<div class="grid"><div>{img(i)}</div><div><div><b>Click:</b> {e(s['screen'])} (tab “▶ Guided demo”)</div>
<div class="say">“{e(s['say'])}”</div><div class="point">{e(s['point'])}</div>
<div class="warn">Backup: if the app is down, show this page.</div></div></div></div>""")
pages.append(f"""<div class="page"><h2>Google Colab (rehearse once before the event — not yet confirmed on real Colab, issue A1-01)</h2>
<ol>{''.join(f'<li><code>{e(x)}</code></li>' if not x.startswith(('Upload', 'Not yet')) else f'<li>{e(x)}</li>' for x in S['colab'])}</ol>
<h2>Likely questions</h2><table><tr><th>Question</th><th>Answer (from the validated outputs)</th></tr>
<tr><td>Is this a real factory?</td><td>No. A hypothetical plant with synthetic records; Saudi grid factor, tariff and gas price from official or credible sources; costs other than solar are assumptions.</td></tr>
<tr><td>Is it AI?</td><td>No trained machine-learning model: statistical estimation, integer optimisation, Monte Carlo and decision analysis.</td></tr>
<tr><td>What if solar costs more?</td><td>{e(pv_txt)}; get a supplier quotation (Sensitivity sheet of the scorecard).</td></tr>
<tr><td>How do you know the maths is right?</td><td>{TS['passed']} of {TS['total']} automated tests pass, fault injection, and an independent recalculation of every method (Phase A6) — on the synthetic case.</td></tr>
<tr><td>What would a pilot need?</td><td>24 months of utility, fuel, production and procurement records, project quotations and a named reviewer; about 16 weeks (B2).</td></tr>
</table></div>""")
doc = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(pages)}</body></html>"
OUT.parent.mkdir(parents=True, exist_ok=True)
tmp = OUT.with_suffix(".html")
tmp.write_text(doc, encoding="utf-8")
from playwright.sync_api import sync_playwright  # noqa: E402
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(tmp.as_uri())
    pg.pdf(path=str(OUT), format="A4", landscape=True, print_background=True, prefer_css_page_size=True)
    b.close()
tmp.unlink()
print("saved", OUT)
