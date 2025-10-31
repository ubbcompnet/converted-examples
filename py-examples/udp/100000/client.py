
import socket
import sys
import time

def main():
    if len(sys.argv) < 3:
        print("Usage: python client.py <server_ip> <port>")
        return

    server_ip = sys.argv[1]
    try:
        port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        return

    socket_fd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for i in range(10000):
        num_bytes = i.to_bytes(4, 'big')
        socket_fd.sendto(num_bytes, (server_ip, port))
        print(f"Sent {i} to the server")
        time.sleep(0.001) # Small delay to avoid overwhelming the server

    socket_fd.close()

if __name__ == "__main__":
    main()
