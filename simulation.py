import simpy.rt
import matplotlib.pyplot as plt
import keyboard
from zigbee_classes import ZigbeeNode, Channel
from network_topology import create_topology # add_node, remove_node
from network_draw import draw_network
import config
import threading

state_lock = threading.Lock()

def run_simulation(env):
    env.run()

def main():
    env = simpy.rt.RealtimeEnvironment(factor=1.0, strict=False)
    channel = Channel(env, state_lock)
    G, nodes_dict = create_topology(env, channel, state_lock)
    nodes = list(nodes_dict.values())

    plt.ion()
    with state_lock:
        draw_network(G, True)
    plt.show()  # make sure window appears immediately

    # start simulation in background thread
    sim_thread = threading.Thread(target=run_simulation, args=(env,), daemon=True)
    sim_thread.start()

    # keyboard.add_hotkey('a', lambda: add_node(env, G, node_types, nodes, channel))
    # keyboard.add_hotkey('r', lambda: remove_node(G, node_types, nodes))

    # print("Starting ZigBee Simulation")
    # print("Press 'a' to add a new end node, 'r' to remove a random end node")

    # step through the simulation manually to slow it down to near real time
    # advance one simulation unit at a time, pausing to keep GUI responsive
    while env.now < config.SIM_TIME or config.SIM_TIME < 0:
        if not plt.fignum_exists(1):
            exit()

        with state_lock:
            draw_network(G)

        plt.pause(0.03)

    for n in nodes:
        print(n.name, n.energy)

    # keep the script alive so the figure stays open until user closes it
    input("Simulation finished, press Enter to exit.")

if __name__ == "__main__":
    main()
