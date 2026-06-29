"""
Figures: (1) the network with safety stock placed on it, baseline vs optimized,
and (2) a cost-comparison bar chart by echelon.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import config as C
from . import network as net


# Fixed layout positions for the 3-echelon tree (x, y).
def _layout():
    pos = {"DC": (3.0, 3.0)}
    rdcs = ["RDC_A", "RDC_B", "RDC_C"]
    for i, r in enumerate(rdcs):
        pos[r] = (1.0 + 2.0 * i, 2.0)
    stores = [n for n in C.NETWORK if n.startswith("S_")]
    for j, s in enumerate(stores):
        pos[s] = (0.2 + 0.62 * j, 1.0)
    return pos


def plot_network(G, result, path, title):
    pos = _layout()
    placement = result["placement"]
    max_ss = max(p["safety_stock"] for p in placement.values()) or 1.0

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    # edges
    for u, v in G.edges:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color="#bbbbbb", lw=1.2, zorder=1)
    # nodes: size ~ safety stock held there
    for node, (x, y) in pos.items():
        ssv = placement[node]["safety_stock"]
        size = 250 + 2600 * (ssv / max_ss)
        color = "#2b6cb0" if node == "DC" else ("#3182ce" if node.startswith("RDC") else "#63b3ed")
        ax.scatter([x], [y], s=size, color=color, edgecolor="white", lw=1.5, zorder=2)
        ax.text(x, y - 0.30, node, ha="center", va="top", fontsize=8)
        ax.text(x, y, f"{ssv:.0f}", ha="center", va="center", fontsize=8,
                color="white", fontweight="bold", zorder=3)

    ax.set_title(f"{title}\n(bubble size & number = safety stock units held)",
                 fontsize=11)
    ax.set_xlim(-0.4, 5.6); ax.set_ylim(0.4, 3.6)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=130)
    plt.close()


def plot_cost_comparison(baseline, optimized, path):
    echelons = {"DC": "Central DC", "RDC": "Regional DCs", "S_": "Stores"}

    def by_echelon(result):
        agg = {"DC": 0.0, "RDC": 0.0, "S_": 0.0}
        for node, p in result["placement"].items():
            key = "DC" if node == "DC" else ("RDC" if node.startswith("RDC") else "S_")
            agg[key] += p["cost"]
        return agg

    b, o = by_echelon(baseline), by_echelon(optimized)
    labels = list(echelons.values())
    keys = list(echelons.keys())
    import numpy as np
    x = np.arange(len(labels))
    w = 0.38

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.bar(x - w / 2, [b[k] for k in keys], w, label="Decentralized baseline", color="#cbd5e0")
    ax.bar(x + w / 2, [o[k] for k in keys], w, label="MEIO optimized", color="#2b6cb0")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("Safety-stock holding cost / day")
    ax.set_title("Where the cost sits: baseline vs MEIO")
    ax.legend()
    for i, k in enumerate(keys):
        ax.text(i - w / 2, b[k], f"{b[k]:.0f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + w / 2, o[k], f"{o[k]:.0f}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=130)
    plt.close()
