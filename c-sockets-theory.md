# C sockets – theory

Based on lectures C1 and C2 (`Lecture_1`, `Lecture_2` slides), Lab 1 (data encoding over TCP) and
Lab 2 (concurrent servers). Every snippet below is used in the fixed examples of this repo
(the helper section at the top of each file in `tcp/` and `udp/`); the Python counterpart is `python-sockets-theory.md`.

## 1. Big picture

- A **socket** is the door a process uses to talk to the network; the OS is on the other side of the
  door. The API comes from BSD 4.1 Unix (1981) and offers two services: a reliable **byte stream**
  (TCP, `SOCK_STREAM`) and an unreliable **datagram** service (UDP, `SOCK_DGRAM`).
- A process is addressed by **IP address + port** (32-bit IPv4 address, 16-bit port).
  A TCP connection is identified by the 4-tuple (client IP, client port, server IP, server port),
  which is why one listening port can serve many clients.
- Client-server: the server runs first and waits; the **client speaks first** (initiates contact).
- The application protocol (message types, syntax, semantics, rules for who sends when) is your job;
  TCP/UDP only move bytes/datagrams.

## 2. Call sequences

```
TCP server                              TCP client
socket()                                socket()
setsockopt(SO_REUSEADDR)
bind(port)
listen(backlog)
accept()  <---- 3-way handshake ---->   connect()
recv()/send()  <--- bytes --->          send()/recv()
close()                                 close()

UDP server                              UDP client
socket(SOCK_DGRAM)                      socket(SOCK_DGRAM)
bind(port)
recvfrom()  <--- 1 datagram --------    sendto()
sendto()    ---- 1 datagram -------->   recvfrom()
```

- `listen` marks the **welcome socket**; it never carries data. `accept` returns a **new** socket for
  one client, and the welcome socket keeps listening. This is what makes serving many clients possible.
- UDP has no `listen/accept/connect` (not needed, not allowed). The client does not `bind`: the OS
  assigns an ephemeral port on the first `sendto`.
- Every call can fail: check the return value (`-1` + `errno`, `perror`). Treat `recv() == 0` as
  "the peer closed the connection".

```c
int s = socket(AF_INET, SOCK_STREAM, 0);                 /* < 0 means error, not == 0 */
int one = 1;
setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);  /* before bind */
struct sockaddr_in a;
memset(&a, 0, sizeof a);
a.sin_family      = AF_INET;
a.sin_addr.s_addr = htonl(INADDR_ANY);                   /* all interfaces */
a.sin_port        = htons(1500);
bind(s, (struct sockaddr *)&a, sizeof a);
listen(s, 16);
int c = accept(s, (struct sockaddr *)&peer, &len);       /* len is a socklen_t, set before the call */
```

## 3. Addresses

- `struct sockaddr` is the generic type (`sa_family` + `sa_data[14]`); `struct sockaddr_in` is the
  IPv4 one (`sin_family`, `sin_port`, `sin_addr`, `sin_zero`). You fill a `sockaddr_in` and
  **cast** it to `struct sockaddr *` in every call. Zero it first with `memset`.
- Text <-> binary: `inet_pton(AF_INET, "192.168.1.5", &a.sin_addr)` and
  `inet_ntop(AF_INET, &a.sin_addr, buf, sizeof buf)`. Avoid `inet_addr` (returns `-1`, which is also the
  valid address 255.255.255.255) and `inet_ntoa` (static buffer: two calls in one `printf` print the same
  address; not thread-safe).
- Names: `getaddrinfo(host, port, &hints, &res)` (thread-safe, IPv4/IPv6) then try each `res`
  entry; free with `freeaddrinfo`. `gethostbyname` is obsolete and not thread-safe. See `tcp_connect()` in
  the top of `tcp/*/client.c`.
- `getsockname` / `getpeername` give the local / remote address of a connected socket.

## 4. Byte order (Lab 1)

The network carries **bytes**. Multi-byte integers must be put in **network byte order = big-endian**.
x86 and ARM are little-endian: `0x12345678` is stored `78 56 34 12`.

