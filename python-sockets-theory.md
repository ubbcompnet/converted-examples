# Python TCP / UDP sockets – theory

Companion to `py-examples/`. Python's `socket` module is a thin wrapper over the C
Berkeley sockets API, so everything from the C examples (and lectures C1/C2) applies;
only the syntax differs.

## 1. The model

A socket is an endpoint identified by (protocol, local IP, local port); a TCP
connection is identified by the 4-tuple (src IP, src port, dst IP, dst port).

```python
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # TCP, IPv4
u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    # UDP, IPv4
```

| | TCP (`SOCK_STREAM`) | UDP (`SOCK_DGRAM`) |
|---|---|---|
| Connection | yes (3-way handshake) | none |
| Unit of data | **byte stream**, no message boundaries | **datagram**, boundaries kept |
| Reliability | retransmission, ordering, no duplicates | none: loss, reorder, duplicates possible |
| Flow / congestion control | yes | none |
| Max message | unlimited (stream) | ~65 507 bytes payload; keep < MTU (~1472) to avoid fragmentation |
| Broadcast / multicast | no | yes |
| Typical use | HTTP, SSH, file transfer, our protocols | DNS, DHCP, streaming, discovery, games |

## 2. Call sequences

TCP server: `socket → bind → listen → accept (loop) → recv/send → close`
TCP client: `socket → connect → send/recv → close`
UDP server: `socket → bind → recvfrom/sendto (loop)`
UDP client: `socket → sendto/recvfrom` (no connect needed; `bind` is implicit, ephemeral port)

```python
# TCP server
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # restart without "Address already in use"
srv.bind(("", 5000))            # "" = all interfaces (INADDR_ANY); "127.0.0.1" = loopback only
srv.listen(5)                   # backlog of pending connections
conn, addr = srv.accept()       # NEW socket for this client; srv keeps listening
data = conn.recv(1024)
conn.close()

# TCP client
c = socket.create_connection(("127.0.0.1", 5000))   # resolves + connects (getaddrinfo inside)

# UDP server / client
u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
u.bind(("", 5000))
data, addr = u.recvfrom(2048)
u.sendto(data, addr)
```

Notes:
- `accept()` returns a new connected socket; the listening socket is separate. In the C
  fork examples the parent must close the connected fd and the child the listener.
- `with socket.socket(...) as s:` closes automatically.
- Addresses are `(host, port)` tuples for IPv4; IPv6 uses 4-tuples (`AF_INET6`).
- `bind` to a port < 1024 needs privileges on Unix.

## 3. TCP is a stream (the most important idea)

`send(b"hello")` followed by `send(b"world")` may arrive as `helloworld`, `hel` + `loworld`,
or anything else. `recv(n)` returns *up to* n bytes, **0 bytes (`b""`) means the peer closed**.
So you must define message boundaries yourself:

1. **Length prefix** (recommended): 4-byte big-endian length, then the payload.
2. **Delimiter**: e.g. `\n` (HTTP headers use `\r\n\r\n`); payload must not contain it.
3. **Fixed size** messages.

Use `sendall()` (loops until everything is sent) and a `recv_exact` helper:

```python
import struct

def recv_exact(s, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed")
        buf += chunk
    return bytes(buf)

def send_msg(s, text):
    data = text.encode("utf-8")                 # encode FIRST, then measure BYTES, not characters
    s.sendall(struct.pack("!I", len(data)) + data)

def recv_msg(s):
    (n,) = struct.unpack("!I", recv_exact(s, 4))
    return recv_exact(s, n).decode("utf-8")
```

Why encode first: `len("ățî")` is 3 characters but 6 UTF-8 bytes. Sending the character
count and then the bytes (as `py-examples/tcp/string/client.py` does) breaks on non-ASCII text.

Rule: never trust a received length; cap it before allocating or looping.

## 4. Data encoding and byte order

Sockets carry bytes, not ints. Network byte order is **big-endian**.

```python
struct.pack("!I", 5)           # b'\x00\x00\x00\x05'  (! = network order, I = u32)
(5).to_bytes(4, "big")         # same bytes
int.from_bytes(b, "big")       # decode;   struct.unpack("!I", b)[0] also works
struct.pack("!i", -3)          # signed 32-bit;  "!H" u16, "!Q" u64, "!f" float, "!d" double
```

`to_bytes` with `signed=False` (default) raises `OverflowError` for negatives; pass
`signed=True` or use `"!i"`.

`socket.htonl()/ntohl()` exist but are rarely needed in Python: they return an *int* whose
in-memory bytes are swapped, e.g. on a little-endian host `socket.htonl(5) == 83886080`.
Do **not** feed that into `to_bytes(4, "big")` (double conversion, a bug in some of these
converted examples). Pick one: `struct.pack("!I", n)` or `n.to_bytes(4, "big")`.

Compatibility with the C examples: C `htonl(x)` + `send(&x, 4)` ≡ Python `struct.pack("!I", x)`.
C `htons` on a 4-byte `int` ≡ nothing sane – use `htonl`.

