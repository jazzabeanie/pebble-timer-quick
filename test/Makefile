# Makefile for running tests without Pebble SDK
# Usage: make test

CC = gcc
CFLAGS = -Wall -g

# Paths
PROJECT_ROOT = ..
SRC_DIR = $(PROJECT_ROOT)/src
TEST_DIR = .
CMOCKA_DIR = $(PROJECT_ROOT)/vendor/cmocka_install

# Include paths
INCLUDES = -I$(TEST_DIR) -I$(SRC_DIR) -I$(CMOCKA_DIR)/include

# Library paths and libs
LDFLAGS = -L$(CMOCKA_DIR)/lib -Wl,-rpath,$(CMOCKA_DIR)/lib
LIBS = -lcmocka

# Source files
TEST_TIMER_SRCS = test_timer.c
TIMER_SRCS = $(SRC_DIR)/timer.c
TEST_MAIN_SRCS = test_main_logic.c

# Output
TEST_TIMER_BIN = run_test_timer
TEST_MAIN_BIN = run_test_main

.PHONY: all test test_timer test_main clean

all: $(TEST_TIMER_BIN) $(TEST_MAIN_BIN)

$(TEST_TIMER_BIN): $(TEST_TIMER_SRCS) $(TIMER_SRCS)
	$(CC) $(CFLAGS) $(INCLUDES) $^ -o $@ $(LDFLAGS) $(LIBS)

$(TEST_MAIN_BIN): $(TEST_MAIN_SRCS) $(TIMER_SRCS)
	$(CC) $(CFLAGS) $(INCLUDES) $^ -o $@ $(LDFLAGS) $(LIBS)

# Run all tests
test: test_timer test_main

# Run individual tests
test_timer: $(TEST_TIMER_BIN)
	./$(TEST_TIMER_BIN)

test_main: $(TEST_MAIN_BIN)
	./$(TEST_MAIN_BIN)

clean:
	rm -f $(TEST_TIMER_BIN) $(TEST_MAIN_BIN)
