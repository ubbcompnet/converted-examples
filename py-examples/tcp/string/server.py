import socket
import sys
import threading


def handle_client(client_socket, client_address):
    print(f"New client connected: {client_address}")
    try:
        len_bytes = client_socket.recv(4)
        if not len_bytes:
            print(f"Client {client_address} disconnected.")
            return
        str_len = int.from_bytes(len_bytes, "big")
        print(f"Received from client {client_address} - length: {str_len}")

        str_data = client_socket.recv(str_len)
        if not str_data:
            print(f"Client {client_address} disconnected.")
            return
        received_string = str_data.decode("utf-8")
        print(f"""Received from {client_address}: {received_string}""")

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
