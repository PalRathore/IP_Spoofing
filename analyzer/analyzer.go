package main

import (
	"fmt"
	"log"

	"github.com/google/gopacket"
	"github.com/google/gopacket/layers"
	"github.com/google/gopacket/pcap"
)

func main() {
	handle, err := pcap.OpenLive("enp0s3", 1600, true, pcap.BlockForever)
	if err != nil {
		log.Fatal(err)
	}

	packetSource := gopacket.NewPacketSource(handle, handle.LinkType())

	synCount := 0
	ackCount := 0

	for packet := range packetSource.Packets() {
		if tcpLayer := packet.Layer(layers.LayerTypeTCP); tcpLayer != nil {
			tcp := tcpLayer.(*layers.TCP)

			if tcp.SYN && !tcp.ACK {
				synCount++
			}

			if tcp.ACK {
				ackCount++
			}

			if (synCount+ackCount)%50 == 0 {
				fmt.Printf("SYN: %d | ACK: %d\n", synCount, ackCount)
			}
		}
	}
}
