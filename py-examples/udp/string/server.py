"""udp/string - server. One datagram = one message (UDP keeps message boundaries).
Usage: python server.py <port>"""
import socket
import sys


def parse_port(text):
    try:
        port = int(text)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise SystemExit("Port must be an integer between 1 and 65535.")
    return port


def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", parse_port(sys.argv[1])))
    print(f"udp server listening on port {s.getsockname()[1]}")
    while True:
        data, addr = s.recvfrom(2048)  # a longer datagram would be silently truncated
        print(f"{addr[0]}:{addr[1]} ({len(data)} bytes): {data.decode('utf-8', errors='replace')}")


if __name__ == "__main__":
    main()
