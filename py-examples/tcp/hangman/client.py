
import socket
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

    try:
        socket_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_fd.connect((server_ip, port))
        print(f"Connected to server {server_ip}:{port}")

        word_len_bytes = socket_fd.recv(4)
        word_len = int.from_bytes(word_len_bytes, 'big')
        guessed_word = ['_'] * word_len
        print(f"Word length: {word_len}")
        print(" ".join(guessed_word))

        while True:
            letter = input("Guess a letter: ")[0]
            socket_fd.send(letter.encode('utf-8'))

            response_code_bytes = socket_fd.recv(4)
            response_code = int.from_bytes(response_code_bytes, 'big')

            if response_code == 1: # Found letter
                count_bytes = socket_fd.recv(4)
                count = int.from_bytes(count_bytes, 'big')
                for _ in range(count):
                    index_bytes = socket_fd.recv(4)
                    index = int.from_bytes(index_bytes, 'big')
                    guessed_word[index] = letter
                print(" ".join(guessed_word))
            elif response_code == 0: # Wrong letter
                print("Wrong guess!")
            elif response_code == 2: # Win
                print("You won!")
                break
            elif response_code == 3: # Lose
                print("You lost!")
                break

    except Exception as e:
        print(f"Error: {e}")
    finally:
        socket_fd.close()

if __name__ == "__main__":
    main()
