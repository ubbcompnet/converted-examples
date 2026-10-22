/* tcp/select - chat server: ONE process, select() multiplexes all clients.
 * Every line a client sends is forwarded to all the other clients.
 * Messages are plain text lines ending in '\n'.
 * Usage: ./server <port> */
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

int main(int argc, char **argv)
{
  int port = argc > 1 ? parse_port(argv[1]) : -1;
  if (port < 0) {
    fprintf(stderr, "usage: %s <port>\n", argv[0]);
    return 1;
  }
  int server = tcp_listen(port);
  if (server < 0) {
    perror("listen");
    return 1;
  }
  printf("chat server on port %d\n", port);

  fd_set master, readable;
  FD_ZERO(&master);
  FD_SET(server, &master);
  int fdmax = server;
  int ids[FD_SETSIZE] = {0}; /* socket -> client number (stays stable when others leave) */
  int next_id = 0;

  for (;;) {
    readable = master;
    if (select(fdmax + 1, &readable, NULL, NULL, NULL) < 0) {
      if (errno == EINTR)
        continue;
      perror("select");
      return 1;
    }
    for (int i = 0; i <= fdmax; i++) {
      if (!FD_ISSET(i, &readable))
        continue;

      if (i == server) {
        struct sockaddr_in peer;
        socklen_t len = sizeof peer;
        int c = accept(server, (struct sockaddr *)&peer, &len);
        if (c < 0) {
          perror("accept");
          continue;
        }
        if (c >= FD_SETSIZE) { /* select() cannot watch it */
          close(c);
          continue;
        }
        FD_SET(c, &master);
        if (c > fdmax)
          fdmax = c;
        ids[c] = ++next_id;
        char who[64], msg[128];
        printf("client %d connected from %s\n", ids[c], peer_str(&peer, who, sizeof who));
        int n = snprintf(msg, sizeof msg, "Welcome to the server! You are client %d\n", ids[c]);
        send_all(c, msg, (size_t)n);
      } else {
        char buf[512];
        ssize_t n = recv(i, buf, sizeof buf - 1, 0);
        if (n <= 0) {
          printf("client %d hung up\n", ids[i]);
          close(i);
          FD_CLR(i, &master);
          continue;
        }
        buf[n] = '\0';
        char out[1024];
        int m = snprintf(out, sizeof out, "Client %d says: %s", ids[i], buf);
        if (m >= (int)sizeof out)
          m = (int)sizeof out - 1;
        for (int j = 0; j <= fdmax; j++)
          if (FD_ISSET(j, &master) && j != server && j != i)
            if (send(j, out, (size_t)m, MSG_NOSIGNAL) < 0)
              perror("send");
      }
    }
  }
}
