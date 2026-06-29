"""
Network construction and demand aggregation.

This is where RISK POOLING enters the model. A store's daily demand has some
standard deviation sigma. When an RDC sits above several stores, the RDC's job is
to buffer the *combined* demand of those stores. If the stores' demands are
independent, the standard deviation of the sum grows like sqrt(sum of variances),
NOT the sum of standard deviations -- so the pooled buffer needed upstream is
proportionally smaller. That sqrt-of-summed-variances is the mathematical engine
behind "hold it upstream and pool the variability."
"""
from __future__ import annotations

import math

import networkx as nx

from . import config as C


def build_network() -> nx.DiGraph:
    """Directed tree, edges point parent -> child (flow of goods downstream)."""
    G = nx.DiGraph()
    for node, attrs in C.NETWORK.items():
        G.add_node(node, **attrs)
    for node, attrs in C.NETWORK.items():
        if attrs["parent"] is not None:
            G.add_edge(attrs["parent"], node)
    return G


def children(G, node):
    return list(G.successors(node))


def is_leaf(G, node):
    return G.out_degree(node) == 0


def descendant_leaves(G, node):
    """All stores fed (directly or indirectly) by this node."""
    if is_leaf(G, node):
        return [node]
    leaves = []
    for c in G.successors(node):
        leaves.extend(descendant_leaves(G, c))
    return leaves


def aggregate_demand(G) -> dict:
    """
    Compute mean and std of demand each node must buffer.
      - leaf (store): its own demand
      - internal node: pooled demand of all stores beneath it
        mean = sum of means ; std = sqrt(sum of variances)   [independence]
    Returns: dict[node] -> (mean, std)
    """
    agg = {}
    for node in G.nodes:
        leaves = descendant_leaves(G, node)
        mean = sum(C.NETWORK[l]["demand_mean"] for l in leaves)
        var = sum(C.NETWORK[l]["demand_std"] ** 2 for l in leaves)
        agg[node] = (mean, math.sqrt(var))
    return agg
