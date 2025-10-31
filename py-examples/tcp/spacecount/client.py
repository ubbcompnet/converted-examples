
import socket
import sys

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

    try:
        socket_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_fd.connect((server_ip, port))
        print(f"Connected to server {server_ip}:{port}")

        message = input("Enter a string (max 100 characters): ")
        if len(message) > 100:
            message = message[:100]

        len_bytes = len(message).to_bytes(4, 'big')
        socket_fd.send(len_bytes)
        print(f"Sent {len(len_bytes)} bytes to the server")

        socket_fd.sendall(message.encode('utf-8'))
        print(f"Sent {len(message)} bytes to the server")

        count_bytes = socket_fd.recv(4)
        count = int.from_bytes(count_bytes, 'big')
        print(f"Received from server: {count}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        socket_fd.close()

if __name__ == "__main__":
    main()
