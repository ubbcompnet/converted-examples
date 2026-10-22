"""tcp/sum - server (thread per client).
client -> server : a, b  (two signed 32-bit ints, big-endian)
server -> client : a + b (signed 64-bit, big-endian)
Usage: python server.py <port>"""
import socket
import sys
import threading

import struct


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


def make_listener(port, host=""):
    """TCP listening socket with SO_REUSEADDR (restart without 'Address already in use')."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(16)
    return s


def parse_port(text):
    try:
        port = int(text)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise SystemExit("Port must be an integer between 1 and 65535.")
    return port


def handle_client(conn, addr):
    print(f"New client connected: {addr}")
    try:
        with conn:
            a, b = struct.unpack("!ii", recv_exact(conn, 8))
            print(f"{addr}: {a} + {b} = {a + b}")
            conn.sendall(struct.pack("!q", a + b))
    except (ConnectionError, OSError) as e:
        print(f"Client {addr}: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return
    srv = make_listener(parse_port(sys.argv[1]))
    print(f"sum server listening on port {srv.getsockname()[1]}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
