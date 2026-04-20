# Execution Guide

This document provides the exact sequence of commands required to run each experiment. All commands assume the environment has been fully set up according to the [Setup Guide](SETUP_GUIDE.md).

---

## Prerequisites Checklist

Before executing any experiment, confirm:

- [ ] Both VMs are running and connected to the `labnet` internal network
- [ ] Static IPs are assigned and verified (192.168.100.10 and 192.168.100.20)
- [ ] `ping` between VMs succeeds in both directions
- [ ] The analyzer binary has been compiled on VM1
- [ ] Scapy is installed on VM1 (`pip3 install scapy`)

---

## Experiment 1: Normal TCP Traffic

This experiment establishes a baseline by generating legitimate TCP connections.

### VM2 (Victim) -- Start the TCP Server

```bash
sudo python3 server.py
```

**Expected output:**
```
Server running...
```

The server is now listening on port 8080 and will print each incoming connection.

### VM1 (Attacker) -- Start the Analyzer

```bash
cd ~/analyzer
sudo ./analyzer
```

The analyzer begins capturing packets on `enp0s3`. No output is printed until packets are detected.

### VM1 (Attacker) -- Generate Normal Traffic

Open a second terminal on VM1 and run:

```bash
for i in $(seq 1 30); do curl --interface enp0s3 192.168.100.20:8080; sleep 0.2; done
```

This sends 30 sequential TCP connections to the victim server with a 200ms delay between each.

### Expected Behavior

**Analyzer output:**
```
SYN: 6 | ACK: 14
SYN: 5 | ACK: 12
```

- SYN and ACK counts remain closely balanced
- SYN/ACK ratio stays below 1.0
- Connection success rate is reported as 1

**Victim output:**
```
Connection from: ('192.168.100.10', <port>)
Connection from: ('192.168.100.10', <port>)
...
```

Each connection originates from the attacker's real IP address.

---

## Experiment 2: TCP SYN Spoofing Attack

This experiment sends spoofed TCP SYN packets to observe incomplete handshakes and trigger detection.

### VM2 (Victim) -- Ensure Server is Running

```bash
sudo python3 server.py
```

### VM1 (Attacker) -- Start the Analyzer

```bash
sudo ./analyzer
```

### VM1 (Attacker) -- Launch Spoofing Attack

Open a second terminal on VM1:

```bash
sudo python3 simulator/spoof.py
```

This sends 2000 TCP SYN packets with randomized source IPs from the 10.0.0.1-254 range to the victim on port 8080.

### Expected Behavior

**Analyzer output:**
```
SYN: 60 | ACK: 0
SYN/ACK Ratio: 60.00
Unique Source IPs: 54
Connection Success Rate: 0
SPOOFING DETECTED (stable)
```

- SYN count increases rapidly
- ACK count remains at 0 or very low
- SYN/ACK ratio exceeds the detection threshold (3.0)
- The analyzer prints a spoofing detection alert

**Victim tcpdump (optional verification):**
```bash
sudo tcpdump -i enp0s3 tcp
```

Output shows SYN packets arriving from various 10.0.0.x addresses with no corresponding ACK responses.

---

## Experiment 3: UDP Reflection Attack

This experiment demonstrates amplification-based spoofing using UDP.

### VM2 (Victim) -- Start the UDP Reflector

```bash
sudo python3 udp_reflector.py
```

**Expected output:**
```
UDP reflector running...
```

### VM1 (Attacker) -- Start the Analyzer

```bash
sudo ./analyzer
```

### VM1 (Attacker) -- Launch Reflection Attack

```bash
sudo python3 simulator/reflect_udp.py
```

This sends UDP packets to the reflector at 192.168.100.30:9999 (or the victim at 192.168.100.20:9999 depending on topology) with the victim's IP (192.168.100.20) set as the source address.

### Expected Behavior

**Analyzer output:**
```
SYN: 0 | ACK: 0
SYN/ACK Ratio: 0.00
```

The TCP-specific analyzer does not detect UDP traffic. SYN and ACK counts remain at zero throughout.

**Victim tcpdump (verification):**
```bash
sudo tcpdump -i enp0s3 udp
```

Output shows a continuous stream of incoming UDP packets from the reflector's IP address, directed to the victim despite the victim never initiating communication.

**Reflector output:**
```
Received from: ('192.168.100.20', <port>)
Received from: ('192.168.100.20', <port>)
...
```

The reflector believes the packets originated from the victim.

---

## Experiment 4: Mixed Traffic

This experiment combines normal and spoofed traffic to verify that the analyzer can detect spoofing even in the presence of legitimate connections.

### Execution

1. Start the victim server and analyzer as in Experiments 1 and 2
2. Begin generating normal traffic:
   ```bash
   for i in $(seq 1 30); do curl --interface enp0s3 192.168.100.20:8080; sleep 0.2; done
   ```
3. While normal traffic is running, open another terminal and launch the spoofing attack:
   ```bash
   sudo python3 simulator/spoof.py
   ```

### Expected Behavior

- The analyzer initially reports balanced SYN/ACK ratios during normal traffic
- Once spoofed traffic begins, SYN counts spike while ACK counts grow slowly
- The SYN/ACK ratio crosses the detection threshold and triggers a spoofing alert
- The detection mechanism correctly identifies the anomaly despite mixed traffic

---

## Command Summary

| Step | VM | Command | Purpose |
|---|---|---|---|
| 1 | VM2 | `sudo python3 server.py` | Start TCP victim server |
| 2 | VM2 | `sudo python3 udp_reflector.py` | Start UDP reflector (for UDP experiments) |
| 3 | VM1 | `sudo ./analyzer` | Start packet analyzer |
| 4 | VM1 | `for i in $(seq 1 30); do curl ... ; done` | Generate normal TCP traffic |
| 5 | VM1 | `sudo python3 simulator/spoof.py` | Execute SYN spoofing attack |
| 6 | VM1 | `sudo python3 simulator/reflect_udp.py` | Execute UDP reflection attack |
| 7 | Either | `sudo tcpdump -i enp0s3 tcp` or `udp` | Manual packet verification |

---

## Stopping Services

- **Analyzer / Server / Reflector:** Press `Ctrl+C` in the respective terminal.
- **Spoofing script:** Terminates automatically after sending all 2000 packets.
- **Reflection script:** Runs in a loop; press `Ctrl+C` to stop.
