"""tcp/reversestring - client. Usage: python client.py <host> <port>"""
import struct
import socket
import sys


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


def send_msg(sock, text):
    data = text.encode("utf-8")  # encode first: the length must count bytes, not characters
    sock.sendall(struct.pack("!I", len(data)) + data)


def recv_msg(sock, max_len=MAX_STR):
    n = recv_u32(sock)
    if n > max_len:
        raise ValueError(f"message too long: {n}")
    return recv_exact(sock, n).decode("utf-8", errors="replace")


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
            print(f"Reversed: {recv_msg(s)}")
    except (ConnectionError, OSError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
