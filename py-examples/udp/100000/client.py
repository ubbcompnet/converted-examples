"""udp/100000 - client: sends COUNT datagrams, each holding its sequence number (big-endian u32).
Optional 3rd argument: delay in seconds between datagrams (e.g. 0.0001 to avoid loss).
Usage: python client.py <server_ip> <port> [delay]"""
import socket
import struct
import sys
import time


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
    if len(sys.argv) < 3:
        print("Usage: python client.py <server_ip> <port> [delay]")
        return
    port = parse_port(sys.argv[2])
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(COUNT):
        s.sendto(struct.pack("!I", i), (sys.argv[1], port))
        if i % 10000 == 0:
            print(f"sent {i}")
        if delay:
            time.sleep(delay)
    print("done")
    s.close()


if __name__ == "__main__":
    main()
