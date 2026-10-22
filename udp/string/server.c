/* udp/string - server. One datagram = one message (no length prefix needed:
 * UDP keeps datagram boundaries). Prints every datagram it receives.
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

#define BUF 2048 /* a datagram longer than this would be silently truncated */

int main(int argc, char **argv)
{
  int port = argc > 1 ? parse_port(argv[1]) : -1;
  if (port < 0) {
    fprintf(stderr, "usage: %s <port>\n", argv[0]);
    return 1;
  }
  int s = socket(AF_INET, SOCK_DGRAM, 0);
  if (s < 0) {
    perror("socket");
    return 1;
  }
  int one = 1;
  setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
  struct sockaddr_in a;
  memset(&a, 0, sizeof a);
  a.sin_family = AF_INET;
  a.sin_addr.s_addr = htonl(INADDR_ANY);
  a.sin_port = htons((uint16_t)port);
  if (bind(s, (struct sockaddr *)&a, sizeof a) < 0) {
    perror("bind");
    return 1;
  }
  printf("udp server waiting on port %d\n", port);

  for (;;) {
    char buf[BUF];
    struct sockaddr_in from;
    socklen_t len = sizeof from;
    ssize_t n = recvfrom(s, buf, sizeof buf - 1, 0, (struct sockaddr *)&from, &len);
    if (n < 0) {
      if (errno == EINTR)
        continue;
      perror("recvfrom");
      return 1;
    }
    buf[n] = '\0'; /* datagrams carry no terminating NUL */
    char who[64];
    printf("%s (%zd bytes): %s\n", peer_str(&from, who, sizeof who), n, buf);
  }
}
