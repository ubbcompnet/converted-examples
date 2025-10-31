
import socket
import select
import sys

def main():
    if len(sys.argv) < 3:
        print("Usage: python client.py <server_ip> <port>")
        return

    server_ip = sys.argv[1]
    try:
        port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        return

    socket_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        socket_fd.connect((server_ip, port))
    except Exception as e:
        print(f"Connection error: {e}")
        return

    print(f"Connected to server {server_ip}:{port}")

    # Receive welcome message
    welcome_msg = socket_fd.recv(1024).decode('utf-8')
    print(welcome_msg)

    inputs = [sys.stdin, socket_fd]

    while True:
        readable, _, _ = select.select(inputs, [], [])

        for s in readable:
            if s == socket_fd:
                # Message from server
                data = s.recv(1024)
                if not data:
                    print("Server has closed connection...")
                    return
                sys.stdout.write(data.decode('utf-8') + '\n')
                sys.stdout.flush()
            else:
                # Input from user
                msg = sys.stdin.readline()
                socket_fd.send(msg.encode('utf-8'))

if __name__ == "__main__":
    main()
