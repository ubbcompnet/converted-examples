"""tcp/sum - client. Usage: python client.py <host> <port>"""
import socket
import struct
import sys


# ---- helpers: TCP is a byte stream, so every read goes through recv_exact() ----
def recv_exact(sock, n):
    """Read exactly n bytes; raise ConnectionError if the peer closes early."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed the connection")
        buf += chunk
    return bytes(buf)


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
    try:
        a = int(input("Give a number: "))
        b = int(input("Give a number: "))
        if not (-2**31 <= a < 2**31 and -2**31 <= b < 2**31):
            print("Numbers must fit in 32 bits (signed).")
            return
    except ValueError:
        print("Please enter integers.")
        return
    try:
        with socket.create_connection((sys.argv[1], port)) as s:
            s.sendall(struct.pack("!ii", a, b))
            (total,) = struct.unpack("!q", recv_exact(s, 8))
            print(f"Received from the server: {total}")
    except (ConnectionError, OSError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
