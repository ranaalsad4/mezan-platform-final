import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
out = sys.argv[1]
fig, ax = plt.subplots(figsize=(12, 6.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 6.6); ax.axis("off")
C = dict(inp=("#FFF2CC", "#B7950B"), step=("#E2F0D9", "#1F4E46"), human=("#FCE4D6", "#C55A11"), out=("#DDEBF7", "#1F3A5F"))
def box(x, y, w, h, t, k, fs=9, bold=False):
    f, e = C[k]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=f, ec=e, lw=1.4))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, weight="bold" if bold else "normal", color="#1F2D2A", wrap=True)
    return (x, y, w, h)
def arrow(a, b, side=("r", "l"), rad=0.0):
    def pt(bx, s):
        x, y, w, h = bx
        return {"r": (x + w, y + h / 2), "l": (x, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}[s]
    ax.add_patch(FancyArrowPatch(pt(a, side[0]), pt(b, side[1]), arrowstyle="-|>", mutation_scale=12, lw=1.3, color="#333",
                                 connectionstyle=f"arc3,rad={rad}"))
ax.text(0.1, 6.35, "Data inputs (pilot: monthly CSV / Excel exports — no system integration needed)", fontsize=10, weight="bold", color="#7A5C00")
ins = ["Utility bills\nelectricity · gas", "Fuel cards & logs\ndiesel", "Production &\nprocurement records", "Project offers\ncapex · savings", "Assumption register\nprices · factors · sources"]
ib = [box(0.1 + i * 2.38, 5.2, 2.18, 0.95, t, "inp") for i, t in enumerate(ins)]
q = box(0.1, 3.25, 2.5, 1.25, "1 · Data-quality checks\nunits · gaps · duplicates\noutliers · estimates with\n95% intervals", "step", 8)
h = box(3.0, 3.25, 2.2, 1.25, "Human review\napprove · reject\noverride · logged\nin the lineage", "human", 8, True)
e = box(5.6, 3.25, 2.5, 1.25, "2 · Emissions accounting\nScope 1, 2, selected Scope 3\n(GHG Protocol)", "step", 8.5)
f = box(8.5, 3.25, 3.4, 1.25, "3 · Financial analysis\nNPV · IRR · payback · abatement cost\nshared ledger (no double counting)", "step", 8)
u = box(8.5, 1.1, 3.4, 1.25, "4 · Uncertainty\nMonte Carlo, 20,000 scenarios\nvalidated on 200,000", "step", 8.5)
o = box(5.6, 1.1, 2.5, 1.25, "5 · Portfolio optimisation\ninteger program + chance\nconstraints (carbon, budget)", "step", 8.5)
v = box(3.0, 1.1, 2.2, 1.25, "6 · Value of information\n& sensitivity", "step", 8.5)
d = box(0.1, 1.1, 2.5, 1.25, "Dashboard & reports\nStreamlit · Excel · Word\naudit trail", "out", 8.5, True)
for b_ in ib[:3]:
    arrow(b_, q, ("b", "t"))
for b_ in ib[3:]:
    arrow(b_, f, ("b", "t"))
arrow(q, h); arrow(h, e); arrow(e, f); arrow(f, u, ("b", "t")); arrow(u, o, ("l", "r")); arrow(o, v, ("l", "r")); arrow(v, d, ("l", "r"))
ax.text(6, 0.45, "Python package (carbon_iq), runs on a laptop (Google Colab run still to be confirmed); data stay with the facility. Each box is existing, tested code; "
        "the pilot adds only data templates and a reviewer.", ha="center", fontsize=8.5, color="#555", style="italic")
fig.savefig(out, dpi=200, bbox_inches="tight"); print("ok")
