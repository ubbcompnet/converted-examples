"""udp/100000 - server: counts how many of the COUNT numbered datagrams arrive and whether
they arrive in order. A round ends after COUNT datagrams or 2 s of silence.
Datagram = u32 sequence number, big-endian. Usage: python server.py <port>"""
import socket
import struct
import sys


def parse_port(text):
    try:
        port = int(text)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise SystemExit("Port must be an integer between 1 and 65535.")
    return port


COUNT = 100000


def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", parse_port(sys.argv[1])))
    print(f"waiting for {COUNT} numbered datagrams on port {s.getsockname()[1]}")

    while True:
        s.settimeout(None)  # wait forever for the first datagram
        received = jumps = expected = 0
        while received < COUNT:
            try:
                data, _ = s.recvfrom(64)
            except socket.timeout:
                break
            if len(data) != 4:
                continue
            if received == 0:
                s.settimeout(2.0)
            (num,) = struct.unpack("!I", data)
            if num != expected:
                if jumps < 5:
                    print(f"unexpected number: wanted {expected}, got {num}")
                jumps += 1
            expected = num + 1
            received += 1
        print(f"round finished: received {received} of {COUNT} (lost {COUNT - received}), "
              f"{jumps} out-of-sequence")


if __name__ == "__main__":
    main()
