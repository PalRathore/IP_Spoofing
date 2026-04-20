# Architecture

This document describes the system architecture, component responsibilities, data flow, and the structural differences between the TCP spoofing and UDP reflection attack paths.

---

## System Components

### Attacker (Simulator)

- **Location:** VM1 (192.168.100.10)
- **Runtime:** Python 3 with Scapy
- **Responsibility:** Generates both legitimate and malicious network traffic
- **Scripts:**
  - `spoof.py` -- Sends 2000 TCP SYN packets with randomized fake source IPs (10.0.0.x range) to the victim on port 8080
  - `reflect_udp.py` -- Sends UDP packets to a reflector service with the victim's IP spoofed as the source address

The attacker does not maintain any state. Each script runs independently as a one-shot operation.

### Victim Server

- **Location:** VM2 (192.168.100.20)
- **Runtime:** Python 3 (standard library `socket` module)
- **Responsibility:** Receives and logs incoming connections
- **Scripts:**
  - `server.py` -- TCP server listening on port 8080, accepts connections and prints the source address before closing
  - `udp_reflector.py` -- UDP server listening on port 9999, echoes received data back to the source address

The victim operates passively. It does not validate or filter incoming traffic.

### Analyzer

- **Location:** VM1 (192.168.100.10), same machine as the attacker
- **Runtime:** Go with gopacket and libpcap
- **Responsibility:** Passively captures all packets traversing the network interface and computes TCP flag statistics
- **Behavior:**
  - Opens `enp0s3` in promiscuous mode
  - Counts packets with the SYN flag set (without ACK) as SYN packets
  - Counts packets with the ACK flag set as ACK packets
  - Reports cumulative counts every 50 packets
  - Applies detection rule: if SYN/ACK ratio exceeds 3, flags traffic as suspicious

The analyzer does not inject or modify any traffic.

---

## Network Topology

```
+----------------------------------+
|           Attacker VM            |
|         192.168.100.10           |
|                                  |
|   +---------+    +-------------+ |
|   |spoof.py |    |reflect_udp  | |
|   +----+----+    +------+------+ |
|        |               |         |
|   +----+---------------+------+  |
|   |       enp0s3 (NIC)        |  |
|   +----+---------------+------+  |
|        |               |         |
|   +----+----+          |         |
|   |analyzer |          |         |
|   |  .go    |          |         |
|   +---------+          |         |
+--------|---------------|--------+
         |               |
    +----+---------------+----+
    |  Internal Network       |
    |  Name: labnet           |
    |  Type: VirtualBox       |
    |  Internal Network       |
    +----+---------------+----+
         |               |
+--------|---------------|--------+
|   +----+----+    +-----+-----+  |
|   |server.py|    |udp_reflect|  |
|   |TCP :8080|    |UDP :9999  |  |
|   +---------+    +-----------+  |
|                                 |
|           Victim VM             |
|         192.168.100.20          |
+---------------------------------+
```

---

## Data Flow

### TCP Spoofing Path

```
spoof.py (VM1)
    |
    | Sends TCP SYN with src=10.0.0.x, dst=192.168.100.20:8080
    v
server.py (VM2)
    |
    | Receives SYN, sends SYN-ACK to 10.0.0.x (nonexistent)
    | No ACK is returned -> half-open connection
    v
analyzer.go (VM1)
    |
    | Captures SYN packets on interface
    | SYN count increments, ACK count does not
    | SYN/ACK ratio diverges -> detection triggered
```

**Key observation:** The spoofed source IP (10.0.0.x) has no valid host behind it on the internal network. The victim's SYN-ACK response is sent to a nonexistent address and is never acknowledged. This produces a measurable imbalance between SYN and ACK counts.

### UDP Reflection Path

```
reflect_udp.py (VM1)
    |
    | Sends UDP to 192.168.100.30:9999 with src=192.168.100.20
    v
udp_reflector.py (VM2 or VM3)
    |
    | Receives UDP from "192.168.100.20" (spoofed)
    | Echoes data back to 192.168.100.20
    v
Victim (VM2) at 192.168.100.20
    |
    | Receives unrequested UDP traffic from reflector
```

**Key observation:** The reflector has no way to verify the source address in the UDP packet. It responds to the spoofed source (the victim), amplifying traffic toward a target that never initiated communication.

### Normal Traffic Path

```
curl (VM1)
    |
    | TCP SYN to 192.168.100.20:8080
    v
server.py (VM2)
    |
    | SYN-ACK to 192.168.100.10
    v
curl (VM1)
    |
    | ACK to 192.168.100.20 -> handshake complete
    v
analyzer.go (VM1)
    |
    | SYN and ACK counts increment proportionally
    | SYN/ACK ratio remains near 1.0
```

---

## TCP vs UDP: Structural Differences

| Aspect | TCP Spoofing Attack | UDP Reflection Attack |
|---|---|---|
| Protocol | TCP | UDP |
| Attack mechanism | SYN flood with fake source IPs | Source IP spoofing to redirect reflector responses |
| Handshake | Three-way handshake is disrupted (never completes) | No handshake exists (UDP is connectionless) |
| Victim impact | Half-open connections consume server resources | Unsolicited inbound traffic floods the victim |
| Analyzer detection | SYN/ACK ratio divergence detected by analyzer | Not detected by current TCP-only analyzer |
| Third party involved | No | Yes (reflector service) |
| Amplification | 1:1 (each SYN produces one SYN-ACK) | Depends on reflector response size relative to request |

---

## Design Decisions

- **Analyzer on attacker VM:** The analyzer runs on the same machine as the attacker because VirtualBox internal networking allows the interface to observe all traffic in promiscuous mode. This avoids the need for a dedicated monitoring VM.
- **Separate TCP and UDP victim services:** The TCP server (`server.py`) and UDP reflector (`udp_reflector.py`) are isolated into separate processes to avoid coupling the two attack scenarios.
- **Go for the analyzer:** Go was chosen for its native concurrency support and the availability of gopacket, which provides efficient access to libpcap without the overhead of interpreted languages.
- **Python for attack scripts:** Scapy provides a high-level API for packet crafting that makes it straightforward to manipulate IP headers and TCP/UDP flags without writing raw socket code.
