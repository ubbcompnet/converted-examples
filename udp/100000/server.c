/* udp/100000 - server: counts how many of the COUNT numbered datagrams arrive
 * and whether they arrive in order. UDP gives no guarantee, so under load you
 * will see loss and/or reordering.
 *
 * A round starts with the first datagram and ends after COUNT datagrams or
 * after 2 seconds of silence; then the summary is printed and a new round starts.
 * Datagram = u32 sequence number, big-endian, from 0 to COUNT-1.
 * Usage: ./server <port> */
#include <sys/time.h>

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

#define COUNT 100000

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
  printf("waiting for %d numbered datagrams on port %d\n", COUNT, port);

  for (;;) {
    struct timeval tv = {0, 0}; /* 0 = wait forever for the first datagram */
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
    long received = 0, jumps = 0;
    uint32_t expected = 0;

    while (received < COUNT) {
      uint32_t num;
      ssize_t n = recvfrom(s, &num, sizeof num, 0, NULL, NULL);
      if (n < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
          break; /* silence: the round is over */
        if (errno == EINTR)
          continue;
        perror("recvfrom");
        return 1;
      }
      if (n != (ssize_t)sizeof num)
        continue;
      if (received == 0) {
        tv.tv_sec = 2;
        setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
      }
      num = ntohl(num);
      if (num != expected) {
        if (jumps < 5)
          printf("unexpected number: wanted %u, got %u\n", expected, num);
        jumps++;
      }
      expected = num + 1;
      received++;
    }
    printf("round finished: received %ld of %d (lost %ld), %ld out-of-sequence\n", received, COUNT,
           COUNT - received, jumps);
  }
}
