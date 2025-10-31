import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_address = ("127.0.0.1", 1276)

msg = input("Msg:")

l = len(msg)

s.connect(server_address)

print(s.send(l.to_bytes(4, byteorder="big")))

s.send(msg.encode())

rev = s.recv(4)

count = socket.ntohl(int.from_bytes(rev, "big"))

print(rev)
