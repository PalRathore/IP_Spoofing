# Detection Logic

This document explains the detection mechanism implemented in the packet analyzer, including the metrics used, the detection rule, its rationale, and its limitations.

---

## Overview

The detection mechanism is rule-based and operates on aggregate TCP flag statistics. It does not perform deep packet inspection, stateful connection tracking, or machine learning. The approach relies on a fundamental property of TCP: spoofed SYN packets cannot complete the three-way handshake.

---

## Metrics Tracked

The analyzer extracts two counters from live packet capture:

### SYN Count

- Incremented when a TCP packet has the SYN flag set and the ACK flag **not** set
- This isolates initial connection request packets (the first step of the TCP handshake)
- SYN-ACK packets (which have both SYN and ACK flags set) are excluded from this count

### ACK Count

- Incremented when a TCP packet has the ACK flag set
- This includes:
  - The third step of the handshake (client ACK)
  - Data transfer ACKs
  - SYN-ACK packets from the server
- ACK count serves as a proxy for successful or in-progress connections

### Reporting Interval

The analyzer prints cumulative SYN and ACK counts every 50 packets:

```go
if (synCount+ackCount)%50 == 0 {
    fmt.Printf("SYN: %d | ACK: %d\n", synCount, ackCount)
}
```

---

## Detection Rule

```
If SYN count > (ACK count * 3), traffic is flagged as suspicious.
```

Equivalently: if the SYN/ACK ratio exceeds 3.0, then spoofing is likely occurring.

### Threshold Selection

The threshold of 3.0 was selected based on observed behavior:

| Traffic Type | Observed SYN/ACK Ratio |
|---|---|
| Normal TCP | 0.38 - 0.40 |
| Spoofed TCP | 38.00 - 104.00 |

The gap between normal (below 0.5) and spoofed (above 38.0) ratios is large. A threshold of 3.0 provides a wide margin above normal traffic while remaining well below observed spoofing ratios.

---

## Why This Rule Works

### Normal TCP Behavior

In a legitimate TCP connection:

1. Client sends SYN (SYN count +1)
2. Server responds with SYN-ACK (ACK count +1)
3. Client sends ACK (ACK count +1)
4. Data transfer generates additional ACKs

Result: ACK count equals or exceeds SYN count. The ratio stays below 1.0.

### Spoofed TCP Behavior

When SYN packets have a fake source IP:

1. Client sends SYN with spoofed source (SYN count +1)
2. Server sends SYN-ACK to the spoofed address (may or may not be captured depending on routing)
3. No ACK is returned because the spoofed IP does not correspond to a real host

Result: SYN count increases while ACK count remains near zero. The ratio diverges sharply.

---

## Detection Flow

```
Capture packet on interface
        |
        v
Is it a TCP packet?
  |           |
  No          Yes
  |           |
  skip        |
              v
       Check TCP flags
       |              |
  SYN && !ACK      ACK set
       |              |
  synCount++     ackCount++
       |              |
       v              v
   Every 50 packets:
   Print SYN and ACK counts
              |
              v
   Compute SYN/ACK ratio
              |
              v
   Ratio > 3.0?
     |          |
    Yes         No
     |          |
   FLAG:       Normal
   Suspicious  traffic
```

---

## Supplementary Indicators

Beyond the SYN/ACK ratio, the analyzer tracks additional metrics that reinforce detection confidence:

### Unique Source IP Count

- Normal traffic produces a small number of unique source IPs (typically 1)
- Spoofed traffic generates many unique source IPs per window (observed: 34-87)
- A sudden increase in unique source IPs during a high SYN/ACK ratio window strongly indicates spoofing

### Connection Success Rate

- Defined as the proportion of SYN packets that result in completed connections
- Normal traffic: success rate of 1 (all connections complete)
- Spoofed traffic: success rate of 0 (no connections complete)

---

## Limitations

### False Positives

- **Legitimate SYN retransmissions:** If a server is slow to respond, clients may retransmit SYN packets, temporarily inflating the SYN count. This could push the ratio above the threshold.
- **Asymmetric routing:** In networks where outbound and inbound traffic take different paths, the analyzer may capture SYN packets but not the corresponding ACKs.
- **Network congestion:** Heavy packet loss affecting ACK packets more than SYN packets could skew the ratio.

### False Negatives

- **Low-rate spoofing:** An attacker sending spoofed SYN packets at a rate comparable to normal traffic could keep the SYN/ACK ratio below the threshold.
- **ACK injection:** An attacker who also injects fake ACK packets would artificially balance the SYN/ACK ratio, evading detection.

### Protocol Scope

- **TCP only:** The analyzer does not parse UDP, ICMP, or other protocols. UDP-based attacks (such as the reflection attack in this project) are invisible to the current detection logic.
- **No per-flow tracking:** The analyzer computes global SYN and ACK totals. It cannot identify which specific source IPs are spoofed versus legitimate.

### Environmental Constraints

- **Single interface:** The analyzer monitors only `enp0s3`. Traffic on other interfaces is not captured.
- **No persistence:** Counts reset when the analyzer is restarted. There is no logging to disk or historical analysis.
- **No alerting:** Detection results are printed to stdout only. There is no integration with external monitoring or alerting systems.
