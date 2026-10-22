# C and Python Socket Programming Examples

Client-server examples in C and Python for the UBB Computer Networks course. The C and Python
versions of each example use the **same wire protocol**, so any client works with any server
(except where a note says otherwise).

Wire conventions (see [c-sockets-theory.md](c-sockets-theory.md) and [python-sockets-theory.md](python-sockets-theory.md)):
integers are big-endian (network order), a string is `u32 length in bytes + UTF-8 bytes`,
and TCP reads/writes loop until all bytes are transferred (`recv_all`/`recv_exact`).

## Layout

| Path | Contents |
|------|----------|
| `tcp/<example>/`, `udp/<example>/` | C versions (`client.c`, `server.c`); every file is self-contained, its helpers (`send_all`, `recv_all`, ...) are at the top |
| `py-examples/tcp/<example>/`, `py-examples/udp/<example>/` | Python versions (same structure, also self-contained: `recv_exact`, `send_msg`, ... are defined in each file) |
| `py-examples/practice/` | custom exercise (see below) |
| `Makefile` | builds all C programs into `build/` |
| [`c-sockets-theory.md`](c-sockets-theory.md) | theory notes on C sockets (from lectures C1/C2 and Labs 1/2) |
| [`python-sockets-theory.md`](python-sockets-theory.md) | theory notes on Python TCP/UDP sockets |

## Examples

**TCP**
- `tcp/sum/` – client sends two signed 32-bit numbers, server returns the sum (64-bit).
- `tcp/string/` – client sends a string, server prints it.
- `tcp/spacecount/` – client sends a string, server returns the number of spaces.
- `tcp/reversestring/` – client sends a string, server returns it reversed.
- `tcp/hangman/` – Hangman over the network (C server; Python client and server in `py-examples/`).
- `tcp/select/` – chat server using `select()` to serve all clients from one process/thread.

**UDP**
- `udp/string/` – sends a string as one datagram; `bcast-client` sends it to a broadcast address.
- `udp/100000/` – sends 100000 numbered datagrams and reports how many arrived and in which order
  (shows that UDP can lose and reorder).

Servers for the simple TCP examples handle each client in its own process (C, `fork`) or thread
(Python). `tcp/select` is a single-process multiplexed server.

## Build and run

```bash
make                                   # C programs -> build/tcp/sum/server, ...
build/tcp/sum/server 5000 &            # C server
build/tcp/sum/client 127.0.0.1 5000    # C client
python3 py-examples/tcp/sum/client.py 127.0.0.1 5000   # Python client against the C server
```

Every server takes `<port>`; clients take `<host> <port>` (UDP clients: `<ipv4> <port>`).
`udp/100000/client.py` accepts an optional delay in seconds between datagrams.

## `py-examples/practice`

A custom client-server application:

- **Server (`server.py`)**
  - Waits for at least 2 clients before starting.
  - Broadcasts its state (`STANDBY`, `EVEN`, `ODD`) over UDP once per second.
  - Requests even numbers first and switches between even and odd every 100 accepted numbers.
  - Sums the valid numbers and stops when the total exceeds 9000, then broadcasts `SERVER_STOPPED`.
- **Client (`client.py [server_ip]`)**
  - Listens to the UDP broadcasts to learn which kind of number is wanted.
  - Generates one random even and one random odd number at startup.
  - Connects over TCP and sends the requested number every 2 seconds.
  - Stops when it learns that the server stopped.

```bash
cd py-examples/practice
python3 server.py                 # terminal 1
python3 client.py                 # terminals 2 and 3 (or: python3 client.py <server_ip>)
```

See [practice.txt](practice.txt) for the original task description.
