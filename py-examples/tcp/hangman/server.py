"""tcp/hangman - server (thread per client). Same protocol as the C server.

server -> client : word length (u32)
then repeat:
  client -> server : one ASCII letter (1 byte)
  server -> client : code (u32)
      1 = found: count (u32) + count x index (u32); if that completed the word, 2 follows
      0 = wrong letter        2 = you won        3 = you lost (no chances left)
Usage: python server.py <port>"""
import socket
import random
import struct
import sys
import threading


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


def send_u32(sock, value):
    sock.sendall(struct.pack("!I", value))


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


WORDS = ["dimethyltryptamine", "failure", "methanol", "interdisciplinarity",
         "depression", "phenylpropanolamine"]


def handle_client(conn, addr):
    print(f"New client connected: {addr}")
    try:
        with conn:
            word = random.choice(WORDS)
            chances = random.randint(5, 8)
            revealed = [False] * len(word)
            print(f"Client {addr} has to guess '{word}' with {chances} wrong shots")
            send_u32(conn, len(word))

            while True:
                letter = recv_exact(conn, 1).decode("ascii", errors="replace")
                indices = [i for i, ch in enumerate(word) if ch == letter]
                if indices:
                    for i in indices:
                        revealed[i] = True
                    conn.sendall(struct.pack(f"!II{len(indices)}I", 1, len(indices), *indices))
                    if all(revealed):
                        send_u32(conn, 2)
                        print(f"Client {addr} won")
                        return
                else:
                    chances -= 1
                    if chances == 0:
                        send_u32(conn, 3)
                        print(f"Client {addr} lost")
                        return
                    send_u32(conn, 0)
    except (ConnectionError, OSError) as e:
        print(f"Client {addr}: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return
    srv = make_listener(parse_port(sys.argv[1]))
    print(f"hangman server listening on port {srv.getsockname()[1]}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
