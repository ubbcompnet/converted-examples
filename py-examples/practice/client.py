
import random
import socket
import sys
import threading
import time
from enum import Enum


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


# Configuration
SERVER_IP = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'  # usage: python client.py [server_ip]
SERVER_TCP_PORT = 12345
BROADCAST_UDP_PORT = 50000
DATA_SEND_INTERVAL = 2 # Send data every 2 seconds

# Server State
class ServerState(Enum):
    STANDBY = "STANDBY"
    EVEN = "EVEN"
    ODD = "ODD"

current_server_state = ServerState.STANDBY
client_running = True

# Client's numbers
client_even_number = random.randint(1, 4) * 2 # Even number between 2 and 8
client_odd_number = random.randint(1, 5) * 2 - 1 # Odd number between 1 and 9

def listen_for_broadcasts():
    """Listens for UDP broadcast messages from the server to get its state."""
    global current_server_state, client_running
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('', BROADCAST_UDP_PORT))

    print(f"Listening for server broadcasts on port {BROADCAST_UDP_PORT}")

    while client_running:
        try:
            data, addr = listen_socket.recvfrom(1024)
            message = data.decode('utf-8')
            if message.startswith("STATE:"):
                state_str = message.split(":")[1]
                try:
                    current_server_state = ServerState(state_str)
                    # print(f"Server state updated to: {current_server_state.value}") # For debugging
                except ValueError:
                    print(f"Received unknown state: {state_str}")
            elif message == "SERVER_STOPPED":
                print("Server has stopped. Client shutting down.")
                client_running = False
                break
        except socket.timeout:
            pass # Continue listening
        except Exception as e:
            print(f"Error listening for broadcasts: {e}")
    listen_socket.close()

def send_data_to_server():
    """Connects to the TCP server and sends data based on server's state."""
    global client_running, current_server_state
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_socket.connect((SERVER_IP, SERVER_TCP_PORT))
        print(f"Connected to server at {SERVER_IP}:{SERVER_TCP_PORT}")

        while client_running:
            data_to_send = None
            if current_server_state == ServerState.EVEN:
                data_to_send = client_even_number
                print(f"Server requesting EVEN. Sending: {data_to_send}")
            elif current_server_state == ServerState.ODD:
                data_to_send = client_odd_number
                print(f"Server requesting ODD. Sending: {data_to_send}")
            else: # STANDBY
                print("Server in STANDBY. Waiting for active state.")

            if data_to_send is not None:
                message = str(data_to_send).encode('utf-8')
                tcp_socket.sendall(len(message).to_bytes(4, 'big') + message)

                # Receive response from server
                try:
                    response_len = int.from_bytes(recv_exact(tcp_socket, 4), 'big')
                    response = recv_exact(tcp_socket, response_len).decode('utf-8')
                except ConnectionError:
                    print("Server disconnected.")
                    break
                print(f"Server response: {response}")

                if response == "SERVER_STOPPED":
                    print("Server has stopped. Client shutting down.")
                    client_running = False
                    break

            time.sleep(DATA_SEND_INTERVAL)

    except ConnectionRefusedError:
        print(f"Connection to server {SERVER_IP}:{SERVER_TCP_PORT} refused. Is the server running?")
    except Exception as e:
        print(f"Error sending data to server: {e}")
    finally:
        tcp_socket.close()
        print("Client disconnected from server.")
        client_running = False

def main():
    global client_running
    print(f"Client initialized with Even: {client_even_number}, Odd: {client_odd_number}")

    # Start threads
    broadcast_thread = threading.Thread(target=listen_for_broadcasts, daemon=True)
    data_send_thread = threading.Thread(target=send_data_to_server, daemon=True)

    broadcast_thread.start()
    data_send_thread.start()

    try:
        while client_running:
            time.sleep(1) # Keep main thread alive
    except KeyboardInterrupt:
        print("Client shutting down due to KeyboardInterrupt.")
    finally:
        client_running = False
        print("Client-side stopped.")

if __name__ == "__main__":
    main()
