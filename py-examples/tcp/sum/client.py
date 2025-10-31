
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

        a = int(input("Give a number: "))
        socket_fd.send(a.to_bytes(4, 'big'))
        print(f"Sent {a} to the server")

        b = int(input("Give a number: "))
        socket_fd.send(b.to_bytes(4, 'big'))
        print(f"Sent {b} to the server")

        sum_bytes = socket_fd.recv(4)
        sum_val = int.from_bytes(sum_bytes, 'big')
        print(f"Received from the server: {sum_val}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        socket_fd.close()

if __name__ == "__main__":
    main()
