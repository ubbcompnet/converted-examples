/* tcp/sum - server (process per client)
 * client -> server : a, b  (two signed 32-bit ints, big-endian)
 * server -> client : a + b (signed 64-bit, as two big-endian u32: high, low)
 * Usage: ./server <port> */
#include <arpa/inet.h>
#include <errno.h>
#include <netdb.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

/* ---- helpers: TCP is a byte stream, send()/recv() may move fewer bytes than asked ---- */

#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0 /* macOS: SIGPIPE is ignored instead */
#endif

/* Send exactly n bytes. 0 = ok, -1 = error. */
static int send_all(int fd, const void *buf, size_t n)
{
  const char *p = buf;
  while (n > 0) {
    ssize_t k = send(fd, p, n, MSG_NOSIGNAL);
    if (k < 0) {
      if (errno == EINTR)
        continue;
      return -1;
    }
    p += k;
    n -= (size_t)k;
  }
  return 0;
}

/* Receive exactly n bytes. 0 = ok, -1 = error or peer closed early. */
static int recv_all(int fd, void *buf, size_t n)
{
  char *p = buf;
  while (n > 0) {
    ssize_t k = recv(fd, p, n, 0);
    if (k == 0)
      return -1; /* orderly close */
    if (k < 0) {
      if (errno == EINTR)
        continue;
      return -1;
    }
    p += k;
    n -= (size_t)k;
  }
  return 0;
}

static int send_u32(int fd, uint32_t v)
{
  uint32_t n = htonl(v);
  return send_all(fd, &n, sizeof n);
}

static int recv_u32(int fd, uint32_t *v)
{
  uint32_t n;
  if (recv_all(fd, &n, sizeof n) != 0)
    return -1;
  *v = ntohl(n);
  return 0;
}

/* Signed 64-bit value sent as two u32 (high word first). */
static int send_i64(int fd, int64_t v)
{
  uint64_t u = (uint64_t)v;
  if (send_u32(fd, (uint32_t)(u >> 32)) != 0)
    return -1;
  return send_u32(fd, (uint32_t)(u & 0xffffffffu));
}

/* "1..65535" -> port, otherwise -1. */
static int parse_port(const char *s)
{
  char *end;
  long v = strtol(s, &end, 10);
  if (*s == '\0' || *end != '\0' || v < 1 || v > 65535)
    return -1;
  return (int)v;
}

/* "ip:port" of a peer, for log messages. */
static const char *peer_str(const struct sockaddr_in *a, char *buf, size_t n)
{
  char ip[INET_ADDRSTRLEN];
  inet_ntop(AF_INET, &a->sin_addr, ip, sizeof ip);
  snprintf(buf, n, "%s:%u", ip, (unsigned)ntohs(a->sin_port));
  return buf;
}

/* TCP listener on all interfaces. Returns fd or -1. */
static int tcp_listen(int port)
{
  signal(SIGPIPE, SIG_IGN); /* a vanished client must not kill the server */
  int s = socket(AF_INET, SOCK_STREAM, 0);
  if (s < 0)
    return -1;
  int one = 1;
  setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
  struct sockaddr_in a;
  memset(&a, 0, sizeof a);
  a.sin_family = AF_INET;
  a.sin_addr.s_addr = htonl(INADDR_ANY);
  a.sin_port = htons((uint16_t)port);
  if (bind(s, (struct sockaddr *)&a, sizeof a) < 0 || listen(s, 16) < 0) {
    close(s);
    return -1;
  }
  return s;
}

/* Process-per-client accept loop (lecture C2).
 * - the parent closes the connected socket, the child closes the listener
 * - the child always exits after handle(), it never goes back to accept()
 * - SIGCHLD is ignored so finished children do not stay zombies */
static void serve_forever(int listener,
                                 void (*handle)(int, const struct sockaddr_in *))
{
  signal(SIGCHLD, SIG_IGN);
  for (;;) {
    struct sockaddr_in peer;
    socklen_t len = sizeof peer;
    int c = accept(listener, (struct sockaddr *)&peer, &len);
    if (c < 0) {
      if (errno != EINTR)
        perror("accept");
      continue;
    }
    pid_t pid = fork();
    if (pid < 0) {
      perror("fork");
      close(c);
      continue;
    }
    if (pid == 0) {
      close(listener);
      handle(c, &peer);
      close(c);
      _exit(0);
    }
    close(c);
  }
}

static void handle(int c, const struct sockaddr_in *peer)
{
  char who[64];
  peer_str(peer, who, sizeof who);
  uint32_t ua, ub;
  if (recv_u32(c, &ua) != 0 || recv_u32(c, &ub) != 0) {
    printf("%s: disconnected before sending both numbers\n", who);
    return;
  }
  int32_t a = (int32_t)ua, b = (int32_t)ub;
  int64_t sum = (int64_t)a + b;
  printf("%s: %d + %d = %lld\n", who, a, b, (long long)sum);
  send_i64(c, sum);
}

int main(int argc, char **argv)
{
  int port = argc > 1 ? parse_port(argv[1]) : -1;
  if (port < 0) {
    fprintf(stderr, "usage: %s <port>\n", argv[0]);
    return 1;
  }
  int s = tcp_listen(port);
  if (s < 0) {
    perror("listen");
    return 1;
  }
  printf("sum server on port %d\n", port);
  serve_forever(s, handle);
  return 0;
}
