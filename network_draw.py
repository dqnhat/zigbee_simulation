import matplotlib.pyplot as plt
import networkx as nx

state_colors = {
    "IDLE": "lightgray",
    "SEND": "orange",
    "RECEIVE": "green",
    "TRANSFER": "yellow",
    "WAIT": "red"
}

def draw_network(G, pos):
    plt.clf()

    node_colors = [
        state_colors.get(node.STATE, "gray")
        for node in G.nodes
    ]

    # draw nodes and edges
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=2000,
        node_color=node_colors
    )

    labels = {node: node.STATE for node in G.nodes}

    # shift labels slightly downward
    pos_labels = {node: (x, y-0.08) for node, (x, y) in pos.items()}

    nx.draw_networkx_labels(
        G,
        pos_labels,
        labels=labels,
        font_size=9,
        font_color="blue"
    )

    # ---- edge tags ----
    # edge_tags = nx.get_edge_attributes(G, "tag")

    # nx.draw_networkx_edge_labels(
    #     G,
    #     pos,
    #     edge_labels=edge_tags,
    #     font_color="red"
    # )

    plt.title("ZigBee Mesh Network")
    plt.draw()