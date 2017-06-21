#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "objects/object.h"
#include "objects/list.h"

#define assert_streq(a, b) assert(strcmp((a), (b)) == 0)


int destroyed = 0;
static void destroy_cb(void *data) { destroyed = 1; }

void test_refcounts(void)
{
	char data[] = "hello";

	struct WeirdObject *test = weirdobject_new("WoloWolo", destroy_cb, (void *) data);
	assert(test->refcount == 1);
	assert(strcmp((char *) test->data, "hello") == 0);

	weirdobject_incref(test);
	weirdobject_incref(test);
	weirdobject_incref(test);
	assert(test->refcount == 4);
	assert_streq((char *) test->data, "hello");

	weirdobject_decref(test);
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


#define ITEM_COUNT 15
void test_lists(void)
{
	// this must contain at least ITEM_COUNT elements
	static char *vals[] = {
		"0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
		"10", "11", "12", "13", "14", "15", "16", "17", "18", "19" };

	struct WeirdObject *items[ITEM_COUNT];
	struct WeirdObject *list = weirdlist_new();
	struct _WeirdList_Data *data = list->data;
	assert(list->refcount == 1);

	for (size_t i = 0; i < ITEM_COUNT; i++) {
		items[i] = weirdobject_new("ListItem", NULL, vals[i]);

		assert(data->length == i);
		assert(items[i]->refcount == 1);

		weirdlist_add(list, items[i]);
		assert(data->length == i+1);
		assert(items[i]->refcount == 2);

		weirdobject_decref(items[i]);
		assert(items[i]->refcount == 1);
		// now decrefing the list destroys the item
	}

	assert(data->length == ITEM_COUNT);
	assert(weirdlist_getlength(list) == ITEM_COUNT);

	for (size_t i = 0; i < ITEM_COUNT; i++) {
		struct WeirdObject *item = weirdlist_getbyindex(list, i);
		assert_streq((char *) item->data, vals[i]);
	}

	weirdobject_decref(list);
}


char *program_name;

void run(char *name, void (test)(void))
{
	printf("---------- %s() ----------\n", name);
	test();
	printf("\n");
}

int main(int argc, char **argv)
{
	program_name = *argv;
	run("test_refcounts", test_refcounts);
	run("test_lists", test_lists);
	printf("\nall OK\n");
	return 0;
}