| Function | Meaning | Size |
|---|---|---|
| `htons` / `ntohs` | host<->network short | 16 bit (ports) |
| `htonl` / `ntohl` | host<->network long | **32 bit** (your integers, `s_addr`) |

Rules (they are the point of Lab 1):

1. Use fixed-width types (`uint32_t`, `int32_t`), never raw `int`/`long` (sizes differ between systems).
2. `htonl` for 32-bit values. **`htons` on a 32-bit `int` converts only 16 bits**: it appears to work for
   small numbers on little-endian machines and breaks otherwise, and it does not interoperate with
   big-endian peers (the bug in the original `tcp/sum` and `tcp/string`).
3. Convert each field separately; never send a raw `struct` (padding and alignment differ) or pointers.
4. Signed values: send `(uint32_t)(int32_t)v`, cast back after `ntohl`. 64-bit: send two 32-bit halves
   (`send_i64` in `tcp/sum/server.c`).
5. Single bytes and `char` arrays need no conversion (but strings need a length).
6. Floats have no `hton`: send decimal text, or `memcpy` the IEEE-754 bits into a `uint32_t` and `htonl`
   it. `float` = 1 sign + 8 exponent + 23 mantissa bits; `double` has the same endianness as integers.
7. Print a received port with `ntohs(addr.sin_port)`.

## 5. TCP is a stream (Lab 1)

`send` returns how many bytes the OS **accepted**, not how many were delivered; `recv` returns *up to*
the requested number. One `send` of 8 bytes can arrive as two `recv`s of 4, and two `send`s as one `recv`.
Therefore:

- **Frame your messages**: a length prefix (`u32 length + bytes`, used everywhere in this repo), a fixed
  size, or a delimiter (`\0`, `\n`). The lab's `charcount` example sends the string with its `\0` and reads
  it byte by byte: it works but costs a syscall per byte and cannot carry `\0` in the data.
- **Loop** until you have everything:

```c
int recv_all(int fd, void *buf, size_t n) {
  char *p = buf;
  while (n > 0) {
    ssize_t k = recv(fd, p, n, 0);
    if (k == 0) return -1;                    /* peer closed early */
    if (k < 0) { if (errno == EINTR) continue; return -1; }
    p += k; n -= (size_t)k;
  }
  return 0;
}
```
  `send_all` is the same with `send`. `MSG_WAITALL` is valid only for `recv` (and can still return short
  on a signal); passing it to `send` does nothing useful.
- **Validate untrusted lengths** before `malloc`/looping (`MAX_STR` in `tcp/string/server.c`), and allocate `len + 1`
  to NUL-terminate. A bug in the original `tcp/string/server.c` used `b * sizeof(str)` (8x too many bytes).
- Strings: the length counts **bytes**; characters are not bytes in UTF-8.
- Error reporting in replies: a status word or a negative `int32_t` (the lab example uses `-1`, `-2`).

## 6. UDP (Lecture C2)

| | TCP | UDP |
|---|---|---|
| write | bytes into a stream | one datagram |
| read | from the stream; unread bytes stay for the next read | from one datagram; **unread bytes are lost** |
| delivery | reliable, ordered | none: loss, reordering, duplicates possible |
| flow control | yes | no: a fast sender can overflow the receiver |

- `sendto(s, buf, len, 0, (struct sockaddr *)&to, sizeof to)`: returns bytes handed to the network; `-1`
  only for *local* errors, an undelivered datagram is **not** reported. Max ~64 KB, keep it under the
  MTU (~1400 bytes) to avoid IP fragmentation.
- `recvfrom(s, buf, len, 0, (struct sockaddr *)&from, &fromlen)`: blocks for one datagram; if `buf` is
  smaller, the rest is **discarded**. `fromlen` must be set (a `socklen_t`) before the call.
- One `sendto` = one `recvfrom`. Datagram boundaries already frame the message, so `udp/string` sends the
  text alone; two datagrams (length + data) can arrive swapped or one can be lost.
