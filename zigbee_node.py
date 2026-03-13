import simpy
import random
import math
import networkx as nx
import threading
from collections import deque
from zigbee_packet import Packet


Wave_length = 3*10**8 / 2.4*10**9
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
    lock : threading.Lock

    Receive_signal_strength = 0
    """The receive signal strength (Watt)"""

    processed_packets = deque(maxlen=10)

    BackoffExponent = 3
    NumberOfBackoff = 4

    cts_received = False
    ack_received = False

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
    
    @property
    def busy(self):
        """
        Check if the node is currently busy transmitting or receiving.
        """
        return self.Receive_signal_strength > self.MINIMAL_SIGNAL_RECEIVE_STRENGTH

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

    def __init__(self, env, name, ntype, graph, lock):
        self.env = env
        self.name = name
        self.ntype = ntype
        self.graph = graph
        self.lock = lock
        self.processed_packets = deque(maxlen=10)

        self.queue = simpy.Store(env)
        env.process(self.receive())
        env.process(self.run())

    def send(self, packet):
        neighbors : ZigbeeNode = nx.neighbors(self.graph, self)

        need_backoff = True
        self.NumberOfBackoff = 0
        backoff_time = self.CSMA_BACKOFF_DEFAULT
        while need_backoff:

            if self.NumberOfBackoff > 1:
                with self.lock:
                    self.STATE = "WAIT"

            if self.NumberOfBackoff > 3:
                with self.lock:
                    self.STATE = "IDLE"

                print("Timeout")
                return
            
            yield self.env.timeout(backoff_time)

            if self.busy:
                backoff_time = backoff_time * random.randint(1, (2**self.BackoffExponent) - 1)
                self.NumberOfBackoff = self.NumberOfBackoff + 1
            else:
                need_backoff = False

        if packet.packet_id not in self.processed_packets:
            self.processed_packets.append(packet.packet_id)

        def send_with_delay(env, srcNode, desNode, distance, packet, delay):
            yield env.timeout(delay)
            desNode.queue.put(packet)
            desNode.Receive_signal_strength = desNode.Receive_signal_strength - srcNode.transmission_strength(srcNode.NODE_SIGNAL_BROUDCAST_STRENGTH, distance)

        self.Receive_signal_strength = self.Receive_signal_strength + self.NODE_SIGNAL_BROUDCAST_STRENGTH

        for neighbor in neighbors:
            distance = self.graph.edges[self, neighbor]["distance"]
            message_send_time = self.transmission_time(packet.size, distance)
            neighbor.Receive_signal_strength = neighbor.Receive_signal_strength + self.transmission_strength(self.NODE_SIGNAL_BROUDCAST_STRENGTH, distance)
            self.env.process(send_with_delay(self.env, self, neighbor, distance, packet, message_send_time))

        yield self.env.timeout(self.transmission_time(packet.size, 0))
        self.Receive_signal_strength = self.Receive_signal_strength - self.NODE_SIGNAL_BROUDCAST_STRENGTH
        with self.lock:
            self.STATE = "IDLE"

    def run(self):
        while True:
            yield self.env.timeout(random.randint(0, 30)/1000)

            if self.ntype == "end":
                end_nodes = [
                    n for n in self.graph.nodes
                    if n.ntype == "end" and n.name != self.name
                ]

                if end_nodes:
                    dst = random.choice(end_nodes)
                    packet = Packet(self.name, dst.name, self.env.now)
                    print()
                    print(self.env.now, self.name, "send packet to", dst.name)
                    with self.lock:
                        self.STATE = "SEND"
                    self.env.process(self.send(packet))

    def receive(self):
        while True:
            packet = yield self.queue.get()

            if packet.packet_id in self.processed_packets:
                continue

            self.processed_packets.append(packet.packet_id)

            if packet.dst == self.name:
                print(self.env.now, self.name, "received packet from", packet.src)
                with self.lock:
                    self.STATE = "RECEIVE"
            else:
                if self.ntype != "end":
                    print(self.env.now, self.name, "forward packet from", packet.src, "to", packet.dst)
                    with self.lock:
                        self.STATE = "TRANSMISS"
                    self.env.process(self.send(packet))

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name