import socket
import sys


server_address = ('127.0.0.1', 1276)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind(server_address)

s.listen(5)

while True:
    
    print ('Waiting for clients:')
    
    conection, client_address = s.accept()
    
    data = conection.recv(4)
    
    data2 = int.from_bytes(data,'big')
    
    str = conection.recv(data2).decode("utf-8")
    
    print (str)
        
    str=str[::-1]
    
    conection.send(str.encode())
    


    