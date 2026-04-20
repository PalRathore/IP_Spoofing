# Experiment Results

This document presents the findings from each experimental scenario, comparing traffic behavior across normal, spoofed, and reflection-based conditions.

---

## Summary of Experiments

| Experiment | Protocol | Traffic Type | SYN/ACK Ratio | Detection Triggered |
|---|---|---|---|---|
| Normal TCP | TCP | Legitimate | 0.38 - 0.40 | No |
| Normal UDP | UDP | Legitimate | 0.00 (N/A) | No |
| SYN Spoofing | TCP | Spoofed | 38.00 - 104.00 | Yes |
| UDP Reflection | UDP | Spoofed | 0.00 (N/A) | No (TCP-only analyzer) |
| Mixed Traffic | TCP | Legitimate + Spoofed | Crosses threshold during attack | Yes |

---

## Experiment 1: Normal TCP Traffic

### Conditions

- 30 sequential `curl` requests from VM1 to VM2 on port 8080
- 200ms delay between requests
- All connections use the attacker's real IP (192.168.100.10)

### Observed Metrics

| Metric | Value |
|---|---|
| SYN count | 5 - 6 per window |
| ACK count | 12 - 14 per window |
| SYN/ACK ratio | 0.38 - 0.40 |
| Unique source IPs | 1 |
| Connection success rate | 1 |

### Analysis

The SYN/ACK ratio remains below 1.0 because each successful TCP connection generates one SYN but multiple ACK packets (the initial handshake ACK plus data transfer ACKs). The single unique source IP confirms that all traffic originates from the legitimate attacker address. No detection alert is triggered.

---

## Experiment 2: Normal UDP Traffic

### Conditions

- UDP packets sent from VM1 to the reflector service on VM2 (port 9999)
- Legitimate source IP used (no spoofing)
- Analyzer running simultaneously

### Observed Metrics

| Metric | Value |
|---|---|
| SYN count | 0 |
| ACK count | 0 |
| SYN/ACK ratio | 0.00 |
| Connection success rate | 0 |

### Analysis

The analyzer's TCP-specific counters remain at zero throughout the UDP experiment. This is expected behavior: UDP packets do not contain TCP flags, so the analyzer's SYN/ACK tracking logic does not engage. The victim's tcpdump confirms normal bidirectional UDP traffic on port 9999.

---

## Experiment 3: TCP SYN Spoofing Attack

### Conditions

- 2000 TCP SYN packets sent from VM1 to VM2 on port 8080
- Source IP randomized from the 10.0.0.1-254 range
- Delay of 0.001 seconds between packets

### Observed Metrics (across successive 2-second traffic windows)

| Window | SYN | ACK | SYN/ACK Ratio | Unique Source IPs | Detection |
|---|---|---|---|---|---|
| 1 | 60 | 0 | 60.00 | 54 | SPOOFING DETECTED (stable) |
| 2 | 38 | 0 | 38.00 | 34 | SPOOFING DETECTED (stable) |
| 3 | 104 | 0 | 104.00 | 87 | SPOOFING DETECTED (stable) |
| 4 | 88 | 0 | 88.00 | 75 | SPOOFING DETECTED (stable) |
| 5 | 62 | 0 | 62.00 | 53 | SPOOFING DETECTED (stable) |

### Analysis

The ACK count remains at 0 across all traffic windows. This occurs because the spoofed source IPs (10.0.0.x) do not correspond to any real host on the internal network. The victim sends SYN-ACK responses to these nonexistent addresses, and no ACK is ever returned to complete the handshake.

The high number of unique source IPs (ranging from 34 to 87 per window) further confirms spoofing activity. In normal traffic, only one or a small number of unique source IPs would be observed.

The detection mechanism correctly triggers the "SPOOFING DETECTED" alert in every window, as the SYN/ACK ratio far exceeds the threshold of 3.0.

---

## Experiment 4: UDP Reflection Attack

### Conditions

- UDP packets sent continuously from VM1 to the reflector on port 9999
- Source IP in the UDP packets is set to the victim's IP (192.168.100.20)
- The reflector echoes all received data back to the spoofed source (the victim)

### Observed Metrics

| Metric | Value |
|---|---|
| SYN count | 0 |
| ACK count | 0 |
| SYN/ACK ratio | 0.00 |
| Analyzer detection | None |

### Analysis

The current analyzer does not detect the UDP reflection attack because it only monitors TCP flags. However, the attack is observable through other means:

- **tcpdump on the victim** shows a continuous stream of incoming UDP packets from the reflector's IP address
- **The reflector's output** logs the spoofed source address (192.168.100.20), believing the victim initiated the communication
- **The victim** receives unsolicited traffic that it never requested

This highlights a limitation of TCP-only detection: UDP-based spoofing attacks require separate detection mechanisms.

---

## Comparative Analysis

### TCP: Normal vs Spoofed

| Attribute | Normal TCP | Spoofed TCP |
|---|---|---|
| Handshake completion | Full (SYN, SYN-ACK, ACK) | Incomplete (SYN only) |
| SYN/ACK ratio | 0.38 - 0.40 | 38.00 - 104.00 |
| Unique source IPs | 1 | 34 - 87 per window |
| Connection success rate | 1 | 0 |
| Server behavior | Accepts and closes connections | Accumulates half-open connections |

### UDP: Normal vs Reflection

| Attribute | Normal UDP | UDP Reflection |
|---|---|---|
| Source IP | Real (192.168.100.10) | Spoofed (192.168.100.20) |
| Traffic direction | Bidirectional (request/response) | Unidirectional toward victim |
| Victim involvement | Active participant | Passive recipient of unrequested traffic |
| Reflector awareness | N/A | Unaware of spoofing |

### Spoofed TCP vs UDP Reflection

| Attribute | TCP SYN Spoofing | UDP Reflection |
|---|---|---|
| Protocol | TCP | UDP |
| Intermediary required | No | Yes (reflector service) |
| Detectable by current analyzer | Yes | No |
| Resource exhaustion target | Server connection table (half-open states) | Network bandwidth (unsolicited inbound traffic) |
| Source verification possible | Yes (SYN/ACK ratio analysis) | Requires UDP-specific analysis |

---

## Key Findings

1. **SYN/ACK ratio is a reliable indicator for TCP spoofing detection.** In all spoofed traffic windows, the ratio exceeded 38.0, while normal traffic remained below 0.5. The separation between normal and spoofed ranges is substantial.

2. **Unique source IP count provides secondary confirmation.** Normal traffic produced 1 unique source IP. Spoofed traffic produced 34-87 unique source IPs per 2-second window.

3. **UDP reflection attacks evade TCP-specific detection.** The analyzer's SYN/ACK tracking is blind to UDP traffic. Detecting UDP reflection requires protocol-specific analysis (e.g., monitoring for asymmetric UDP flows or unexpected source addresses).

4. **Connection success rate drops to zero under spoofing.** Since spoofed connections cannot complete the handshake, the connection success metric provides a clear binary indicator when combined with the SYN/ACK ratio.
