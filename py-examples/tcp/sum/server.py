
import socket
import sys
import threading

def handle_client(client_socket, client_address):
    print(f"New client connected: {client_address}")
    try:
        a_bytes = client_socket.recv(4)
        if not a_bytes:
            print(f"Client {client_address} disconnected.")
            return
        a = int.from_bytes(a_bytes, 'big')
        print(f"Received from client {client_address} - {a}")

        b_bytes = client_socket.recv(4)
        if not b_bytes:
            print(f"Client {client_address} disconnected.")
            return
        b = int.from_bytes(b_bytes, 'big')
        print(f"Received from client {client_address} - {b}")

        sum_val = a + b
        print(f"Sending to {client_address} - {sum_val}")
        client_socket.send(sum_val.to_bytes(4, 'big'))
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {client_address} closed.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Port must be an integer.")
        return

    server_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_fd.bind(("", port))
    server_fd.listen(5)
    print(f"Server listening on port {port}")

    while True:
        client, addr = server_fd.accept()
        client_handler = threading.Thread(target=handle_client, args=(client, addr))
        client_handler.start()

if __name__ == "__main__":
    main()
