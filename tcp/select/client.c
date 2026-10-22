/* tcp/select - chat client: select() on the keyboard and the socket.
 * Usage: ./client <host> <port> */
#include <sys/select.h>

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

/* "1..65535" -> port, otherwise -1. */
static int parse_port(const char *s)
{
  char *end;
  long v = strtol(s, &end, 10);
  if (*s == '\0' || *end != '\0' || v < 1 || v > 65535)
    return -1;
  return (int)v;
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
  int c = tcp_connect(argv[1], port);
  if (c < 0) {
    perror("connect");
    return 1;
  }

  for (;;) {
    fd_set rd;
    FD_ZERO(&rd);
    FD_SET(STDIN_FILENO, &rd);
    FD_SET(c, &rd);
    if (select(c + 1, &rd, NULL, NULL, NULL) < 0) {
      if (errno == EINTR)
        continue;
      perror("select");
      return 1;
    }
    char buf[512];
    if (FD_ISSET(STDIN_FILENO, &rd)) {
      ssize_t n = read(STDIN_FILENO, buf, sizeof buf);
      if (n <= 0) /* Ctrl-D */
        break;
      if (send_all(c, buf, (size_t)n) != 0) {
        perror("send");
        return 1;
      }
    }
    if (FD_ISSET(c, &rd)) {
      ssize_t n = recv(c, buf, sizeof buf, 0);
      if (n <= 0) {
        printf("Server has closed the connection...\n");
        return 2;
      }
      fwrite(buf, 1, (size_t)n, stdout);
      fflush(stdout);
    }
  }
  close(c);
  return 0;
}
