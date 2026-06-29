"""
The two strategies we compare.

BASELINE -- "decouple everywhere" (single-echelon thinking):
    Every stage holds its own safety stock sized to its own lead time, with no
    coordination. Formally this is the feasible point where every service time
    S_j = 0, so each net time tau_j = T_j. It is what you get when each location
    is managed in isolation -- the naive policy MEIO is meant to beat.

OPTIMIZED -- Guaranteed-Service Model (Graves & Willems, 2000):
    Choose the service times across the whole tree to MINIMISE total safety-stock
    holding cost. Because lead times are integers, the optimum occurs at integer
    service times, so a dynamic program over the tree finds the GLOBAL optimum
    exactly -- no heuristic, no local-optimum risk.

    f_node(si) = min cost of the subtree rooted at `node`, given it is promised
                 inbound service time `si`:

        f_node(si) =  min over S in [0, min(max_service, si + T_node)] of
                         h_node * k * sigma_node * sqrt(si + T_node - S)
                       + sum_children f_child(S)

    The root (DC) receives si = 0 from the external supplier; the answer is
    f_DC(0). A second pass replays the arg-mins to recover where stock is placed.
"""
from __future__ import annotations

import math
from functools import lru_cache

from . import config as C
from . import network as net
from . import safety_stock as ss


# ----------------------------------------------------------------------------
# Baseline: "stock at the edge" (all safety stock at the stores)
# ----------------------------------------------------------------------------
def _path_lead_time(G, leaf) -> int:
    """Total lead time from the root down to a store (the full replenishment pipeline)."""
    total, node = 0, leaf
    while node is not None:
        total += C.NETWORK[node]["lead_time"]
        node = C.NETWORK[node]["parent"]
    return total


def decentralized_baseline(G, agg) -> dict:
    """
    The common naive design: keep inventory at the STORES so they are responsive,
    and treat everything upstream as flow-through (no dedicated safety stock).

    Consequence: when a store runs low, its order has to travel all the way back
    to the source, so each store must buffer the ENTIRE end-to-end lead time on
    its OWN demand -- no risk pooling at all. This is a feasible point of the same
    guaranteed-service model (every upstream stage quotes its maximum service
    time, i.e. holds nothing), so comparing the optimizer against it is rigorous,
    not a straw man.
    """
    placement = {}
    total = 0.0
    for node in G.nodes:
        if net.is_leaf(G, node):
            tau = _path_lead_time(G, node)          # full pipeline on own demand
            sigma = agg[node][1]
        else:
            tau = 0.0                                # flow-through, holds nothing
            sigma = agg[node][1]
        sstock = ss.safety_stock(sigma, tau)
        cost = ss.holding_cost(node, sigma, tau)
        placement[node] = dict(service_out=0, tau=tau, safety_stock=sstock, cost=cost)
        total += cost
    return dict(strategy="decentralized_baseline", placement=placement, total_cost=total)


# ----------------------------------------------------------------------------
# Optimized: Graves-Willems guaranteed-service DP (exact)
# ----------------------------------------------------------------------------
def gsm_optimize(G, agg) -> dict:
    root = [n for n in G.nodes if C.NETWORK[n]["parent"] is None][0]

    @lru_cache(maxsize=None)
    def f(node, si):
        T = C.NETWORK[node]["lead_time"]
        sigma = agg[node][1]
        max_s = min(C.NETWORK[node]["max_service_time"], si + T)
        kids = net.children(G, node)

        best_cost, best_s = math.inf, 0
        for s_out in range(0, max_s + 1):
            tau = si + T - s_out
            here = ss.holding_cost(node, sigma, tau)
            child_cost = sum(f(c, s_out) for c in kids)
            total = here + child_cost
            if total < best_cost:
                best_cost, best_s = total, s_out
        return best_cost  # we recover best_s in the replay pass below

    def best_service(node, si):
        T = C.NETWORK[node]["lead_time"]
        sigma = agg[node][1]
        max_s = min(C.NETWORK[node]["max_service_time"], si + T)
        kids = net.children(G, node)
        best_cost, best_s = math.inf, 0
        for s_out in range(0, max_s + 1):
            tau = si + T - s_out
            total = ss.holding_cost(node, sigma, tau) + sum(f(c, s_out) for c in kids)
            if total < best_cost:
                best_cost, best_s = total, s_out
        return best_s

    total = f(root, 0)

    # Replay arg-mins from the root down to recover per-node placement.
    placement = {}
    def replay(node, si):
        s_out = best_service(node, si)
        T = C.NETWORK[node]["lead_time"]
        sigma = agg[node][1]
        tau = si + T - s_out
        placement[node] = dict(
            service_in=si, service_out=s_out, tau=tau,
            safety_stock=ss.safety_stock(sigma, tau),
            cost=ss.holding_cost(node, sigma, tau),
        )
        for c in net.children(G, node):
            replay(c, s_out)
    replay(root, 0)

    return dict(strategy="gsm_optimized", placement=placement, total_cost=total)
