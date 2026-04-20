import socket

HOST = "0.0.0.0"
PORT = 9999

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

print("UDP reflector running...")

while True:
    data, addr = sock.recvfrom(1024)
    print("Received from:", addr)
    sock.sendto(data, addr)
