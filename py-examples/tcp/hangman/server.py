
import socket
import sys
import threading
import random

WORDS = ["dimethyltryptamine", "failure", "methanol", "interdisciplinarity", "depresion", "phenylpropanolamine"]

def handle_client(client_socket, client_address):
    print(f"New client connected: {client_address}")
    try:
        word = random.choice(WORDS)
        chances = random.randint(5, 8)
        guessed_word = ['_'] * len(word)
        remaining_letters = len(word)

        print(f"Client {client_address} has to guess word: {word} in {chances} shots")

        client_socket.send(len(word).to_bytes(4, 'big'))
        print(f"Sent to client {client_address} word length: {len(word)}")

        while chances > 0 and remaining_letters > 0:
            letter_byte = client_socket.recv(1)
            if not letter_byte:
                print(f"Client {client_address} disconnected.")
                return
            
            letter = letter_byte.decode('utf-8')
            print(f"{client_address}: {letter}")

            if letter in word:
                indices = [i for i, l in enumerate(word) if l == letter]
                for i in indices:
                    if guessed_word[i] == '_':
                        guessed_word[i] = letter
                        remaining_letters -= 1
                
                client_socket.send((1).to_bytes(4, 'big')) # Found letter
                client_socket.send(len(indices).to_bytes(4, 'big'))
                for i in indices:
                    client_socket.send(i.to_bytes(4, 'big'))
            else:
                chances -= 1
                client_socket.send((0).to_bytes(4, 'big')) # Wrong letter

        if remaining_letters == 0:
            client_socket.send((2).to_bytes(4, 'big')) # Win
            print(f"Client {client_address} won.")
        else:
            client_socket.send((3).to_bytes(4, 'big')) # Lose
            print(f"Client {client_address} lost.")

    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {client_address} closed.")

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
    server_fd.bind(("", port))
    server_fd.listen(5)
    print(f"Server listening on port {port}")

    while True:
        client, addr = server_fd.accept()
        client_handler = threading.Thread(target=handle_client, args=(client, addr))
        client_handler.start()

if __name__ == "__main__":
    main()
