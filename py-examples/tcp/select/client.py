"""tcp/select - chat client: select() on the keyboard and the socket.
(select on sys.stdin works on Unix/macOS, not on Windows.)
Usage: python client.py <server_ip> <port>"""
import select
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
    if len(sys.argv) < 3:
        print("Usage: python client.py <server_ip> <port>")
        return
    port = parse_port(sys.argv[2])
    try:
        sock = socket.create_connection((sys.argv[1], port))
    except OSError as e:
        print(f"Connection error: {e}")
        return

    with sock:
        while True:
            readable, _, _ = select.select([sys.stdin, sock], [], [])
            for s in readable:
                if s is sock:
                    data = sock.recv(1024)
                    if not data:
                        print("Server has closed the connection...")
                        return
                    sys.stdout.write(data.decode("utf-8", errors="replace"))
                    sys.stdout.flush()
                else:
                    line = sys.stdin.readline()
                    if not line:  # Ctrl-D
                        return
                    sock.sendall(line.encode("utf-8"))


if __name__ == "__main__":
    main()
