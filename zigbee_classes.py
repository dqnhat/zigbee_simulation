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

# -----------------------------
# ZigBee Packet
# -----------------------------

class Packet:
    def __init__(self, src, dst, time):
        self.src = src
        self.dst = dst
        self.start = time

# -----------------------------
# ZigBee Node
# -----------------------------

class ZigbeeNode:

    PACKET_LOSS = 0.05
    CSMA_BACKOFF = (1, 3)
    TX_ENERGY = 0.8
    RX_ENERGY = 0.3
    IDLE_ENERGY = 0.02
    STATE = "IDLE"

    def __init__(self, env, name, ntype, graph, channel, lock):
        self.env = env
        self.name = name
        self.ntype = ntype
        self.graph = graph
        self.channel = channel
        self.lock = lock
        self.energy = 100
        self.queue = simpy.Store(env)
        self.process = env.process(self.run())
        env.process(self.receive())

    def send(self, packet):
        dst_node = next(n for n in self.graph.nodes if n.name == packet.dst)
        path = nx.shortest_path(self.graph, self, dst_node)

        hop = path[1]

        backoff = random.randint(*self.CSMA_BACKOFF)
        yield self.env.process(self.channel.transmit(backoff))
        yield self.env.timeout(backoff)

        if random.random() < self.PACKET_LOSS:
            print(self.env.now, "Packet lost")
            return

        with self.lock:
            self.energy -= self.TX_ENERGY

        # deliver packet to this hop
        yield hop.queue.put(packet)

        with self.lock:
            self.STATE = "IDLE"

        delay = self.env.now - packet.start
        print(self.env.now, "Packet delivered delay", delay)

    def run(self):
        while True:
            yield self.env.timeout(random.randint(4, 8))

            if self.ntype == "end":
                end_nodes = [
                    n for n in self.graph.nodes
                    if n.ntype == "end" and n.name != self.name
                ]

                if end_nodes:
                    dst = random.choice(end_nodes)

                    # wait until channel is free
                    while self.channel.busy:
                        with self.lock:
                            self.STATE = "WAIT"
                        yield self.env.timeout(1)

                    packet = Packet(self.name, dst.name, self.env.now)
                    print()
                    print(self.env.now, self.name, "send packet to", dst.name)
                    with self.lock:
                        self.STATE = "SEND"
                    self.env.process(self.send(packet))
            with self.lock:
                self.energy -= self.IDLE_ENERGY

    def receive(self):
        while True:
            packet = yield self.queue.get()
            with self.lock:
                self.energy -= self.RX_ENERGY
            if packet.dst == self.name:
                with self.lock:
                    self.STATE = "RECEIVE"
            else:
                with self.lock:
                    self.STATE = "TRANSFER"
                self.env.process(self.send(packet))
                print(self.env.now, self.name, "transfer packet to", packet.dst)

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name