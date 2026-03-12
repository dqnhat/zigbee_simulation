import simpy
import random
import math
import networkx as nx
import threading
from zigbee_channel import Channel


Wave_length = 3*10^8 / 2.4*10^9
"""
Calculate the theoretical wave length of radio signal.
λ = c / f = 0.125 (m)

Assumptions:
- Zigbee frequency: 2.4 GHz or 2.4 * 10^9 Hz
- Light speed: 3e8 m/s
"""

class ZigbeeNode:
    """
    A zigbee node, can be a divice cabable of transmiss or receive 2.4GHz signal
    """

    CSMA_BACKOFF_DEFAULT = 0.00032
    """
    Default value of CSMA backoff, often 0.32 ms or 20 symbols

    @Unit second
    """
    MINIMAL_SIGNAL_RECEIVE_STRENGTH = 3.16e-12
    """
    Minimal radio signal strength where node can process.
    Or -85 dBm (IEEE 802.15.4-2020, PHY specification).

    @Unit Watt
    """
    NODE_SIGNAL_BROUDCAST_STRENGTH = 0.001
    """
    1 mW or 0 dBm. This value depend on the node hardware.
    """

    name = "Node"
    """Name of the node, also use as id"""
    env : simpy.RealtimeEnvironment = None
    """ The enviroment simulation is running on, create from simpy"""
    graph : nx.Graph
    channel : Channel
    lock : threading.Lock

    Receive_signal_strength = 0
    """The receive signal strength (Watt)"""

    BackoffExponent = 2
    NumberOfBackoff = 4

    cts_received = False
    ack_received = False

    # TX_ENERGY = 0.8
    # RX_ENERGY = 0.3
    # IDLE_ENERGY = 0.02
    STATE = "IDLE"

    @property
    def MAX_TRANSMISSION_DISTANCE(self):
        """
        Calculate the theoretical maximum transmission distance.
        In reality, there are wall or terrain that block the signal.

        Uses the Friis free-space propagation equation:
        Pr = Pt * (λ / (4πd))²

        Assumptions:
        - Zigbee frequency: 2.4 GHz
        - Receiver sensitivity: -85 dBm
        - Transmit power: 1 mW
        """
        Distance = Wave_length / (4 * math.pi * math.sqrt(self.MINIMAL_SIGNAL_RECEIVE_STRENGTH / self.NODE_SIGNAL_BROUDCAST_STRENGTH))
        return Distance

    def transmission_time(self, packet_bits, distance):
        """
        Calculate total transmission time.

        Components:
        - Packet transmission time (serialization)
        - Propagation delay
        """

        DATA_RATE = 250000  # bits per second (IEEE 802.15.4 2.4GHz)
        LIGHT_SPEED = 3e8   # m/s

        tx_time = packet_bits / DATA_RATE
        propagation_time = distance / LIGHT_SPEED

        total_time = tx_time + propagation_time

        return total_time
    
    @staticmethod
    def transmission_strength(Pt, distance):
        """
        Calculate the theoretical maximum transmission distance.
        In reality, there are wall or terrain that block the signal.

        Uses the Friis free-space propagation equation:
        Pr = Pt * (λ / (4πd))²

        Assumptions:
        - Zigbee frequency: 2.4 GHz
        - Receiver sensitivity: -85 dBm
        - Transmit power: 1 mW
        """
        Pr = Pt * (Wave_length / (4 * math.pi * distance))**2
        return Pr

    def __init__(self, env, name, ntype, graph, channel, lock):
        self.env = env
        self.name = name
        self.ntype = ntype
        self.graph = graph
        self.channel = channel
        self.lock = lock

        self.queue = simpy.Store(env)
        env.process(self.receive())

    def send(self, packet):
        neighbors = nx.neighbors(self.graph, self)

        need_backoff = True
        self.NumberOfBackoff = 0
        backoff_time = self.CSMA_BACKOFF_DEFAULT
        while need_backoff:
            with self.lock:
                self.STATE = "WAIT"

            if self.NumberOfBackoff > 3:
                with self.lock:
                    self.STATE = "IDLE"

                print("Timeout")
                return
            
            self.env.timeout(backoff_time)

            if self.channel.busy:
                backoff_time = backoff_time * random.randint(1, (2**self.BackoffExponent) - 1)
                self.NumberOfBackoff = self.NumberOfBackoff + 1
            else:
                need_backoff = False

        for neighbor in neighbors:
            distance = self.graph.edges[self][neighbor]["distance"]
            message_send_time = self.transmission_time(packet.size, distance)
            self.env.process(send_with_delay(self.env, neighbor, packet, message_send_time))

            def send_with_delay(env, node, packet, delay):
                yield env.timeout(delay)
                node.queue.put(packet)

        # dst_node = next(n for n in self.graph.nodes if n.name == packet.dst)
        # path = nx.shortest_path(self.graph, self, dst_node)
        # hop = path[1]

        # # Step 1: send RTS
        # rts = Packet(self.name, hop.name, self.env.now, ptype="RTS")

        # while self.channel.busy:
        #     with self.lock:
        #         self.STATE = "WAIT"
        #     yield self.env.timeout(1)

        # with self.lock:
        #     self.STATE = "SEND"

        # distance = self.graph[self][hop]["distance"]
        # yield self.env.process(self.channel.transmit(distance))
        # yield hop.queue.put(rts)

        # # Step 2: wait for CTS
        # timeout = 5
        # start_wait = self.env.now

        # while not getattr(self, "cts_received", False):
        #     if self.env.now - start_wait > timeout:
        #         print(self.env.now, self.name, "CTS timeout")
        #         with self.lock:
        #             self.STATE = "IDLE"
        #         return
        #     yield self.env.timeout(1)

        # self.cts_received = False

        # # Step 3: send actual DATA
        # while self.channel.busy:
        #     with self.lock:
        #         self.STATE = "WAIT"
        #     yield self.env.timeout(1)

        # with self.lock:
        #     self.STATE = "SEND"

        # yield self.env.process(self.channel.transmit(distance))
        # yield hop.queue.put(packet)

        # # Step 4: wait for ACK
        # start_wait = self.env.now
        # while not getattr(self, "ack_received", False):
        #     if self.env.now - start_wait > timeout:
        #         print(self.env.now, self.name, "ACK timeout")
        #         with self.lock:
        #             self.STATE = "IDLE"
        #         return
        #     yield self.env.timeout(1)

        # self.ack_received = False

        # with self.lock:
        #     self.STATE = "IDLE"

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