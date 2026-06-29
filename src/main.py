"""
End-to-end MEIO pipeline.

Run:  python -m src.main   (from project root)

  1. Build the 3-echelon network and aggregate demand (risk pooling).
  2. Compute the decentralized baseline (decouple at every stage).
  3. Solve the Guaranteed-Service Model for the optimal safety-stock placement.
  4. Compare total cost + show WHERE stock moved, and save figures/results.
"""
from __future__ import annotations

import json
import warnings

import pandas as pd

from . import config as C
from . import network as net
from . import optimize, visualize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 120)


def placement_table(result) -> pd.DataFrame:
    rows = []
    for node, p in result["placement"].items():
        rows.append({
            "node": node,
            "tau (net days)": round(p["tau"], 1),
            "safety_stock": round(p["safety_stock"], 1),
            "cost/day": round(p["cost"], 1),
        })
    order = {n: i for i, n in enumerate(C.NETWORK)}
    return pd.DataFrame(rows).sort_values("node", key=lambda s: s.map(order)).reset_index(drop=True)


def main():
    print("=" * 70)
    print("MULTI-ECHELON INVENTORY OPTIMIZATION (MEIO)")
    print("Guaranteed-Service Model  vs  decentralized baseline")
    print("=" * 70)

    G = build = net.build_network()
    agg = net.aggregate_demand(G)

    print("\n[1] Network: 1 Central DC -> 3 Regional DCs -> 9 Stores")
    print(f"    Service level {C.SERVICE_LEVEL:.0%} (k = {C.SAFETY_FACTOR})")
    print("    Demand pooling (mean, std of demand each node buffers):")
    for node in C.NETWORK:
        m, s = agg[node]
        tag = "store" if node.startswith("S_") else ("RDC" if node.startswith("RDC") else "DC ")
        print(f"      {node:6s} [{tag}]  mean={m:6.0f}  std={s:6.1f}")

    # 2 + 3
    print("\n[2] Decentralized baseline (all safety stock held at stores, full pipeline) ...")
    base = optimize.decentralized_baseline(G, agg)
    print("[3] Solving Guaranteed-Service Model (exact tree DP) ...")
    opt = optimize.gsm_optimize(G, agg)

    # 4. Compare
    print("\n[4] Results")
    print("\n  --- Decentralized baseline ---")
    print("  " + placement_table(base).to_string(index=False).replace("\n", "\n  "))
    print("\n  --- MEIO optimized ---")
    print("  " + placement_table(opt).to_string(index=False).replace("\n", "\n  "))

    b, o = base["total_cost"], opt["total_cost"]
    saving = (b - o) / b
    print("\n  " + "-" * 50)
    print(f"  Baseline total safety-stock cost/day : {b:8.1f}")
    print(f"  MEIO total safety-stock cost/day     : {o:8.1f}")
    print(f"  REDUCTION                            : {saving:8.1%}")
    print("  " + "-" * 50)

    # The qualitative story:
    dc_base = base["placement"]["DC"]["safety_stock"]
    dc_opt = opt["placement"]["DC"]["safety_stock"]
    store_base = sum(base["placement"][n]["safety_stock"] for n in C.NETWORK if n.startswith("S_"))
    store_opt = sum(opt["placement"][n]["safety_stock"] for n in C.NETWORK if n.startswith("S_"))
    print(f"\n  Safety stock at Central DC : {dc_base:.0f} -> {dc_opt:.0f} units")
    print(f"  Safety stock across Stores : {store_base:.0f} -> {store_opt:.0f} units")
    print("  (MEIO pushes buffering to where it is cheapest and most pooled.)")

    # Risk pooling: the engine behind the saving.
    import math
    sum_sigma = sum(C.NETWORK[n]["demand_std"] for n in C.NETWORK if n.startswith("S_"))
    pooled_sigma = agg["DC"][1]
    print(f"\n  Risk pooling: 9 stores' combined std = {sum_sigma:.0f} units (held separately),")
    print(f"                but POOLED at the DC it is only {pooled_sigma:.0f} units "
          f"({sum_sigma / pooled_sigma:.1f}x less variability to buffer).")

    # Figures
    visualize.plot_network(G, base, C.FIG_DIR / "network_baseline.png",
                           "Decentralized baseline -- safety stock placement")
    visualize.plot_network(G, opt, C.FIG_DIR / "network_optimized.png",
                           "MEIO optimized -- safety stock placement")
    visualize.plot_cost_comparison(base, opt, C.FIG_DIR / "cost_comparison.png")

    # Save numeric results
    out = {
        "service_level": C.SERVICE_LEVEL,
        "baseline_total_cost": b,
        "meio_total_cost": o,
        "reduction_pct": saving,
        "baseline": base["placement"],
        "optimized": opt["placement"],
    }
    with open(C.RES_DIR / "results.json", "w") as fh:
        json.dump(out, fh, indent=2, default=float)

    print("\n" + "=" * 70)
    print("Done. Figures -> outputs/figures/   Results -> outputs/results/results.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
