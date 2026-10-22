/* udp/100000 - client: sends COUNT datagrams as fast as it can, each holding
 * its sequence number as a big-endian u32. Usage: ./client <ip> <port> */
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
  int port = argc > 2 ? parse_port(argv[2]) : -1;
  struct sockaddr_in to;
  memset(&to, 0, sizeof to);
  to.sin_family = AF_INET;
  to.sin_port = htons((uint16_t)(port > 0 ? port : 0));
  if (port < 0 || inet_pton(AF_INET, argv[1], &to.sin_addr) != 1) {
    fprintf(stderr, "usage: %s <ipv4-address> <port>\n", argv[0]);
    return 1;
  }
  int s = socket(AF_INET, SOCK_DGRAM, 0);
  if (s < 0) {
    perror("socket");
    return 1;
  }
  long failed = 0;
  for (uint32_t i = 0; i < COUNT; i++) {
    uint32_t n = htonl(i);
    if (sendto(s, &n, sizeof n, 0, (struct sockaddr *)&to, sizeof to) < 0)
      failed++;
    if (i % 10000 == 0)
      printf("sent %u\n", i);
  }
  printf("done, %ld sendto() calls failed\n", failed);
  close(s);
  return 0;
}
