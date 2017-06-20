#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "objects/object.h"

#define assert_streq(a, b) assert(strcmp((a), (b)) == 0)


int destroyed = 0;
static void destroy_cb(void *data) { destroyed = 1; }

void test_refcounts(void)
{
	char data[] = "hello";

	struct WeirdObject *test = weirdobject_new("WoloWolo", destroy_cb, (void *) data);
	assert(test->refcount == 0);
	assert(strcmp((char *) test->data, "hello") == 0);

	weirdobject_incref(test);
	weirdobject_incref(test);
	weirdobject_incref(test);
	assert(test->refcount == 3);
	assert_streq((char *) test->data, "hello");

	weirdobject_decref(test);
	weirdobject_decref(test);
	assert(test->refcount == 1);
	assert_streq((char *) test->data, "hello");

	assert(!destroyed);
	weirdobject_decref(test);
	// test is freed, can't check refcounts and stuff anymore
	assert(destroyed);
	assert(test->refcount == 0);
}


char *program_name;

void run(char *name, void (test)(void))
{
	test();
	printf("%s: test_%s is OK\n", program_name, name);
}

int main(int argc, char **argv)
{
	program_name = *argv;
	run("refcounts", test_refcounts);
	return 0;
}
