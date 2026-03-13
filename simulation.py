import simpy.rt
import matplotlib.pyplot as plt
import keyboard
from network_topology import create_topology # add_node, remove_node
from network_draw import draw_network
import config
import threading

state_lock = threading.Lock()

def run_simulation(env):
    env.run()

def main():
    global pos
    env = simpy.rt.RealtimeEnvironment(factor=1000, strict=False)
    G, nodes_dict, pos = create_topology(env, state_lock)

    plt.ion()
    with state_lock:
        draw_network(G, pos)
    plt.show()  # make sure window appears immediately

    # start simulation in background thread
    sim_thread = threading.Thread(target=run_simulation, args=(env,), daemon=True)
    sim_thread.start()

    while env.now < config.SIM_TIME or config.SIM_TIME < 0:
        # Check if figure window was closed
        if not plt.fignum_exists(1):
            break

        with state_lock:
            draw_network(G, pos)

        plt.pause(0.03)

    plt.close('all')

if __name__ == "__main__":
    main()
