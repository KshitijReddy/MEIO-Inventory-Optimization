"""
Safety-stock mathematics for the Guaranteed-Service Model (GSM).

Key concepts (Graves & Willems, 2000):

  * Every stage j quotes an OUTBOUND service time S_j: the time it promises to
    fulfil an order from its downstream customer.
  * It receives an INBOUND service time SI_j from its supplier = the supplier's
    outbound service time.
  * Its NET REPLENISHMENT TIME is:
        tau_j = SI_j + T_j - S_j
    Read it as: time to get stock in (SI_j), plus time to process (T_j), minus the
    delay it is allowed to pass on to its own customer (S_j). The stage must hold
    safety stock to cover demand variability over exactly this net time.
  * Safety stock at j:
        SS_j = k * sigma_j * sqrt(tau_j)
    and its holding cost is h_j * SS_j.

The decision is the vector of service times. Pushing S_j up at a stage shrinks its
own net time (less stock there) but FORCES its children to quote a larger inbound
time (more stock downstream). The optimizer balances this across the whole tree.
"""
from __future__ import annotations

import math

from . import config as C


def net_replenishment_time(si: float, lead_time: float, s_out: float) -> float:
    """tau = SI + T - S  (must be >= 0 to be feasible)."""
    return si + lead_time - s_out


def safety_stock(sigma: float, tau: float) -> float:
    """SS = k * sigma * sqrt(tau).  tau<0 is infeasible -> inf."""
    if tau < 0:
        return math.inf
    return C.SAFETY_FACTOR * sigma * math.sqrt(tau)


def holding_cost(node: str, sigma: float, tau: float) -> float:
    """Annualised-agnostic holding cost of the safety stock held at this node."""
    h = C.NETWORK[node]["holding_cost"]
    return h * safety_stock(sigma, tau)
