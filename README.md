# Multi-Echelon Inventory Optimization (MEIO)

**Where should safety stock sit in a distribution network — and how much does
getting it right actually save?** This project models a real 3-tier supply chain,
finds the *provably optimal* placement of safety stock across it using the
Guaranteed-Service Model, and benchmarks that optimum against the naive policy most
networks default to.

> **Result:** a **43% reduction** in safety-stock holding cost (5,724 → 3,250 per
> day) versus a decentralized "stock-at-the-edge" baseline, **at the same 95%
> service level** — driven by risk pooling (the 9 stores' combined demand
> variability of **211 units** collapses to **73** when pooled upstream, ~2.9× less
> to buffer).

---

## What problem is this solving?

Every supply chain holds **safety stock** — buffer inventory that absorbs demand
and lead-time variability so customers aren't left waiting. Hold too little and you
stock out; hold too much and you tie up capital. In a *single* location that's a
simple trade-off. In a **network** it gets hard, because the same protection can be
bought *cheaply once* at a pooled upstream location, or *expensively many times
over* at the edge.

This project answers: **across a central DC, regional DCs, and stores, where do you
place the buffers to minimise total holding cost without hurting service?**

The network:

```
            Central DC            (cheap to hold, pools ALL demand)
           /     |      \
        RDC_A   RDC_B   RDC_C     (regional — pools its stores' demand)
        /|\     /|\     /|\
      9 stores total ...          (face customer demand directly, expensive)
```

13 stocking nodes, one SKU, a 95% target service level.

---

## The two forces in tension (the heart of the project)

The entire optimization is a tug-of-war between two opposing forces. Understand
these and you understand everything:

1. **Holding cost rises downstream.** Holding a unit costs 1 at the DC, 2 at a
   regional DC, 4 at a store (the product is more valuable and more handled closer
   to the customer). So all else equal, you'd rather hold stock **upstream**.

2. **Variability pools upstream.** One DC buffering nine stores' *combined* demand
   needs far less safety stock than nine separate buffers — because for independent
   demand, the standard deviation of the sum grows like **√(Σ variances)**, *not*
   the sum of the standard deviations. (In the data: nine stores summing to 211
   units of std pool to just 73 at the DC.)

Both forces push stock upstream — but stores must still serve customers
*immediately*, so they can't hold nothing. The optimizer finds the exact balance.

---

## The core concepts (own these for an interview)

### 1. Safety stock and why it scales with √(lead time)

```
SS = k · σ · √L
```

σ is daily demand std, L is the lead time, and k is a service-level factor
(k = 1.645 for 95%). **Why the square root?** Over L independent days the
*variances* add (variance scales with L), and standard deviation is the square root
of variance — so demand std over L days is σ·√L. This is why doubling lead time
multiplies safety stock by √2, not 2. It's the single most-probed formula here.

### 2. Risk pooling — the engine of the saving

The same √-of-variances math, applied across *locations* instead of *time*. Pooling
nine independent store demands at one node means their ups and downs partly cancel,
so the pooled std (73) is far below the sum of the individual stds (211). Holding
the buffer once, upstream, is therefore much cheaper than holding it nine times at
the edge. **This is *why* MEIO beats the baseline.**

### 3. The Guaranteed-Service Model and "net replenishment time"

This is the one genuinely non-obvious idea — spend the most time here.

