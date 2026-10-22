
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
MIN_CLIENTS = 2
MAX_TOTAL_SUM = 9000
DATA_COLLECTION_INTERVAL = 2 # Client sends data every 2 seconds
STATE_SWITCH_THRESHOLD = 100 # Switch state every 100 data points collected
SERVER_TCP_PORT = 12345
BROADCAST_UDP_PORT = 50000
BROADCAST_IP = '255.255.255.255' # Broadcast address

# Server State
class ServerState(Enum):
    STANDBY = "STANDBY"
    EVEN = "EVEN"
    ODD = "ODD"

total_sum = 0
current_state = ServerState.STANDBY
connected_clients = [] # List of (client_socket, client_address)
collected_data_count = 0
server_running = True
state_lock = threading.Lock() # To protect shared state variables

def broadcast_state():
    """Broadcasts the current server state to clients."""
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_socket.settimeout(0.2) # Small timeout for non-blocking send

    while server_running:
        with state_lock:
            message = f"STATE:{current_state.value}".encode('utf-8')
        try:
            broadcast_socket.sendto(message, (BROADCAST_IP, BROADCAST_UDP_PORT))
            # print(f"Broadcasted state: {current_state.value}") # For debugging
        except Exception as e:
            print(f"Error broadcasting state: {e}")
        time.sleep(1) # Broadcast every second
    # Tell clients that are not talking to us right now (STANDBY) that we are gone.
    # UDP may lose a datagram, so send it a few times.
    for _ in range(3):
        try:
            broadcast_socket.sendto(b"SERVER_STOPPED", (BROADCAST_IP, BROADCAST_UDP_PORT))
        except Exception:
            pass
        time.sleep(0.1)
    broadcast_socket.close()

def handle_client(client_socket, client_address):
    """Handles a single client connection."""
    global total_sum, collected_data_count, current_state, server_running

    print(f"Client {client_address} connected.")
    try:
        while server_running:
            data_len = int.from_bytes(recv_exact(client_socket, 4), 'big')  # raises ConnectionError on disconnect
            if data_len > 32:
                break # not our protocol
            received_value = int(recv_exact(client_socket, data_len).decode('utf-8'))

            with state_lock:
                if current_state == ServerState.STANDBY:
                    response = "Server in STANDBY. Waiting for more clients.".encode('utf-8')
                elif current_state == ServerState.EVEN and received_value % 2 == 0:
                    total_sum += received_value
                    collected_data_count += 1
                    response = f"ACK:{received_value}".encode('utf-8')
                    print(f"Received {received_value} (even) from {client_address}. Total sum: {total_sum}")
                elif current_state == ServerState.ODD and received_value % 2 != 0:
                    total_sum += received_value
                    collected_data_count += 1
                    response = f"ACK:{received_value}".encode('utf-8')
                    print(f"Received {received_value} (odd) from {client_address}. Total sum: {total_sum}")
                else:
                    response = "NACK:Invalid number type or state".encode('utf-8')
                    print(f"Rejected {received_value} from {client_address} (state: {current_state.value})")

                if total_sum > MAX_TOTAL_SUM:
                    server_running = False
                    response = "SERVER_STOPPED".encode('utf-8')

            client_socket.sendall(len(response).to_bytes(4, 'big') + response)
            if not server_running:
                break

    except (ConnectionError, ValueError, OSError) as e:
        print(f"Client {client_address}: {e}")
    finally:
        print(f"Client {client_address} disconnected.")
        with state_lock:
            # Remove client from connected_clients list
            for i, (sock, addr) in enumerate(connected_clients):
                if addr == client_address:
                    connected_clients.pop(i)
                    break
        client_socket.close()

def state_manager():
    """Manages the server's state transitions based on connected clients and collected data."""
    global current_state, collected_data_count, server_running

    while server_running:
        with state_lock:
            num_connected = len(connected_clients)
            if current_state == ServerState.STANDBY:
                if num_connected >= MIN_CLIENTS:
                    current_state = ServerState.EVEN # Start with EVEN
                    print(f"Server moved from STANDBY to {current_state.value}. Clients: {num_connected}")
            else: # Server is in EVEN or ODD state
                if num_connected < MIN_CLIENTS:
                    current_state = ServerState.STANDBY
                    print(f"Server moved to STANDBY. Not enough clients. Clients: {num_connected}")
                elif collected_data_count >= STATE_SWITCH_THRESHOLD:
                    current_state = ServerState.ODD if current_state == ServerState.EVEN else ServerState.EVEN
                    collected_data_count = 0 # Reset count after state switch
                    print(f"Server switched state to {current_state.value}")

            if total_sum > MAX_TOTAL_SUM:
                server_running = False
                print(f"Total sum ({total_sum}) exceeded {MAX_TOTAL_SUM}. Server stopping.")

        time.sleep(0.5) # Check state every half second

def main():
    global server_running

    # Setup TCP server for clients
    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_server_socket.bind(('', SERVER_TCP_PORT))
    tcp_server_socket.listen(5)
    print(f"TCP Server listening on port {SERVER_TCP_PORT}")

    # Start broadcast and state manager threads
    broadcaster = threading.Thread(target=broadcast_state, daemon=True)
    broadcaster.start()
    threading.Thread(target=state_manager, daemon=True).start()

    try:
        while server_running:
            try:
                tcp_server_socket.settimeout(1) # Accept with a timeout to check server_running flag
                client_socket, client_address = tcp_server_socket.accept()
                with state_lock:
                    connected_clients.append((client_socket, client_address))
                threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()
            except socket.timeout:
                continue # Just check server_running flag again
            except Exception as e:
                print(f"Error accepting client connection: {e}")
                if not server_running:
                    break
    except KeyboardInterrupt:
        print("Server shutting down due to KeyboardInterrupt.")
    finally:
        server_running = False
        broadcaster.join(timeout=2)  # let it send SERVER_STOPPED
        for sock, _ in connected_clients:
            sock.close()
        tcp_server_socket.close()
        print("Server stopped.")

if __name__ == "__main__":
    main()
