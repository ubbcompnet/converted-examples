# Builds every C example into build/<dir>/<name>, e.g. build/tcp/sum/server
CC     ?= cc
CFLAGS ?= -Wall -Wextra -O2

SRC := $(wildcard tcp/*/*.c udp/*/*.c)
BIN := $(patsubst %.c,build/%,$(SRC))

all: $(BIN)

build/%: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -rf build

.PHONY: all clean
