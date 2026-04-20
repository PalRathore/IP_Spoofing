import socket

HOST = "0.0.0.0"
PORT = 8080

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

print("Server running...")

while True:
    conn, addr = s.accept()
    print("Connection from:", addr)
    conn.close()
