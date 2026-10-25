PRJ := ./build/robot_sim

SRCDIR := ./src
INCDIR := ./include
OBJDIR := ./build

CC := gcc
CFLAGS := -std=c99 -pedantic -I $(INCDIR) -I $(SRCDIR) -Wall -Wextra -Werror -g -O0 -DDEBUG -MMD -MP -pthread
LDLIBS := -pthread -lrt -lm
LDFLAGS :=

sources := $(wildcard $(SRCDIR)/*.c)
objects := $(patsubst %.c, $(OBJDIR)/%.o, $(notdir $(sources)))

vpath %.c $(SRCDIR)

all: $(PRJ)

$(OBJDIR):
	mkdir -p $(OBJDIR)

$(OBJDIR)/%.o: %.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(PRJ): $(objects)
	$(CC) $(LDFLAGS) $(objects) $(LDLIBS) -o $(PRJ)

run: $(PRJ)
	$(PRJ)

.PHONY: all clean run

clean:
	rm -rf $(OBJDIR) data/*.txt

-include $(objects:.o=.d)
