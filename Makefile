CFLAGS += -Wall -Wextra -Wno-unused-parameter -std=c99
OBJS = objects/object.o test_objects.o

test_objects: $(OBJS)
	cc $(CFLAGS) $(OBJS) -o test_objects

all: test_objects

clean:
	find -name '*.o' -print -delete
	rm -fv test_objects