## 5. UDP specifics

- One `sendto` = one datagram; one `recvfrom(bufsize)` returns exactly one datagram. If
  `bufsize` is smaller than the datagram the rest is **silently discarded**.
- No ordering or delivery guarantee. Sending a length datagram then a data datagram (as
  `udp/string` does) can fail if they are reordered or one is lost: put the whole message in
  **one** datagram.
- Add your own sequence numbers / ACKs / timeouts if you need reliability (the `udp/100000`
  example shows loss and reordering when sending fast; the Python version's `sleep(0.001)`
  hides it on loopback).
- `connect()` on a UDP socket only sets a default peer (then `send`/`recv` work and ICMP
  errors surface); it creates no connection.
- **Broadcast**: `s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)` then `sendto(..., ("255.255.255.255", port))`
  or the subnet broadcast address. Receivers `bind(("", port))`; several receivers on one
  host need `SO_REUSEADDR` (on macOS/BSD sometimes also `SO_REUSEPORT`). Broadcast does not
  cross routers.
- Multicast: join a group with `IP_ADD_MEMBERSHIP`.

## 6. Blocking, timeouts, non-blocking

| Mode | How | Effect |
|---|---|---|
| Blocking (default) | – | `accept/recv/connect` wait forever |
| Timeout | `s.settimeout(5.0)` | raises `socket.timeout` (`TimeoutError`) |
| Non-blocking | `s.setblocking(False)` / `settimeout(0)` | raises `BlockingIOError` if not ready |

A `settimeout` on the listening socket is the easy way to make an accept loop that can
check a "running" flag (as `practice/server.py` does).

## 7. Serving many clients (lecture C2)

| Model | Python | Good for | Watch out |
|---|---|---|---|
| Iterative | plain loop | tiny demos | one slow client blocks all |
| Process per client | `os.fork()`, `multiprocessing` | isolation, no shared state | state not shared; reap children |
| Thread per client | `threading.Thread(target=handle, args=(conn, addr))` | shared state (games, chat) | protect shared data with `Lock`; races |
| Multiplexing | `select.select`, `selectors`, `poll`, `epoll` | many mostly-idle connections, one thread, no locks | never block inside a handler; keep per-client buffers |
| async | `asyncio.start_server` | very many connections | everything must be non-blocking/awaitable |

Threads and CPython: the GIL means threads do not run Python code in parallel, but they
are fine for I/O-bound servers because `recv/send/accept` release the GIL.

`select` skeleton (what `tcp/select/server.py` does):

```python
import select
inputs = [srv]
while True:
    readable, _, _ = select.select(inputs, [], [], 1.0)   # timeout optional
    for s in readable:
        if s is srv:
            conn, addr = srv.accept(); inputs.append(conn)
        else:
            data = s.recv(1024)
            if not data:                 # peer closed
                inputs.remove(s); s.close()
            else:
                ...                      # handle
```

- Use the socket object itself (or its fileno) in the lists, never an index into the list
  as a client id: indexes shift when clients leave. Keep a dict `sock -> id` instead.
- `select.select` on `sys.stdin` works on Unix, not on Windows.
- With a thread per client, keep the shared state under `with lock:` and make
  check-and-set operations (e.g. "is there already a winner?") atomic.

## 8. Error handling and shutdown

- `ConnectionRefusedError`: nobody listening. `ConnectionResetError` / `BrokenPipeError`:
  the peer vanished. `socket.timeout`. `OSError: [Errno 98] Address already in use`:
  set `SO_REUSEADDR` before `bind`.
- `recv` returning `b""` = orderly close; handle it everywhere or you loop forever.
- `shutdown(socket.SHUT_WR)` says "I'm done sending" but lets you still read the reply;
  `close()` releases the descriptor. (HTTP/1.0-style "read until EOF" protocols need this.)
- A TCP port stays in `TIME_WAIT` for ~1–2 min after an active close, hence `SO_REUSEADDR`.
- Always close in `finally` / a `with` block.

## 9. Name resolution

`socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)` returns every address (IPv4 and
IPv6) to try; `create_connection` does this for you. Prefer it over `gethostbyname`
(IPv4 only). `socket.inet_pton/ntop` convert between text and packed addresses.

## 10. Quick checklist for a correct Python socket program

- [ ] `SO_REUSEADDR` on listeners
- [ ] `sendall`, `recv_exact`, treat `b""` as closed
- [ ] explicit message framing (length prefix) and an agreed byte order (`"!"`)
- [ ] encode text to bytes before computing the length
- [ ] cap lengths received from the network
- [ ] timeouts so a silent client cannot hang a worker
- [ ] shared state protected (threads) or no shared state (processes)
- [ ] sockets closed on every path
- [ ] UDP: one message per datagram, sequence numbers if order/loss matters

## Further reading
- Python docs: `socket`, `select`, `selectors`, `struct`, `socketserver`
- `man 7 tcp`, `man 7 udp`, `man 2 recv`, `man 2 select`
- Beej's Guide to Network Programming (C, but the concepts map 1:1)
