// Mezan v2 learning guide (Word) from docs/v2/learning.json (written by tools/build_v2_docs.py).
// Usage: node report/v2/learning_guide.js <project dir> <out.docx>
const fs = require("fs");
const path = require("path");
const L = require(path.resolve(__dirname, "../lib.js"));
const { D, P, H1, H2, B, N, Cap, callout, table, fig } = L;
const [, , ROOT, OUT] = process.argv;
const J = JSON.parse(fs.readFileSync(path.join(ROOT, "docs/v2/learning.json"), "utf8"));
const ref = k => { const [t, u] = J.refs[k]; return u ? `${t} [${u}](${u})` : t; };
const k = [];
k.push(new D.Paragraph({ spacing: { after: 80 }, children: [new D.TextRun({ text: "Mezan | ميزان v2 — Learning guide", bold: true, font: L.FONT, size: 40, color: "0E2A25" })] }));
k.push(P("Every method in the platform: what it is, where it came from, why Mezan needs it, how it works, a small example, the "
  + "exact Python function that implements it, and a 20-30-second explanation for judges. Generated from carbon_iq/learning.py, the "
  + "same content as the app's Learning Center. 30 October 2026.", { r: { color: L.GREY } }));
k.push(callout(["**Labels used throughout.** Synthetic = made-up test data for a hypothetical Riyadh plant. Reported = Ma'aden's published "
  + "2025 figures for Ma'aden Rolling Company (MRC), Sustainability Data Book 2025, PDF page 5. Benchmark = external published source. "
  + "Hypothetical = a Mezan assumption, never a company value.",
  "**Methods, not machine learning.** Mezan uses accounting, statistics, simulation and optimisation; it contains no trained "
  + "machine-learning model. It is a research prototype, not production software or investment advice."]));
k.push(H1("Method status (judged from the code)"));
k.push(table(["#", "Method", "Status", "What exactly"], J.methods.map((m, i) => [String(i + 1), m.title, m.status, m.status_note]),
  [500, 2600, 1500, 5306], { size: 15 }));
k.push(H1("How the methods connect"));
if (fs.existsSync(path.join(ROOT, "docs/v2/methods_flow.png"))) k.push(...fig(path.join(ROOT, "docs/v2"), "methods_flow.png", "How Mezan's methods connect (teaching order)", 470));
k.push(P("Data are checked and completed, converted to emissions, valued as projects, combined into the best portfolio, then tested in "
  + "simulated futures against the target and the budget. Value of information can send you back to collect better data; sensitivity, "
  + "stability and timing check how robust and how urgent the recommendation is. In the code, optimisation, simulation and the "
  + "confidence rules run together on the same scenarios."));
J.methods.forEach((m, i) => {
  k.push(H1(`${i + 1}. ${m.title}`, true));
  k.push(P(`**Status: ${m.status}.** ${m.status_note}`));
  k.push(H2("1 · What is it?")); k.push(P(m.what));
  k.push(H2("2 · Where did it come from?")); k.push(P(m.origin)); m.refs.forEach(r => k.push(B(ref(r))));
  k.push(H2("3 · Why does Mezan need it?")); k.push(P(m.why));
  k.push(H2("4 · How does it work?")); m.how.forEach(s => k.push(new D.Paragraph({ numbering: { reference: "num", level: 0, instance: i + 1 }, spacing: { after: 50, line: 256 }, children: L.runs(s) })));
  k.push(H2("5 · Simple example")); k.push(P(m.example));
  k.push(H2("6 · How did we implement it?"));
  k.push(table(["File", "Function", "What goes in", "What comes out"], m.code.map(([f, fn, a, b]) => [f, fn + "()", a, b]), [2700, 2000, 2600, 2606], { size: 15 }));
  k.push(P("**The actual Python code** (main function, read from the source when this guide was built):"));
  m.code_src.split("\n").forEach(line => k.push(new D.Paragraph({ spacing: { after: 0, line: 220 }, shading: { type: D.ShadingType.CLEAR, fill: "F4F6F5", color: "auto" },
    children: [new D.TextRun({ text: line.length ? line : " ", font: "Consolas", size: 14 })] })));
  k.push(H2("7 · How should I explain it to judges?")); k.push(callout([`“${m.judges}”`], "EEF4F1", "1F6B5C"));
  if (m.advanced) k.push(P(`*Advanced:* ${m.advanced}`, { r: { color: L.GREY } }));
});
k.push(H1("Examples: synthetic plant and MRC", true));
k.push(table(J.example_cols, J.examples.map(r => r.map(String)), [2600, 3500, 3806], { size: 15 }));
k.push(Cap("Synthetic numbers from the saved model run (outputs/results.json). MRC energy and emissions are reported values; MRC investment results are a hypothetical scenario."));
k.push(H1("Glossary"));
k.push(table(["Term", "Meaning"], J.glossary, [2400, 7506], { size: 15 }));
k.push(H1("What the prototype proves — and what still needs real-world validation"));
k.push(H2("Proves")); J.proves.forEach(x => k.push(B(x)));
k.push(H2("Still needs real-world validation")); J.needs.forEach(x => k.push(B(x)));
k.push(H1("References"));
Object.keys(J.refs).forEach(r => k.push(B(ref(r))));
k.push(Cap("References were checked by web search (28-30 Oct 2026). Open each link before quoting it."));
const doc = new D.Document({
  styles: { default: { document: { run: { font: L.FONT, size: L.SZ } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: D.LevelFormat.BULLET, text: "•", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] },
    { reference: "num", levels: [{ level: 0, format: D.LevelFormat.DECIMAL, text: "%1.", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 } } },
    footers: { default: new D.Footer({ children: [new D.Paragraph({ alignment: D.AlignmentType.RIGHT, children: [new D.TextRun({ text: "Mezan v2 · learning guide · page ", size: 16, color: L.GREY }), new D.TextRun({ children: [D.PageNumber.CURRENT], size: 16, color: L.GREY })] })] }) },
    children: k }] });
D.Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("saved", OUT); });
