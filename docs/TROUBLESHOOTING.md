# Troubleshooting

This document lists common issues encountered during setup and execution, along with their causes and solutions.

---

## Network Issues

### Problem: VMs cannot ping each other

| Possible Cause | Solution |
|---|---|
| Different internal network names | Verify both VMs use the same network name (`labnet`) in VirtualBox settings |
| Netplan not applied | Run `sudo netplan apply` on both VMs |
| Interface is DOWN | Run `sudo ip link set enp0s3 up` |
| Incorrect IP configuration | Verify IPs with `ip a` and ensure both are on the 192.168.100.0/24 subnet |
| Firewall blocking ICMP | Disable UFW temporarily: `sudo ufw disable` |

### Problem: Adapter not listed in VirtualBox

| Possible Cause | Solution |
|---|---|
| Adapter not enabled | In VM Settings > Network, ensure Adapter 1 is checked as enabled |
| Wrong adapter type | Set "Attached to" to "Internal Network", not NAT or Bridged |

---

## Analyzer Issues

### Problem: No packets captured by the analyzer

| Possible Cause | Solution |
|---|---|
| Wrong interface name in code | Run `ip a` and update the interface name in `analyzer.go` (line with `pcap.OpenLive`) |
| Analyzer not running as root | Run with `sudo ./analyzer` |
| Promiscuous mode not enabled | In VirtualBox, set Promiscuous Mode to "Allow All" for the network adapter |
| No traffic being generated | Verify the victim server is running and traffic scripts are executing |

### Problem: Analyzer build fails

| Possible Cause | Solution |
|---|---|
| Go not installed | Install Go: `sudo apt install golang -y` |
| gopacket dependency missing | Run `go get github.com/google/gopacket` |
| libpcap-dev not installed | Install: `sudo apt install libpcap-dev -y` |
| No internet for dependency download | Temporarily switch VM adapter to NAT mode, download dependencies, then switch back to Internal Network |
| Go module not initialized | Run `go mod init analyzer` before `go get` |

### Problem: "permission denied" when running analyzer

| Possible Cause | Solution |
|---|---|
| pcap requires root privileges | Always run the analyzer with `sudo`: `sudo ./analyzer` |

---

## Spoofing Script Issues

### Problem: Spoof script has no effect

| Possible Cause | Solution |
|---|---|
| Network is not Internal Network | Spoofed packets are dropped by NAT or Bridged networks. Ensure both VMs use Internal Network mode |
| Target IP is incorrect | Verify `target` variable in `spoof.py` matches the victim's IP (192.168.100.20) |
| Scapy not installed | Install: `pip3 install scapy` |
| Script not running as root | Scapy requires root for raw socket access: `sudo python3 spoof.py` |

### Problem: "Operation not permitted" when sending packets

| Possible Cause | Solution |
|---|---|
| Insufficient privileges | Run with `sudo` |
| Raw socket restricted | Ensure the user has permission to create raw sockets (root or CAP_NET_RAW capability) |

---

## Victim Server Issues

### Problem: Server does not start

| Possible Cause | Solution |
|---|---|
| Port 8080 already in use | Kill the existing process: `sudo lsof -i :8080` then `sudo kill <PID>` |
| Python 3 not available | Install: `sudo apt install python3 -y` |
| Socket permission error | Run with `sudo python3 server.py` |

### Problem: Server starts but no connections are logged

| Possible Cause | Solution |
|---|---|
| Client targeting wrong IP or port | Verify curl command uses `192.168.100.20:8080` |
| Network not connected | Re-check ping connectivity between VMs |
| Firewall blocking port 8080 | Disable UFW: `sudo ufw disable` or allow port: `sudo ufw allow 8080` |

---

## UDP Reflector Issues

### Problem: UDP reflector receives no packets

| Possible Cause | Solution |
|---|---|
| Reflector IP mismatch | Update `reflector_ip` in `reflect_udp.py` to match the VM running the reflector |
| Wrong port | Ensure the reflector binds to port 9999 and the attack script targets port 9999 |
| Reflector not running | Start the reflector before launching the reflection attack |

---

## tcpdump Issues

### Problem: tcpdump shows no output

| Possible Cause | Solution |
|---|---|
| Wrong interface specified | Use `ip a` to identify the correct interface and pass it with `-i` flag |
| No matching traffic | Adjust the filter (e.g., `tcp` vs `udp` vs no filter) |
| Not running as root | Run with `sudo tcpdump -i enp0s3` |

---

## General Verification Commands

| Command | Purpose |
|---|---|
| `ip a` | List network interfaces and IP addresses |
| `ping 192.168.100.20` | Test connectivity to victim |
| `sudo tcpdump -i enp0s3` | Capture all traffic on interface |
| `sudo tcpdump -i enp0s3 tcp` | Capture TCP traffic only |
| `sudo tcpdump -i enp0s3 udp` | Capture UDP traffic only |
| `sudo lsof -i :8080` | Check if port 8080 is in use |
| `go version` | Verify Go installation |
| `python3 --version` | Verify Python installation |
| `pip3 show scapy` | Verify Scapy installation |
