import matplotlib.pyplot as plt
import networkx as nx

def draw_network(G):
    plt.clf()
    pos = nx.spring_layout(G)
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=2000
    )
    plt.title("ZigBee Mesh Network")
    plt.draw()