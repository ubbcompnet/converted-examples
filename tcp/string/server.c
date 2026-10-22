/* tcp/string - server (process per client)
 * client -> server : a string (u32 length + bytes)
 * The server prints it. Usage: ./server <port> */
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

#define MAX_STR (1u << 20) /* largest string accepted from the network */

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

static int recv_u32(int fd, uint32_t *v)
{
  uint32_t n;
  if (recv_all(fd, &n, sizeof n) != 0)
    return -1;
  *v = ntohl(n);
  return 0;
}

/* Receive a string into a freshly malloc'ed, NUL-terminated buffer.
 * The length announced by the peer is checked before allocating. */
static int recv_str(int fd, char **out, uint32_t *len_out)
{
  uint32_t len;
  if (recv_u32(fd, &len) != 0 || len > MAX_STR)
    return -1;
  char *s = malloc((size_t)len + 1);
  if (!s)
    return -1;
  if (recv_all(fd, s, len) != 0) {
    free(s);
    return -1;
  }
  s[len] = '\0';
  *out = s;
  if (len_out)
    *len_out = len;
  return 0;
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
  char *str;
  uint32_t len;
  if (recv_str(c, &str, &len) != 0) {
    printf("%s: bad or incomplete message\n", who);
    return;
  }
  printf("%s sent %u bytes: %s\n", who, len, str);
  free(str);
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
  printf("string server on port %d\n", port);
  serve_forever(s, handle);
  return 0;
}