- Byte-order rules still apply to integers inside datagrams (`udp/100000` sends `htonl(i)`).
- Datagrams carry no `\0`: terminate the buffer yourself (`buf[n] = '\0'`).
- **Broadcast**: UDP only, not routed beyond the local network. The sender sets
  `SO_BROADCAST` and uses the subnet broadcast (e.g. `192.168.1.255`) or `255.255.255.255`; receivers
  `bind` to `INADDR_ANY:port`. Several listeners on one host need `SO_REUSEADDR` (macOS: also
  `SO_REUSEPORT`) before `bind`.

## 7. Socket options

`setsockopt(s, level, optname, &value, sizeof value)`; docs in `man 7 socket|tcp|udp|ip`.
- `SO_REUSEADDR`: lets a restarted server re-bind its port while old connections sit in TIME_WAIT
  (otherwise `bind` fails with "Address already in use"). Set it before `bind`.
- `SO_BROADCAST`: required to `sendto` a broadcast address.
- `SO_RCVTIMEO` / `SO_SNDTIMEO`: timeout for `recv`/`send` (`EAGAIN` when it expires; `udp/100000/server.c`
  uses it to end a round after 2 s of silence).
- `MSG_NOSIGNAL` (flag of `send`) or `signal(SIGPIPE, SIG_IGN)`: writing to a closed connection raises
  `SIGPIPE` and kills the process by default.

## 8. Serving many clients (Lecture C2 / Lab 2)

| Model | How | Use when | Cost |
|---|---|---|---|
| Iterative | `accept` loop, handle inline | tiny demos | one slow client blocks everyone |
| Process per client | `fork` | clients are independent; isolation, `exec`, per-client `alarm` | no shared memory (IPC needed) |
| Thread per client | `pthread_create` | clients share state (game, chat, shared array) | locks, races; one crash kills all |
| Multiplexed | `select`/`poll`/`epoll` in one process | shared state without locks, timeouts, many idle clients | one slow handler blocks all; state machine style |

Pick by state: independent clients -> fork (or threads); interdependent -> threads (+ mutex) or `select`.

### fork server (`serve_forever()` in `tcp/sum/server.c`)

```c
signal(SIGCHLD, SIG_IGN);                       /* reap children automatically, no zombies */
for (;;) {
  int c = accept(s, (struct sockaddr *)&peer, &len);
  if (c < 0) { if (errno != EINTR) perror("accept"); continue; }
  pid_t pid = fork();
  if (pid < 0) { perror("fork"); close(c); continue; }
  if (pid == 0) { close(s); handle(c); close(c); _exit(0); }   /* child: must exit */
  close(c);                                                     /* parent: must close */
}
```

- The child **must exit**, otherwise it falls into the `accept` loop and processes multiply. A `continue`
  inside the child (as in the original examples) does exactly that.
- The parent **must close the accepted socket** (descriptor leak; the peer never sees FIN while the
  parent still holds a copy) and the child closes the listener.
- `accept` failure is `c < 0`, not `c == 0`; check it in the **parent**, before forking.
- Per-client timeout with `alarm()`+`SIGALRM` works because each child is its own process; with threads use
  `SO_RCVTIMEO` or `select`/`poll` timeouts. Do not call `printf`/`send` in a signal handler.

### thread server

```c
int *arg = malloc(sizeof *arg);  *arg = accept(...);           /* own copy per thread */
pthread_t t;  pthread_create(&t, NULL, worker, arg);  pthread_detach(t);
```
Compile with `-pthread`. Protect shared data with a mutex and make check-and-set operations (such as
"is there already a winner?") atomic. Thread-unsafe library calls (`inet_ntoa`, `gethostbyname`, `strtok`,
`getpwent`, `ctime`, `rand`, `strerror`) have `_r` or modern replacements (`inet_ntop`, `getaddrinfo`,
`strtok_r`, `getpwnam_r`, `ctime_r`, `rand_r`, `strerror_r`).

### select server (`tcp/select`)

