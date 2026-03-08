import simpy
import matplotlib.pyplot as plt
import keyboard
from zigbee_classes import SIM_TIME, packet_count, packet_delivered, total_delay, redraw_flag, ZigbeeNode, Channel
from network_topology import create_topology, add_node, remove_node
from network_draw import draw_network

def print_stats():
    print("\n----- Simulation Stats -----")
    print("Packets generated:", packet_count)
    print("Packets delivered:", packet_delivered)
    if packet_delivered > 0:
        print("Average delay:", total_delay / packet_delivered)

def main():
    global redraw_flag
    env = simpy.Environment()
    G, node_types = create_topology()
    channel = Channel(env)
    nodes = []
    for name, ntype in node_types.items():
        nodes.append(ZigbeeNode(env, name, ntype, G, channel))

    plt.ion()
    draw_network(G)
    plt.show()  # make sure window appears immediately

    keyboard.add_hotkey('a', lambda: add_node(env, G, node_types, nodes, channel))
    keyboard.add_hotkey('r', lambda: remove_node(G, node_types, nodes))

    print("Starting ZigBee Simulation")
    print("Press 'a' to add a new end node, 'r' to remove a random end node")

    # step through the simulation manually to slow it down to near real time
    # advance one simulation unit at a time, pausing to keep GUI responsive
    while env.now < SIM_TIME:
        env.run(until=env.now + 1)
        if redraw_flag:
            draw_network(G)
            redraw_flag = False
        plt.pause(0.01)  # allow GUI events and redraws

    print_stats()
    print("\nEnergy remaining")
    for n in nodes:
        print(n.name, n.energy)

    # keep the script alive so the figure stays open until user closes it
    input("Simulation finished, press Enter to exit.")