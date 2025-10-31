
import socket
import sys

def main():
    if len(sys.argv) < 3:
        print("Usage: python bcast-client.py <broadcast_ip> <port>")
        return

    broadcast_ip = sys.argv[1]
    try:
        port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        return

    socket_fd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_fd.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    message = input("Enter a string (max 100 characters): ")
    if len(message) > 100:
        message = message[:100]

    len_bytes = len(message).to_bytes(4, 'big')
    socket_fd.sendto(len_bytes, (broadcast_ip, port))
    print(f"Sent {len(len_bytes)} bytes to the server")

    socket_fd.sendto(message.encode('utf-8'), (broadcast_ip, port))
    print(f"Sent {len(message)} bytes to the server")

    socket_fd.close()

if __name__ == "__main__":
    main()
