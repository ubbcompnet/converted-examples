"""udp/string - broadcast client: SO_BROADCAST lets it send to e.g. 255.255.255.255.
Usage: python bcast-client.py <broadcast_ip> <port>"""
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


MAX_MSG = 1400  # stay below the Ethernet MTU: no IP fragmentation


def main():
    if len(sys.argv) < 3:
        print("Usage: python bcast-client.py <ip> <port>")
        return
    port = parse_port(sys.argv[2])
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    data = input("Enter a string: ").encode("utf-8")
    if len(data) > MAX_MSG:
        print(f"Message too long, truncated to {MAX_MSG} bytes")
        data = data[:MAX_MSG]
    s.sendto(data, (sys.argv[1], port))
    print(f"Sent {len(data)} bytes")
    s.close()


if __name__ == "__main__":
    main()
