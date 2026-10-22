/* tcp/hangman - server (process per client). Works with py-examples/tcp/hangman/client.py
 *
 * server -> client : word length (u32)
 * then repeat:
 *   client -> server : one letter (1 byte)
 *   server -> client : code (u32)
 *       1 = letter found: then count (u32) and count x index (u32, 0-based)
 *           if that completed the word the server then sends 2
 *       0 = wrong letter (chances left)
 *       2 = you won          3 = you lost (no chances left)
 * Usage: ./server <port> */
#include <time.h>

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

static const char *WORDS[] = {"dimethyltryptamine", "failure", "methanol", "interdisciplinarity",
                              "depression", "phenylpropanolamine"};
#define NWORDS (sizeof WORDS / sizeof WORDS[0])
#define MAX_WORD 64

static void handle(int c, const struct sockaddr_in *peer)
{
  char who[64];
  peer_str(peer, who, sizeof who);

  /* seed per child: time alone would give the same word to clients that connect in the same second */
  srand((unsigned)time(NULL) ^ ((unsigned)getpid() << 8));
  const char *word = WORDS[(unsigned)rand() % NWORDS];
  size_t len = strlen(word);
  int chances = 5 + rand() % 4;
  char revealed[MAX_WORD] = {0};
  size_t remaining = len;

  printf("%s has to guess \"%s\" in %d wrong shots\n", who, word, chances);
  if (send_u32(c, (uint32_t)len) != 0)
    return;

  for (;;) {
    unsigned char letter;
    if (recv_all(c, &letter, 1) != 0) {
      printf("%s disconnected\n", who);
      return;
    }
    uint32_t idx[MAX_WORD], n = 0;
    for (size_t i = 0; i < len; i++) {
      if ((unsigned char)word[i] == letter) {
        idx[n++] = (uint32_t)i;
        if (!revealed[i]) {
          revealed[i] = 1;
          remaining--;
        }
      }
    }
    if (n > 0) {
      if (send_u32(c, 1) != 0 || send_u32(c, n) != 0)
        return;
      for (uint32_t i = 0; i < n; i++)
        if (send_u32(c, idx[i]) != 0)
          return;
      if (remaining == 0) {
        send_u32(c, 2);
        printf("%s won\n", who);
        return;
      }
    } else {
      if (--chances == 0) {
        send_u32(c, 3);
        printf("%s lost\n", who);
        return;
      }
      if (send_u32(c, 0) != 0)
        return;
    }
  }
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
  printf("hangman server on port %d\n", port);
  serve_forever(s, handle);
  return 0;
}
