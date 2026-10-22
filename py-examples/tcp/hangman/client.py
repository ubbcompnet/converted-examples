"""tcp/hangman - client (works with the Python and the C server).
Usage: python client.py <server_ip> <port>"""
import struct
import socket
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


def recv_u32(sock):
    return struct.unpack("!I", recv_exact(sock, 4))[0]


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
        print("Usage: python client.py <server_ip> <port>")
        return
    port = parse_port(sys.argv[2])
    try:
        with socket.create_connection((sys.argv[1], port)) as s:
            word_len = recv_u32(s)
            guessed = ["_"] * word_len
            print(f"Word length: {word_len}")
            print(" ".join(guessed))

            while True:
                letter = input("Guess a letter: ").strip().lower()
                if len(letter) != 1 or not letter.isascii() or not letter.isalpha():
                    print("Enter exactly one letter a-z.")
                    continue
                s.sendall(letter.encode("ascii"))

                code = recv_u32(s)
                if code == 1:  # found
                    for _ in range(recv_u32(s)):
                        guessed[recv_u32(s)] = letter
                    print(" ".join(guessed))
                    if "_" not in guessed:  # the server now sends the final code
                        code = recv_u32(s)
                if code == 0:
                    print("Wrong guess!")
                elif code == 2:
                    print("You won!")
                    break
                elif code == 3:
                    print("You lost!")
                    break
    except (ConnectionError, OSError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