```c
fd_set master, readable;
FD_ZERO(&master); FD_SET(listener, &master); int fdmax = listener;
for (;;) {
  readable = master;                                   /* select() overwrites the set */
  select(fdmax + 1, &readable, NULL, NULL, NULL);      /* highest fd + 1, not a count */
  for (int i = 0; i <= fdmax; i++) if (FD_ISSET(i, &readable)) {
    if (i == listener) { /* accept, FD_SET, update fdmax */ }
    else               { /* recv; <= 0: close(i), FD_CLR(i, &master); else handle */ }
  }
}
```
- Returns the number of ready fds, `0` on timeout, `-1` on error (retry on `EINTR`).
- A **readable listener** means "a connection is waiting" (so `accept` will not block); a readable client
  socket may mean data **or** EOF (`recv` returns 0).
- Timeout: a `struct timeval`; `NULL` = wait forever. On Linux `select` modifies it, so set it again
  before every call (lab 2 task 3: 10 s inactivity).
- Limits: `FD_SETSIZE` (usually 1024); `poll`/`epoll` have no such cap. Never block on one client
  inside the loop; keep per-client input buffers because one `recv` can hold half a message or three.
- The client uses `select` on fd 0 (stdin) and the socket so incoming messages appear while typing.

## 9. I/O models (Lecture C2)

A read has two phases: (1) wait for data, (2) copy it from the kernel to user space.

1. **Blocking** (default): the process sleeps through both phases.
2. **Non-blocking**: returns immediately with `EWOULDBLOCK`/`EAGAIN` if not ready; you poll in a loop.
3. **Multiplexed** (`select`, `poll`): block on many descriptors; the following `recv` will not block.
4. **Signal-driven** (`SIGIO`): the kernel signals when data is *ready*.
5. **Asynchronous** (`aio_read`): the kernel does both phases and signals when the operation is *complete*.

With plain blocking I/O both sides must agree exactly who reads and who writes; an unexpected extra
`read` blocks forever (deadlock), which is one motivation for `select`.

## 10. Closing

`close(fd)` releases the descriptor (the connection ends when every copy of it is closed, which matters
after `fork`). `shutdown(fd, SHUT_WR)` says "I am done sending" while still allowing reads. A closed TCP
port stays in TIME_WAIT for a while, hence `SO_REUSEADDR`.

## 11. How the labs map to this

| Topic | Where |
|---|---|
| Fixed-width ints, `htonl`, length prefix, `send_all`/`recv_all` | Lab 1 tasks 1-14; helper section of each `tcp/*` program |
| Sum/string/space count/reverse | `tcp/sum`, `tcp/string`, `tcp/spacecount`, `tcp/reversestring` |
| fork-per-client | Lab 2 `charcount`; `serve_forever()` |
| Threads + shared state | Lab 2 tasks 4, 6, 8, 9 (arrays, guessing game, P2P registry) |
| `select` + timeout | Lab 2 task 3 (float guess, 10 s); `tcp/select` |
| UDP, broadcast | `udp/string`, `udp/100000` |
| Game protocol design | `tcp/hangman` (codes: 1 found / 0 wrong / 2 won / 3 lost) |

## 12. Checklist for a correct C socket program

- [ ] every syscall's return value checked (`socket`/`accept` `< 0`, `recv == 0` = closed)
- [ ] fixed-width types on the wire, `htonl`/`ntohl` (not `htons`) for 32-bit values, big-endian
- [ ] length-prefixed messages, `send_all`/`recv_all` loops, lengths validated before allocation
- [ ] `SO_REUSEADDR` on listeners; `SIGPIPE` ignored or `MSG_NOSIGNAL`
- [ ] fork: child exits, parent closes the client fd, `SIGCHLD` handled; threads: own copy of the fd,
      mutex around shared state, `_r` functions
- [ ] `select`: master set copied each loop, `EINTR` retried, buffers sized `sizeof buf - 1`
- [ ] `inet_pton`/`inet_ntop`/`getaddrinfo` instead of `inet_addr`/`inet_ntoa`/`gethostbyname`
- [ ] UDP: one message per datagram, buffer big enough, sequence numbers if order or loss matters
- [ ] all descriptors closed on every path, memory freed

## Further reading
`man 2 socket|bind|listen|accept|connect|send|recv|select`, `man 7 socket|tcp|udp|ip`; Stevens, *UNIX
Network Programming vol. 1*; Beej's Guide to Network Programming; Kurose & Ross, *Computer Networking*.
