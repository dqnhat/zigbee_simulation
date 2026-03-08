import simpy
import random
import networkx as nx

SIM_TIME = 100
PACKET_LOSS = 0.05
CSMA_BACKOFF = (1, 3)
TX_ENERGY = 0.8
RX_ENERGY = 0.3
IDLE_ENERGY = 0.02

packet_count = 0
packet_delivered = 0
total_delay = 0

redraw_flag = False

# -----------------------------
# Channel (shared medium)
# -----------------------------

class Channel:
    def __init__(self, env):
        self.env = env
        self.busy = False

    def transmit(self, duration):
        if self.busy:
            return False
        self.busy = True
        yield self.env.timeout(duration)
        self.busy = False
        return True

# -----------------------------
# ZigBee Packet
# -----------------------------

class Packet:
    def __init__(self, src, dst, time):
        global packet_count
        packet_count += 1
        self.id = packet_count
        self.src = src
        self.dst = dst
        self.start = time

# -----------------------------
# ZigBee Node
# -----------------------------

class ZigbeeNode:
    def __init__(self, env, name, ntype, graph, channel):
        self.env = env
        self.name = name
        self.ntype = ntype
        self.graph = graph
        self.channel = channel
        self.energy = 100
        self.queue = simpy.Store(env)
        self.process = env.process(self.run())
        env.process(self.receive())

    def send(self, packet):
        path = nx.shortest_path(self.graph, self.name, packet.dst)
        for hop in path[1:]:
            backoff = random.randint(*CSMA_BACKOFF)
            yield self.env.timeout(backoff)
            if random.random() < PACKET_LOSS:
                print(self.env.now, "Packet lost")
                return
            yield self.env.process(self.channel.transmit(1))
            self.energy -= TX_ENERGY
        global packet_delivered, total_delay
        packet_delivered += 1
        delay = self.env.now - packet.start
        total_delay += delay
        print(self.env.now, "Packet delivered delay", delay)

    def run(self):
        while True:
            yield self.env.timeout(random.randint(4, 8))
            if self.ntype == "end":
                packet = Packet(self.name, "Coordinator", self.env.now)
                print(self.env.now, self.name, "send packet")
                self.env.process(self.send(packet))
            self.energy -= IDLE_ENERGY

    def receive(self):
        while True:
            packet = yield self.queue.get()
            self.energy -= RX_ENERGY