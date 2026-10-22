"""tcp/select - chat server: ONE thread, select() multiplexes all clients.
Every line a client sends is forwarded to the others. Messages are text lines ending in '\n'.
Usage: python server.py <port>"""
import socket
import select
import sys


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


def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return
    server = make_listener(parse_port(sys.argv[1]))
    print(f"chat server listening on port {server.getsockname()[1]}")

    ids = {}  # socket -> client number (stays stable when other clients leave)
    next_id = 0
    inputs = [server]

    while True:
        readable, _, _ = select.select(inputs, [], [])
        for s in readable:
            if s is server:
                conn, addr = server.accept()
                next_id += 1
                ids[conn] = next_id
                inputs.append(conn)
                print(f"client {next_id} connected from {addr}")
                conn.sendall(f"Welcome to the server! You are client {next_id}\n".encode())
                continue

            try:
                data = s.recv(1024)
            except OSError:
                data = b""
            if not data:
                print(f"client {ids[s]} hung up")
                inputs.remove(s)
                del ids[s]
                s.close()
                continue

            message = f"Client {ids[s]} says: ".encode() + data
            if not message.endswith(b"\n"):
                message += b"\n"
            print(message.decode("utf-8", errors="replace"), end="")
            for other in inputs[1:]:
                if other is not s:
                    try:
                        other.sendall(message)
                    except OSError as e:
                        print(f"Error sending to client {ids[other]}: {e}")


if __name__ == "__main__":
    main()
