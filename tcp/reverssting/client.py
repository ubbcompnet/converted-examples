import socket
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_address = ('127.0.0.1', 1276)

msg = input("Msg:")

l = socket.htons(len(msg))

s.connect(server_address)

s.send(str(l).encode())

s.send(msg.encode())

rev = s.recv(len(msg)).decode("utf-8")

print (rev)

