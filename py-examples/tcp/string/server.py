"""tcp/string - server (thread per client).
client -> server : a string (u32 length in BYTES + UTF-8 bytes); the server prints it.
Usage: python server.py <port>"""
import socket
import struct
import sys
import threading


MAX_STR = 1 << 20  # largest string accepted from the network


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


def recv_u32(sock):
    return struct.unpack("!I", recv_exact(sock, 4))[0]


def recv_msg(sock, max_len=MAX_STR):
    n = recv_u32(sock)
    if n > max_len:
        raise ValueError(f"message too long: {n}")
    return recv_exact(sock, n).decode("utf-8", errors="replace")


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
            print(f"Received from {addr}: {recv_msg(conn)}")
    except (ConnectionError, ValueError, OSError) as e:
        print(f"Client {addr}: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return
    srv = make_listener(parse_port(sys.argv[1]))
    print(f"string server listening on port {srv.getsockname()[1]}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
