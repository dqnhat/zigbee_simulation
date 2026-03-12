import simpy
import random
import networkx as nx

# -----------------------------
# Channel (shared medium)
# -----------------------------

class Channel:
    def __init__(self, env, lock):
        self.env = env
        self.lock = lock
        self.busy = False
        self.resource = simpy.Resource(env, capacity=1)

    def transmit(self, duration):
        with self.resource.request() as req:
            yield req
            with self.lock:
                self.busy = True
            yield self.env.timeout(duration)
            with self.lock:
                self.busy = False
