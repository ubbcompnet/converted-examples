
import socket
import select
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        return

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Port must be an integer.")
        return

    server_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_fd.setblocking(False)
    server_fd.bind(("", port))
    server_fd.listen(5)

    inputs = [server_fd]
    client_count = 0

    print(f"Server listening on port {port}")

    while inputs:
        readable, _, _ = select.select(inputs, [], [])

        for s in readable:
            if s is server_fd:
                conn, addr = s.accept()
                print(f"New client connected: {addr}")
                conn.setblocking(False)
                inputs.append(conn)
                client_count += 1
                conn.send(f"Welcome to the server! You are client {client_count}".encode('utf-8'))
            else:
                try:
                    data = s.recv(1024)
                    if data:
                        message = f"Client {inputs.index(s)} says: {data.decode('utf-8').strip()}"
                        print(message)
                        for client in inputs:
                            if client != server_fd and client != s:
                                try:
                                    client.send(message.encode('utf-8'))
                                except Exception as e:
                                    print(f"Error sending to client: {e}")
                    else:
                        print(f"Client {inputs.index(s)} hung up.")
                        inputs.remove(s)
                        s.close()
                except ConnectionResetError:
                    print(f"Client {inputs.index(s)} reset the connection.")
                    inputs.remove(s)
                    s.close()

if __name__ == "__main__":
    main()
