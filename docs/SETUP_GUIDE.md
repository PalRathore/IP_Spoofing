# Setup Guide

This document covers the complete environment setup required to run the IP spoofing simulation, including virtual machine creation, network configuration, and software installation.

---

## Prerequisites

| Requirement | Details |
|---|---|
| Host OS | Windows (tested) or any OS supporting VirtualBox |
| Virtualization | Oracle VirtualBox (latest stable version) |
| Guest OS | Ubuntu (Desktop or Server edition) |
| Disk space | Minimum 50 GB free (for two VMs) |
| RAM | Minimum 6 GB total (2 GB + 1.5 GB for VMs plus host overhead) |

---

## Step 1: Install VirtualBox

Download and install Oracle VirtualBox from the official site. No special configuration is needed. Default installation settings are sufficient.

---

## Step 2: Create Virtual Machines

### VM1 -- Attacker and Analyzer

| Setting | Value |
|---|---|
| Name | attacker |
| RAM | 2048 MB |
| CPU cores | 2 |
| Disk | 20 GB (dynamically allocated) |
| OS | Ubuntu |

This VM runs the spoofing scripts (`spoof.py`, `reflect_udp.py`) and the packet analyzer (`analyzer.go`).

### VM2 -- Victim

| Setting | Value |
|---|---|
| Name | victim |
| RAM | 1536 MB |
| CPU cores | 1 |
| Disk | 20 GB (dynamically allocated) |
| OS | Ubuntu |

This VM runs the victim services (`server.py`, `udp_reflector.py`).

Install Ubuntu on both VMs using the standard installation process.

---

## Step 3: Configure VirtualBox Networking

For each VM, configure the network adapter as follows:

1. Open VM Settings in VirtualBox
2. Navigate to **Network** > **Adapter 1**
3. Set **Attached to:** `Internal Network`
4. Set **Name:** `labnet`
5. Expand **Advanced** and set **Promiscuous Mode:** `Allow All`

Both VMs must use the same internal network name (`labnet`). This creates an isolated Layer 2 segment with no external connectivity.

**Why Internal Network:** Internal networking ensures complete isolation from the host machine and the internet. No traffic leaves the virtual environment, which is essential for safe attack simulation.

**Why Promiscuous Mode:** The analyzer needs to capture all packets on the interface, including those not addressed to its own MAC address. Promiscuous mode enables this.

---

## Step 4: Install System Dependencies

Run the following commands on **both** VMs after booting Ubuntu:

```bash
sudo apt update
sudo apt upgrade -y
```

### On VM1 (Attacker + Analyzer)

```bash
sudo apt install python3-pip tcpdump golang -y
pip3 install scapy
```

Go is required for building the analyzer. Scapy is required for the spoofing scripts. tcpdump is used for manual packet verification.

### On VM2 (Victim)

```bash
sudo apt install python3 tcpdump -y
```

The victim only needs Python 3 (which is typically pre-installed on Ubuntu) and tcpdump for verification.

---

## Step 5: Identify the Network Interface

On each VM, run:

```bash
ip a
```

Identify the interface connected to the internal network. It is typically named `enp0s3`. Confirm that the interface is in the `UP` state. If it shows `DOWN`, bring it up:

```bash
sudo ip link set enp0s3 up
```

---

## Step 6: Configure Static IP Addresses

Edit the Netplan configuration file on each VM:

```bash
sudo nano /etc/netplan/01-netcfg.yaml
```

### VM1 (Attacker) -- 192.168.100.10

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: no
      addresses: [192.168.100.10/24]
```

### VM2 (Victim) -- 192.168.100.20

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: no
      addresses: [192.168.100.20/24]
```

Apply the configuration on each VM:

```bash
sudo netplan apply
```

**Note:** Replace `enp0s3` with the actual interface name identified in Step 5 if it differs.

---

## Step 7: Verify Connectivity

From VM1 (Attacker):

```bash
ping 192.168.100.20
```

From VM2 (Victim):

```bash
ping 192.168.100.10
```

Both pings must succeed before proceeding. If they fail:

- Verify that both VMs are using the same internal network name (`labnet`)
- Confirm that Netplan configuration has been applied (`sudo netplan apply`)
- Check that the interface is UP (`ip a`)
- Ensure the subnet mask is /24 on both sides

---

## Step 8: Transfer Project Files

Copy the project files to the appropriate VM. The recommended directory structure on VM1:

```
~/analyzer/
    analyzer.go

~/analyzer/simulator/
    spoof.py
    reflect_udp.py
```

On VM2:

```
~/victim/
    server.py
    udp_reflector.py
```

Files can be transferred via shared folders in VirtualBox or by cloning the repository on each VM if Git is installed.

---

## Step 9: Build the Analyzer

On VM1, navigate to the analyzer directory and build:

```bash
cd ~/analyzer
go mod init analyzer
go get github.com/google/gopacket
go build
```

This produces an executable named `analyzer` in the current directory. The build requires internet access on VM1, which means temporarily switching the network adapter to NAT mode, building, then switching back to Internal Network mode.

Alternatively, build the analyzer before configuring the internal network, or use a second network adapter (Adapter 2) set to NAT for package downloads.

---

## Environment Summary

| VM | IP Address | Role | Services |
|---|---|---|---|
| VM1 | 192.168.100.10 | Attacker + Analyzer | spoof.py, reflect_udp.py, analyzer |
| VM2 | 192.168.100.20 | Victim | server.py, udp_reflector.py |

| Network Setting | Value |
|---|---|
| Type | Internal Network |
| Name | labnet |
| Subnet | 192.168.100.0/24 |
| Promiscuous Mode | Allow All |
| Internet Access | None (isolated) |
