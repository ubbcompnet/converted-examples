/* udp/string - client: sends the line you type as ONE datagram.
 * Usage: ./client <ip> <port> */
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

#define MAX_MSG 1400 /* stay below the Ethernet MTU: no IP fragmentation */

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
  char line[MAX_MSG + 1];
  if (read_line("Enter a string: ", line, sizeof line) != 0)
    return 1;
  ssize_t n = sendto(s, line, strlen(line), 0, (struct sockaddr *)&to, sizeof to);
  if (n < 0) {
    perror("sendto");
    return 1;
  }
  printf("Sent %zd bytes\n", n);
  close(s);
  return 0;
}
