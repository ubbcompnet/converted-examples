
# C and Python Socket Programming Examples

This repository contains a collection of client-server examples written in both C and Python, demonstrating various networking concepts.

## C Examples

The `c/` directory contains the original set of examples written in C. These examples cover fundamental socket programming concepts, including:

*   **TCP (Transmission Control Protocol):**
    *   `tcp/sum/`: A simple client-server application where the client sends two numbers to the server, and the server returns their sum.
    *   `tcp/string/`: A client sends a string to the server, and the server sends it back, possibly modified.
    *   `tcp/hangman/`: A more complex example implementing the game of Hangman over a network.
    *   `tcp/select/`: Demonstrates using the `select()` system call for handling multiple clients concurrently.
*   **UDP (User Datagram Protocol):**
    *   `udp/string/`: A simple client-server application for sending and receiving strings using UDP.
    *   `udp/100000/`: An example designed to handle a large number of messages.

## Python Examples

The `py-examples/` directory contains Python implementations of the same networking concepts, often with a more modern and simplified approach.

*   **`tcp/` and `udp/` subdirectories:** These mirror the structure of the C examples, providing Python versions of the same client-server interactions.
*   **`practice/`:** A custom client-server application with the following logic:
    *   **Server (`server.py`):**
        *   Waits for a minimum of 2 clients to connect before starting.
        *   Broadcasts its current state (`STANDBY`, `EVEN`, `ODD`) to the network using UDP.
        *   Initially, it requests even numbers. After receiving 100 numbers, it switches to requesting odd numbers, and so on.
        *   It sums all the valid numbers received from clients.
        *   The server stops when the total sum exceeds 9000.
    *   **Client (`client.py`):
        *   Listens for the server's UDP broadcasts to know the current required number type (even or odd).
        *   Generates one random even and one random odd number at startup.
        *   Connects to the server via TCP and sends the appropriate number every 2 seconds, based on the server's state.
        *   Stops when it receives a "SERVER_STOPPED" message from the server.

### How to Run the Python `practice` Example:

1.  **Open a terminal** and navigate to the `py-examples/practice/` directory.
2.  **Start the server:**
    ```bash
    python3 server.py
    ```
3.  **Open at least two new terminal windows** and navigate to the same directory in each.
4.  **Start the clients:**
    ```bash
    python3 client.py
    ```
    Run this command in each of the new terminal windows. The server will then change its state from `STANDBY` to `EVEN` and begin processing numbers.
