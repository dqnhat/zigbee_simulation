import simpy
import random
import networkx as nx

class Packet:
    def __init__(self, src, dst, time, ptype="DATA"):
        self.src = src
        self.dst = dst
        self.start = time

        # Header
        self.packet_id = random.randint(0, 1000000)
        self.ptype = ptype   # "RTS", "CTS", "DATA", "ACK"
        self.size = 8*100 # 100 byte as bit
        
        # Data