# Code Explanation

This document provides a detailed explanation of each source file in the project, including its purpose, behavior, and role within the system.

---

## analyzer.go

**Location:** `analyzer/analyzer.go`

**Language:** Go

**Dependencies:** `github.com/google/gopacket`, `github.com/google/gopacket/layers`, `github.com/google/gopacket/pcap`

### Purpose

The analyzer is the detection component of the system. It passively captures all packets on the network interface, parses TCP headers, and tracks the ratio of SYN to ACK flags to identify spoofing anomalies.

### Behavior

1. Opens the `enp0s3` interface in promiscuous mode using libpcap with a snapshot length of 1600 bytes and blocking read mode
2. Creates a packet source that iterates over all captured packets
3. Initializes two counters: `synCount` and `ackCount`
4. For each captured packet:
   - Checks if the packet contains a TCP layer
   - If the TCP SYN flag is set and the ACK flag is not set, increments `synCount`
   - If the TCP ACK flag is set, increments `ackCount`
   - Every 50 packets (combined SYN + ACK), prints the current counts
5. Runs indefinitely until terminated with Ctrl+C

### Key Code Sections

```go
handle, err := pcap.OpenLive("enp0s3", 1600, true, pcap.BlockForever)
```
Opens a live packet capture on the specified interface. The `true` parameter enables promiscuous mode. `pcap.BlockForever` means the read operation blocks until a packet is available.

```go
if tcp.SYN && !tcp.ACK {
    synCount++
}
```
Counts pure SYN packets (connection initiation requests). The `!tcp.ACK` condition excludes SYN-ACK packets sent by the server.

```go
if tcp.ACK {
    ackCount++
}
```
Counts all packets with the ACK flag set, including SYN-ACK responses and data acknowledgments.

### Role in System

The analyzer is the core detection mechanism. It runs on the attacker VM and monitors all traffic flowing through the shared internal network interface. It does not modify or inject any packets.

---

## spoof.py

**Location:** `simulator/spoof.py`

**Language:** Python 3

**Dependencies:** Scapy

### Purpose

Simulates a TCP SYN flood attack by sending a large number of SYN packets with randomly generated fake source IP addresses. This creates incomplete TCP handshakes on the victim server.

### Behavior

1. Sets the target IP to `192.168.100.20` (victim server)
2. Loops 2000 times, and for each iteration:
   - Generates a random source IP in the format `10.0.0.x` where x is between 1 and 254
   - Constructs an IP packet with the fake source and real destination
   - Attaches a TCP segment with destination port 8080 and the SYN flag set
   - Sends the packet without printing per-packet output (`verbose=0`)

### Key Code Sections

```python
fake_ip = f"10.0.0.{random.randint(1,254)}"
```
Generates a randomized source IP from a range that does not exist on the internal network. This ensures that the victim's SYN-ACK responses have no valid destination.

```python
pkt = IP(src=fake_ip, dst=target)/TCP(dport=8080, flags="S")
```
Constructs a packet with a spoofed IP header and a TCP header containing only the SYN flag. The `/` operator in Scapy stacks protocol layers.

```python
send(pkt, verbose=0)
```
Sends the packet at the IP layer (Layer 3). Scapy handles Ethernet framing automatically.

### Role in System

This script is the primary attack tool. It generates the spoofed traffic that the analyzer is designed to detect. The high volume of SYN packets from diverse fake IPs creates a measurable SYN/ACK imbalance.

---

## server.py

**Location:** `victim/server.py`

**Language:** Python 3

**Dependencies:** None (standard library only)

### Purpose

Acts as the victim TCP server. It listens for incoming TCP connections on port 8080 and logs the source address of each connection.

### Behavior

1. Creates a TCP socket (`SOCK_STREAM`)
2. Binds to all interfaces (`0.0.0.0`) on port 8080
3. Enters listening mode
4. Prints "Server running..." to confirm startup
5. Enters an infinite loop:
   - Accepts incoming connections
   - Prints the source IP and port
   - Immediately closes the connection