Every stage quotes its customer an **outbound service time** `S` ("I'll fulfil your
order within S days") and receives an **inbound service time** `SI` from its
supplier. The stage must hold safety stock to cover its **net replenishment time**:

```
tau = SI + T − S
```

In plain English: *the time to get stock in (SI), plus my own processing time (T),
minus the delay I'm allowed to pass on to my customer (S).* That `tau` is the
effective window the stage must buffer, so its safety stock is `k · σ · √tau`.

The crucial consequence: if a stage promises a **faster** service time (smaller S),
it holds **more** stock itself but lets its customer hold less. Promise a **slower**
service time (larger S) and it holds less but forces the downstream stage to hold
more. **Choosing these service times across the whole network is the optimization.**

### 4. Why the solver is *exact*, not a heuristic

Because the cost objective is **concave** in the service times, its minimum always
occurs at **integer** service times. That means a **dynamic program over the tree**
can find the *provably global optimum* — no heuristic, no risk of a local minimum.
This is your strongest technical claim: "exact, not approximate."

The DP:

```
f_node(si) = min over S in [0, min(max_service, si+T)] of
                h·k·σ·√(si + T − S)  +  Σ_children f_child(S)
```

`f_node(si)` answers "given inbound service time `si`, what's the cheapest way to
run this node and everything beneath it?" The root (DC) gets `si = 0`; the answer is
`f_DC(0)`. A second "replay" pass recovers where stock ends up.

---

## Baseline vs. optimum — and why the comparison is fair

**Baseline — "stock at the edge":** keep all inventory at the stores for
responsiveness, with everything upstream as flow-through (holding nothing). The
consequence: when a store runs low, its order travels all the way back to the
source, so each store must buffer the **entire 17-day pipeline** on its **own,
un-pooled** demand. This is the common real-world default ("push stock to stores so
they're responsive").

Critically, this baseline is **a feasible point of the same model** (it's what you
get when every upstream stage quotes its maximum service time), so the optimizer is
genuinely searching a space that *includes* the baseline and beating it — not
competing against a straw man.

| Strategy | DC | Regional DCs | Stores | **Total cost/day** |
|---|---|---|---|---|
| Decentralized baseline | 0 | 0 | 5,724 | **5,724** |
| **MEIO optimized** | 378 | 909 | 1,963 | **3,250** |

The optimizer moves buffering **off the expensive, un-pooled store edge and onto
the cheap, pooled upstream nodes**: store safety stock falls from **1,431 → 491
units**, a pooled **378-unit** buffer appears at the DC, and total cost drops **43%**
— with **no change in service level**, so it's a pure efficiency gain, not a service
trade-off.

---

## Tech stack

- **Language:** Python
- **Core libraries:** NetworkX (build/traverse the network tree), NumPy, pandas
  (results), Matplotlib (figures)
- **Standard library:** `functools.lru_cache` (memoising the DP), `math`, `json`
- **Methods / concepts:** Operations Research, the **Guaranteed-Service Model**
  (Graves & Willems, 2000) for multi-echelon inventory, **dynamic programming** for
  exact optimization, safety-stock theory, risk pooling
- **Engineering:** modular package (config / network / safety_stock / optimize /
  visualize / main), a single reproducible entry point

When asked "what's the stack," lead with: *"Python with NetworkX, but the substance
is the operations-research method — the Guaranteed-Service Model solved exactly with
dynamic programming."* The hard part was the modeling, not the libraries.

---

## How to run

```bash
pip install -r requirements.txt
python -m src.main          # from the project root
```

Figures land in `outputs/figures/` (network placement for each strategy + cost
comparison); full numeric placement in `outputs/results/results.json`.

---

## Likely interview questions

- **"Why √(lead time) in the safety-stock formula?"** — Variance adds over
  independent periods; std is its square root, so demand std over L days is σ·√L.
- **"Where does the 43% saving come from?"** — Two sources: pooling variability
  upstream (211 → 73) *and* holding it where it's cheaper (DC cost 1 vs store 4).
  The baseline pays both penalties; the optimum avoids both.
- **"Exact or heuristic?"** — Exact and global: the concave objective means the
  optimum is at integer service times, which the tree DP finds exactly.
- **"Isn't the baseline a straw man?"** — No — "all stock at the edge" is a feasible
  configuration of the same model, so the optimizer beats a point it genuinely
  searched.
- **"What's a limitation?"** — Pooling assumes store demands are *independent*; if
  they're positively correlated (e.g., a region-wide promotion), the pooled std is
  larger and the saving shrinks.

---

## Honest limitations & next steps

- **Independence assumption.** The √-of-variances pooling assumes uncorrelated store
  demand. Positive correlation reduces the benefit — a good sensitivity analysis to
  add.
- **Single SKU, deterministic lead times.** Real networks have many SKUs and
  variable lead times (a lead-time-variability term in the formula is the natural
  extension).
- **Constant demand parameters.** Feeding in *forecasted* σ per SKU would connect
  this directly to a demand-forecasting pipeline (predict → optimize).
- **Scale.** The DP is fast on this tree; benchmarking it against a MILP formulation
  on larger networks would round out the OR story.

---

## What this project demonstrates

The ability to take a real operations problem, **formulate it mathematically**
(objective, decision variables, constraints), recognise the structure that makes it
**exactly solvable**, implement a **dynamic-programming optimizer** over a network,
and **quantify the result against a fair baseline** — plus the supply-chain depth to
explain *why* it works (risk pooling, the centralization-vs-responsiveness
trade-off). It reads as a trained industrial engineer, not someone who called a
solver.

*Reference: Graves, S.C. & Willems, S.P. (2000), "Optimizing Strategic Safety Stock
Placement in Supply Chains," Manufacturing & Service Operations Management.*
