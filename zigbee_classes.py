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
    def __init__(self, src, dst, time, ptype="DATA"):
        self.src = src
        self.dst = dst
        self.start = time
        self.ptype = ptype   # "RTS", "CTS", "DATA", "ACK"

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
        self.BackoffExponent = 1
        self.NumberOfBackoff = 4
        self.cts_received = False
        self.ack_received = False

        self.energy = 100
        self.queue = simpy.Store(env)
        self.process = env.process(self.run())
        env.process(self.receive())

    def send(self, packet):
        dst_node = next(n for n in self.graph.nodes if n.name == packet.dst)
        path = nx.shortest_path(self.graph, self, dst_node)
        hop = path[1]

        # Step 1: send RTS
        rts = Packet(self.name, hop.name, self.env.now, ptype="RTS")

        while self.channel.busy:
            with self.lock:
                self.STATE = "WAIT"
            yield self.env.timeout(1)

        with self.lock:
            self.STATE = "SEND"

        distance = self.graph[self][hop]["distance"]
        yield self.env.process(self.channel.transmit(distance))
        yield hop.queue.put(rts)

        # Step 2: wait for CTS
        timeout = 5
        start_wait = self.env.now

        while not getattr(self, "cts_received", False):
            if self.env.now - start_wait > timeout:
                print(self.env.now, self.name, "CTS timeout")
                with self.lock:
                    self.STATE = "IDLE"
                return
            yield self.env.timeout(1)

        self.cts_received = False

        # Step 3: send actual DATA
        while self.channel.busy:
            with self.lock:
                self.STATE = "WAIT"
            yield self.env.timeout(1)

        with self.lock:
            self.STATE = "SEND"

        yield self.env.process(self.channel.transmit(distance))
        yield hop.queue.put(packet)

        # Step 4: wait for ACK
        start_wait = self.env.now
        while not getattr(self, "ack_received", False):
            if self.env.now - start_wait > timeout:
                print(self.env.now, self.name, "ACK timeout")
                with self.lock:
                    self.STATE = "IDLE"
                return
            yield self.env.timeout(1)

        self.ack_received = False

        with self.lock:
            self.STATE = "IDLE"

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

            if packet.ptype == "RTS":
                # receiver says "ready"
                with self.lock:
                    self.STATE = "RECEIVE"

                cts = Packet(self.name, packet.src, self.env.now, ptype="CTS")

                src_node = next(n for n in self.graph.nodes if n.name == packet.src)
                distance = self.graph[self][src_node]["distance"]

                yield self.env.process(self.channel.transmit(distance))
                yield src_node.queue.put(cts)

            elif packet.ptype == "CTS":
                if packet.dst == self.name:
                    self.cts_received = True

            elif packet.ptype == "DATA":
                if packet.dst == self.name:
                    with self.lock:
                        self.STATE = "RECEIVE"

                    ack = Packet(self.name, packet.src, self.env.now, ptype="ACK")
                    src_node = next(n for n in self.graph.nodes if n.name == packet.src)
                    distance = self.graph[self][src_node]["distance"]

                    yield self.env.process(self.channel.transmit(distance))
                    yield src_node.queue.put(ack)
                else:
                    with self.lock:
                        self.STATE = "TRANSFER"
                    self.env.process(self.send(packet))

            elif packet.ptype == "ACK":
                if packet.dst == self.name:
                    self.ack_received = True

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name