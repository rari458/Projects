CC = gcc
CFLAGS = -Wall

# Directories
SRCDIR = src
DBBPT_SRCDIR = $(SRCDIR)/dbbpt
INMEMBPT_SRCDIR = $(SRCDIR)/inmembpt
BINDIR = bin
GIFTDIR = gift_from_ta
TESTOUT_DIR = test_out

# Source files
INMEMBPT_SRC = $(INMEMBPT_SRCDIR)/inmembpt.c
DBBPT_MAIN_SRC = $(DBBPT_SRCDIR)/main.c
DBBPT_BPT_SRC = $(DBBPT_SRCDIR)/dbbpt.c
FILE_MANAGER_SRC = $(DBBPT_SRCDIR)/file_manager.c

# Object files to be provided
OS := $(shell uname -s)
ifeq ($(OS),Linux)
    PROVIDED_OBJS = $(GIFTDIR)/dbbpt_linux.o
else ifeq ($(OS),Darwin)
    PROVIDED_OBJS = $(GIFTDIR)/dbbpt_mac.o
else
    $(error Unsupported OS: $(OS). Please use Linux or macOS.)
endif

# Targets
INMEMBPT_TARGET = $(BINDIR)/inmembpt
DBBPT_TARGET = $(BINDIR)/dbbpt
DBBPT_WITH_GIFTS_TARGET = $(BINDIR)/file_manager_tester

.PHONY: all clean inmembpt dbbpt file_manager_tester reset_test_env

all: inmembpt file_manager_tester dbbpt

inmembpt: $(INMEMBPT_TARGET)
$(INMEMBPT_TARGET): $(INMEMBPT_SRC)
	@mkdir -p $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $<

dbbpt: $(DBBPT_TARGET)
$(DBBPT_TARGET): $(DBBPT_MAIN_SRC) $(DBBPT_BPT_SRC) $(FILE_MANAGER_SRC)
	@mkdir -p $(BINDIR)
	@echo "Build dbbpt..."
	$(CC) $(CFLAGS) -o $@ $^

file_manager_tester: $(DBBPT_WITH_GIFTS_TARGET)
$(DBBPT_WITH_GIFTS_TARGET): $(PROVIDED_OBJS) $(FILE_MANAGER_SRC) $(DBBPT_MAIN_SRC)
	@mkdir -p $(BINDIR)
	@echo "Build dbbpt using your file manager source and TA's object files..."
	$(CC) $(CFLAGS) -o $@ $^

clean:
	@echo "Cleaning up..."
	rm -rf $(BINDIR)

reset_test_env:
	@echo "Setting up test environment..."
	rm -rf $(TESTOUT_DIR)
	mkdir -p $(TESTOUT_DIR)
