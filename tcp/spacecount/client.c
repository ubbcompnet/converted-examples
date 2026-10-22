/* tcp/spacecount - client. Usage: ./client <host> <port> */
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

/* String = u32 length + bytes. */
static int send_str(int fd, const char *s, size_t len)
{
  if (len > MAX_STR || send_u32(fd, (uint32_t)len) != 0)
    return -1;
  return send_all(fd, s, len);
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

/* Prompt, read one line (spaces allowed), strip the newline. 0 = ok. */
static int read_line(const char *prompt, char *buf, size_t size)
{
  printf("%s", prompt);
  fflush(stdout);
  if (!fgets(buf, (int)size, stdin))
    return -1;
  buf[strcspn(buf, "\r\n")] = '\0';
  return 0;
}

/* Connect to host:port (name or IP, IPv4/IPv6). Returns fd or -1. */
static int tcp_connect(const char *host, int port)
{
  signal(SIGPIPE, SIG_IGN);
  struct addrinfo hints, *res, *p;
  memset(&hints, 0, sizeof hints);
  hints.ai_family = AF_UNSPEC;
  hints.ai_socktype = SOCK_STREAM;
  char ps[16];
  snprintf(ps, sizeof ps, "%d", port);
  if (getaddrinfo(host, ps, &hints, &res) != 0)
    return -1;
  int fd = -1;
  for (p = res; p; p = p->ai_next) {
    fd = socket(p->ai_family, p->ai_socktype, p->ai_protocol);
    if (fd < 0)
      continue;
    if (connect(fd, p->ai_addr, p->ai_addrlen) == 0)
      break;
    close(fd);
    fd = -1;
  }
  freeaddrinfo(res);
  return fd;
}

int main(int argc, char **argv)
{
  int port = argc > 2 ? parse_port(argv[2]) : -1;
  if (port < 0) {
    fprintf(stderr, "usage: %s <host> <port>\n", argv[0]);
    return 1;
  }
  char line[1024];
  if (read_line("Enter a string: ", line, sizeof line) != 0) return 1;
  int c = tcp_connect(argv[1], port);
  if (c < 0) {
    perror("connect");
    return 1;
  }
  uint32_t count;
  if (send_str(c, line, strlen(line)) != 0 || recv_u32(c, &count) != 0) {
    fprintf(stderr, "connection error\n");
    close(c);
    return 1;
  }
  printf("Spaces: %u\n", count);
  close(c);
  return 0;
}