### Key Code Sections

```python
s.bind((HOST, PORT))
s.listen()
```
The empty `listen()` call uses the system default backlog. Under SYN flood conditions, the kernel's SYN queue may fill up as half-open connections accumulate.

```python
conn, addr = s.accept()
print("Connection from:", addr)
conn.close()
```
Only fully established connections (completed three-way handshake) appear in `accept()`. During a spoofing attack, `accept()` blocks because spoofed connections never complete the handshake.

### Role in System

The server provides a concrete target for both normal and spoofed traffic. In normal conditions, it successfully accepts and logs connections. Under spoofing conditions, it demonstrates the impact of incomplete handshakes by stalling on `accept()`.

---

## reflect_udp.py

**Location:** `simulator/reflect_udp.py`

**Language:** Python 3

**Dependencies:** Scapy

### Purpose

Simulates a UDP reflection/amplification attack by sending UDP packets to a reflector service with the victim's IP address spoofed as the source.

### Behavior

1. Sets the victim IP to `192.168.100.20` and the reflector IP to `192.168.100.30`
2. Constructs an IP packet with:
   - Source IP: victim's address (spoofed)
   - Destination IP: reflector's address
3. Adds a UDP layer targeting port 9999 and a raw payload ("test")
4. Sends the packet in a continuous loop (`loop=1`)

### Key Code Sections

```python
packet = IP(src=victim_ip, dst=reflector_ip)/UDP(dport=9999)/Raw(load="test")
```
The critical element is `src=victim_ip`: the source IP is set to the victim's address, not the attacker's. When the reflector processes this packet, it sends its response to the victim.

```python
send(packet, loop=1)
```
The `loop=1` parameter causes Scapy to send the packet repeatedly in an infinite loop, simulating sustained attack traffic.

### Role in System

This script demonstrates a different class of IP spoofing: reflection-based attacks. Unlike the TCP SYN flood, which directly targets the victim, this attack uses a third-party reflector to indirect traffic toward the victim. The victim receives unsolicited UDP traffic from the reflector.

---

## udp_reflector.py

**Location:** `victim/udp_reflector.py`

**Language:** Python 3

**Dependencies:** None (standard library only)

### Purpose

Acts as a UDP echo service that reflects any received data back to the sender. In the context of the reflection attack, the "sender" is actually the victim (due to source IP spoofing).

### Behavior

1. Creates a UDP socket (`SOCK_DGRAM`)
2. Binds to all interfaces (`0.0.0.0`) on port 9999
3. Prints "UDP reflector running..." to confirm startup
4. Enters an infinite loop:
   - Receives up to 1024 bytes of data along with the sender's address
   - Prints the sender's address
   - Sends the received data back to the sender's address

### Key Code Sections

```python
data, addr = sock.recvfrom(1024)
```
Receives a UDP datagram. The `addr` tuple contains the source IP and port from the packet header. When the source IP is spoofed, `addr` contains the victim's address.

```python
sock.sendto(data, addr)
```
Echoes the data to the address extracted from the incoming packet. Since `addr` contains the victim's spoofed address, the response is sent to the victim instead of the actual attacker.

### Role in System

The reflector is the unwitting intermediary in the reflection attack. It has no mechanism to verify whether the source address in incoming UDP packets is legitimate. Its echo behavior amplifies the attack by directing responses toward the victim.

---

## File Summary

| File | Language | Role | Protocol | Active/Passive |
|---|---|---|---|---|
| `analyzer.go` | Go | Detection | TCP (capture) | Passive |
| `spoof.py` | Python | Attack (SYN flood) | TCP | Active |
| `reflect_udp.py` | Python | Attack (reflection) | UDP | Active |
| `server.py` | Python | Victim (TCP) | TCP | Passive |
| `udp_reflector.py` | Python | Victim (reflector) | UDP | Passive |
