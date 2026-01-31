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
TEST_SRCS = test_timer.c
TIMER_SRCS = $(SRC_DIR)/timer.c
MAIN_LOGIC_SRCS = test_main_logic.c

# Output
TEST_BIN = run_tests
MAIN_LOGIC_BIN = run_test_main_logic

.PHONY: all test test_main_logic clean

all: $(TEST_BIN) $(MAIN_LOGIC_BIN)

$(TEST_BIN): $(TEST_SRCS) $(TIMER_SRCS)
	$(CC) $(CFLAGS) $(INCLUDES) $^ -o $@ $(LDFLAGS) $(LIBS)

$(MAIN_LOGIC_BIN): $(MAIN_LOGIC_SRCS) $(TIMER_SRCS)
	$(CC) $(CFLAGS) $(INCLUDES) $^ -o $@ $(LDFLAGS) $(LIBS)

test: $(TEST_BIN)
	./$(TEST_BIN)

test_main_logic: $(MAIN_LOGIC_BIN)
	./$(MAIN_LOGIC_BIN)

clean:
	rm -f $(TEST_BIN) $(MAIN_LOGIC_BIN)
