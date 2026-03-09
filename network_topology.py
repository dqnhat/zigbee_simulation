import networkx as nx
import random
import config
from zigbee_classes import ZigbeeNode, Channel

# -----------------------------
# Network Topology
# -----------------------------

def create_topology(env, channel, lock):
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
        node = ZigbeeNode(env, name, ntype, G, channel, lock)
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

    return G, nodes

# def add_node(env, G, node_types, nodes, channel):
#     end_count = sum(1 for n in node_types.values() if n == "end")
#     new_name = f"End{end_count + 1}"
#     node_types[new_name] = "end"
#     G.add_node(new_name)
#     G.add_edge("Router1", new_name)  # connect to Router1
#     new_node = ZigbeeNode(env, new_name, "end", G, channel)
#     nodes.append(new_node)
#     print(f"Added new node: {new_name}")
#     config.redraw_flag = True

# def remove_node(G, node_types, nodes):
#     end_nodes = [n for n in node_types if node_types[n] == "end"]
#     if end_nodes:
#         remove_name = random.choice(end_nodes)
#         del node_types[remove_name]
#         G.remove_node(remove_name)
#         nodes[:] = [n for n in nodes if n.name != remove_name]
#         print(f"Removed node: {remove_name}")
#         config.redraw_flag = True