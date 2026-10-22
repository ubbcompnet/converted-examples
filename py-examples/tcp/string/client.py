"""tcp/string - client. Usage: python client.py <host> <port>"""
import struct
import socket
import sys


def send_msg(sock, text):
    data = text.encode("utf-8")  # encode first: the length must count bytes, not characters
    sock.sendall(struct.pack("!I", len(data)) + data)


def parse_port(text):
    try:
        port = int(text)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise SystemExit("Port must be an integer between 1 and 65535.")
    return port


def main():
    if len(sys.argv) < 3:
        print("Usage: python client.py <host> <port>")
        return
    port = parse_port(sys.argv[2])
    message = input("Enter a string: ")
    try:
        with socket.create_connection((sys.argv[1], port)) as s:
            send_msg(s, message)
            print(f"Sent {len(message.encode('utf-8'))} bytes to the server")
    except OSError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
