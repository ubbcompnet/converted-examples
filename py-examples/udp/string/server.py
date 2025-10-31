
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

    while True:
        data, addr = server_fd.recvfrom(1024)
        str_len = int.from_bytes(data, 'big')
        print(f"Received from {addr} - length: {str_len}")

        data, addr = server_fd.recvfrom(str_len)
        message = data.decode('utf-8')
        print(f"""Received from {addr}:
{message}
""")

if __name__ == "__main__":
    main()
