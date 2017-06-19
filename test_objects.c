#include <stdio.h>
#include <string.h>
#include "objects/object.h"

// torvalds hates me for doing this :(
#define ASSERT_FALSE(x) if ((x)) return 1;
#define ASSERT_TRUE(x) if (!(x)) return 2;
#define ASSERT_EQ(x, y) if ((x) != (y)) return 3;
#define ASSERT_STREQ(x, y) if(strcmp((x), (y)) != 0) return 4;


int destroyed = 0;
static void destroy_cb(struct WeirdObject *me) { destroyed = 1; }
int test_refcounts(void)
{
	char data[] = "hello";

	struct WeirdObject *test = weirdobject_new("WoloWolo", destroy_cb, (void *) data);
	ASSERT_EQ(test->refcount, 1);
	ASSERT_STREQ((char *) test->data, "hello");

	weirdobject_incref(test);
	ASSERT_EQ(test->refcount, 2);
	ASSERT_STREQ((char *) test->data, "hello");

	weirdobject_decref(test);
	ASSERT_EQ(test->refcount, 1);
	ASSERT_STREQ((char *) test->data, "hello");

	ASSERT_FALSE(destroyed);
	weirdobject_decref(test);
	// test is freed, can't check refcounts and stuff anymore
	ASSERT_TRUE(destroyed);
	ASSERT_EQ(test->refcount, 0);
	return 0;
}

int run(char *name, int (test)(void))
{
	int ret = test();
	if (ret == 0)
		printf("OK:   %s\n", name);
	else
		printf("FAIL: %s (code %d)\n", name, ret);
	return ret;
}


int main(void)
{
	int nfailed = 0;
	nfailed += run("refcounts", test_refcounts);
	printf("%d tests failed\n", nfailed);
	return nfailed == 0 ? 0 : 1;
}
