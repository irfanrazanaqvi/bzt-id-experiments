"""Shared figure style: serif (matches Figs 1-2), colour-blind-safe palette, 300 dpi, sized for a 6.5 in text width."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
C = dict(blue="#0072B2", verm="#D55E00", green="#009E73", purple="#CC79A7", orange="#E69F00", sky="#56B4E9", grey="#7f7f7f", lgrey="#bdbdbd", ink="#111111")
def setup():
    plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 9, "axes.titlesize": 9.5,
        "axes.labelsize": 9, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": 0.6,
        "axes.axisbelow": True, "figure.dpi": 100, "savefig.dpi": 300, "savefig.facecolor": "white", "figure.facecolor": "white",
        "lines.linewidth": 1.6, "lines.markersize": 5, "legend.frameon": False})
def panel(ax, text): ax.set_title(text, loc="left", fontweight="bold", fontsize=9.5)
