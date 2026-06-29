"""
Configuration for the multi-echelon inventory optimization (MEIO) project.

We model a 3-echelon distribution network for a single SKU:

        Central DC          (echelon 3 -- upstream, cheap to hold, pools all demand)
        /    |    \\
     RDC_A  RDC_B  RDC_C    (echelon 2 -- regional, pools its stores' demand)
     /|\\    /|\\    /|\\
   stores stores stores     (echelon 1 -- face customer demand directly)

The whole point of the project is *where to place safety stock* in this network.
Holding cost rises as you move downstream (value is added / product is closer to
the customer), and demand variability POOLS as you move upstream (one DC absorbing
nine stores' noise needs proportionally less buffer than nine separate buffers).
Those two forces are what the optimizer trades off.

Lead times are in DAYS. Demand is in UNITS/DAY.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "outputs" / "figures"
RES_DIR = ROOT / "outputs" / "results"
FIG_DIR.mkdir(parents=True, exist_ok=True)
RES_DIR.mkdir(parents=True, exist_ok=True)

# Target cycle service level -> safety factor k (z-score).
SERVICE_LEVEL = 0.95
SAFETY_FACTOR = 1.645  # z for 95%

# ----------------------------------------------------------------------------
# Network definition
# ----------------------------------------------------------------------------
# Each node: id -> dict(parent, lead_time, holding_cost, max_service_time, demand)
#   lead_time         : replenishment/processing time T_j at this stage (days)
#   holding_cost      : h_j, cost to hold one unit one day at this stage
#   max_service_time  : upper bound on the outbound service time the node may quote
#                       (stores must serve customers immediately -> 0)
#   demand_mean/std   : ONLY for stores (leaf demand). Upstream demand is derived
#                       by aggregation in network.py (this is where pooling enters).
#
# holding_cost increases downstream: DC=1.0, RDC=2.0, Store=4.0
# lead_time:  external->DC = 10, DC->RDC = 5, RDC->Store = 2

NETWORK = {
    "DC": dict(parent=None, lead_time=10, holding_cost=1.0, max_service_time=99),

    "RDC_A": dict(parent="DC", lead_time=5, holding_cost=2.0, max_service_time=99),
    "RDC_B": dict(parent="DC", lead_time=5, holding_cost=2.0, max_service_time=99),
    "RDC_C": dict(parent="DC", lead_time=5, holding_cost=2.0, max_service_time=99),

    # Stores: face customer demand (mean, std units/day), must quote service time 0.
    "S_A1": dict(parent="RDC_A", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=60,  demand_std=20),
    "S_A2": dict(parent="RDC_A", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=80,  demand_std=28),
    "S_A3": dict(parent="RDC_A", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=50,  demand_std=18),

    "S_B1": dict(parent="RDC_B", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=100, demand_std=35),
    "S_B2": dict(parent="RDC_B", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=70,  demand_std=24),
    "S_B3": dict(parent="RDC_B", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=90,  demand_std=30),

    "S_C1": dict(parent="RDC_C", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=40,  demand_std=15),
    "S_C2": dict(parent="RDC_C", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=55,  demand_std=19),
    "S_C3": dict(parent="RDC_C", lead_time=2, holding_cost=4.0, max_service_time=0, demand_mean=65,  demand_std=22),
}
