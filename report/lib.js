// Shared docx helpers for the Mezan complete report.
const fs = require("fs");
const path = require("path");
const D = require("docx");
const { Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType, WidthType, ShadingType, BorderStyle,
  HeadingLevel, ExternalHyperlink, ImageRun } = D;

const NAVY = "1F3A5F", GREY = "4A5A70", STRIPE = "F3F5F8", LINE = "C9D1DB", LINK = "1F5FA8", CALLOUT = "FFF4D6";
const FONT = "Calibri", SZ = 20;
const W = 11906 - 2 * 1000;

function sub(t, base) {
  // _{x} subscript, ^{x} superscript
  return t.split(/(_\{[^}]*\}|\^\{[^}]*\})/).filter(Boolean).map(x =>
    x.startsWith("_{") ? new TextRun({ text: x.slice(2, -1), subScript: true, ...base }) :
    x.startsWith("^{") ? new TextRun({ text: x.slice(2, -1), superScript: true, ...base }) : new TextRun({ text: x, ...base }));
}
function runs(text, base = {}) {
  const b = { font: FONT, size: SZ, ...base };
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)\s]+\))/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(...sub(text.slice(last, m.index), b));
    const t = m[0];
    if (t.startsWith("**")) out.push(...sub(t.slice(2, -2), { ...b, bold: true }));
    else if (t.startsWith("[")) {
      let [, label, url] = t.match(/\[([^\]]+)\]\(([^)\s]+)\)/);
      label = label.replace(/\*/g, "");
      out.push(new ExternalHyperlink({ link: url, children: [new TextRun({ text: label, ...b, color: LINK, underline: {} })] }));
    } else out.push(...sub(t.slice(1, -1), { ...b, italics: true }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(...sub(text.slice(last), b));
  return out;
}
const P = (t, o = {}) => new Paragraph({ spacing: { after: 90, line: 264 }, alignment: o.align, keepNext: o.keepNext, ...o.p, children: runs(t, o.r || {}) });
const H1 = (t, pb = false) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: pb, spacing: { before: pb ? 0 : 260, after: 100 }, keepNext: true,
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 2 } },
  children: [new TextRun({ text: t, bold: true, font: FONT, size: 28, color: NAVY })] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 170, after: 70 }, keepNext: true,
  children: [new TextRun({ text: t, bold: true, font: FONT, size: 23, color: NAVY })] });
const B = t => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 50, line: 256 }, children: runs(t) });
const N = t => new Paragraph({ numbering: { reference: "num", level: 0 }, spacing: { after: 50, line: 256 }, children: runs(t) });
const EQ = t => new Paragraph({ spacing: { before: 40, after: 70 }, indent: { left: 360 }, keepNext: true,
  shading: { fill: STRIPE, type: ShadingType.CLEAR, color: "auto" }, children: sub(t, { font: "Cambria", size: 21, italics: true }) });
const Cap = t => new Paragraph({ spacing: { before: 40, after: 150 }, children: [new TextRun({ text: t, italics: true, font: FONT, size: 17, color: GREY })] });
const TT = t => new Paragraph({ spacing: { before: 120, after: 60 }, keepNext: true, children: [new TextRun({ text: t, bold: true, font: FONT, size: 19, color: NAVY })] });

function callout(text, fill = CALLOUT, bar = "C9A227") {
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [W],
    rows: [new TableRow({ children: [new TableCell({ width: { size: W, type: WidthType.DXA },
      shading: { fill, type: ShadingType.CLEAR, color: "auto" },
      borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
        left: { style: BorderStyle.SINGLE, size: 24, color: bar } },
      margins: { top: 100, bottom: 100, left: 160, right: 160 },
      children: (Array.isArray(text) ? text : [text]).map(t => new Paragraph({ spacing: { after: 40 }, children: runs(t, { size: 19 }) })) })] })] });
}

function table(headers, rows, widths, opt = {}) {
  const sz = opt.size || 17;
  const bd = { style: BorderStyle.SINGLE, size: 4, color: LINE };
  const borders = { top: bd, bottom: bd, left: bd, right: bd };
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (txt, w, i, hdr, bold, fill) => new TableCell({ width: { size: w, type: WidthType.DXA }, borders,
    shading: hdr ? { fill: NAVY, type: ShadingType.CLEAR, color: "auto" } : fill ? { fill, type: ShadingType.CLEAR, color: "auto" }
      : (i % 2 ? { fill: STRIPE, type: ShadingType.CLEAR, color: "auto" } : undefined),
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    children: [new Paragraph({ alignment: (!hdr && opt.center && opt.center.includes(widths.indexOf(w))) ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: runs(String(txt), { size: sz, bold: hdr || bold || undefined, color: hdr ? "FFFFFF" : undefined }) })] });
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, j) => cell(h, widths[j], 0, true)) }),
      ...rows.map((r, i) => new TableRow({ cantSplit: true, children: r.map((c, j) =>
        cell(c, widths[j], i + 1, false, opt.boldFirst && j === 0, opt.highlight && opt.highlight(i, j) ? "E2F0D9" : undefined)) }))] });
}

function fig(dir, file, caption, widthPx = 620) {
  const buf = fs.readFileSync(path.join(dir, file));
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 0 }, keepNext: true,
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: widthPx, height: Math.round(widthPx * h / w) },
      altText: { title: caption, description: caption, name: file } })] }), Cap(caption)];
}

module.exports = { D, NAVY, GREY, STRIPE, FONT, SZ, W, runs, P, H1, H2, B, N, EQ, Cap, TT, callout, table, fig };
