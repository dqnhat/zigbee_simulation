import networkx as nx
import numpy as np
import random
import config
from zigbee_node import ZigbeeNode

# -----------------------------
# Network Topology
# -----------------------------

def create_topology(env, lock):
    G = nx.Graph()

    node_types = {
        "Coordinator": "coordinator",
        "Router1": "router",
        "Router2": "router",
        "End1": "end",
        "End2": "end",
        "End3": "end",
        "End4": "end"
    }

    nodes = {}

    # create ZigbeeNode objects
    for name, ntype in node_types.items():
        node = ZigbeeNode(env, name, ntype, G, lock)
        nodes[name] = node
        G.add_node(node)

    edges = [
        ("Coordinator", "Router1"),
        ("Coordinator", "Router2"),
        ("Router1", "End1"),
        ("Router1", "End2"),
        ("Router2", "End3"),
        ("Router2", "End4")
    ]

    for a, b in edges:
        G.add_edge(nodes[a], nodes[b])

    pos = nx.spring_layout(G)

    for u, v, data in G.edges(data=True):
        G[u][v]["distance"] = np.linalg.norm(pos[u] - pos[v])

    return G, nodes, pos