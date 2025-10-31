
import socket
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Port must be an integer.")
        return

    server_fd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_fd.bind(("", port))

    print(f"Server listening on port {port}")

    prev = -1
    while True:
        data, addr = server_fd.recvfrom(4)
        num = int.from_bytes(data, 'big')

        if num != prev + 1:
            print(f"Wrong order! Expecting {prev + 1}, got {num}")
        
        prev = num
        print(f"Received from {addr}: {num}")

if __name__ == "__main__":
    main()
