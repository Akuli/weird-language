#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "objects/object.h"
#include "objects/list.h"
#include "objects/integer.h"
#include "objects/string.h"

#define assert_streq(a, b) assert(strcmp((a), (b)) == 0)

#define START_TEST printf("\n---------- %s() ----------\n", __func__)

int destroyed = 0;
static void destroy_cb(void *data) { destroyed = 1; }

void test_refcounts(void)
{
	START_TEST;
	char data[] = "hello";

	struct WeirdObject *test = weirdobject_new("WoloWolo", destroy_cb, (void *) data);
	assert(test->refcount == 1);
	assert_streq((char *) test->data, "hello");

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
	START_TEST;

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
		assert(item->refcount == 2);	// initial 1 + incref in getbyindex
		assert_streq((char *) item->data, vals[i]);
		weirdobject_decref(item);
	}

	weirdobject_decref(list);
}
#undef ITEM_COUNT


void test_integers(void)
{
	START_TEST;
	struct WeirdObject
		*zero = weirdint_new(0, 1),
		*a = weirdint_new(10, 1),
		*b = weirdint_new(20, 1),
		*c = weirdint_new(10, -1),
		*aa = weirdint_add(a, a),
		*ac = weirdint_add(a, c),
		*bc = weirdint_add(b, c);

	assert(weirdint_eq(aa, b));
	assert(weirdint_eq(bc, a));
	assert(weirdint_eq(ac, zero));

	weirdobject_decref(zero);
	weirdobject_decref(a);
	weirdobject_decref(b);
	weirdobject_decref(c);
	weirdobject_decref(aa);
	weirdobject_decref(ac);
	weirdobject_decref(bc);
}

void test_strings(void) {
    START_TEST;
    struct WeirdObject *x = weirdstring_new("abc", 3);
    struct WeirdObject *y = weirdstring_new("def", 3);
    struct WeirdObject *z = weirdstring_concat(x, y);

    struct _WeirdString_Data *z_data = z->data;
    assert(z_data->len == 6);

    char *z_cstr = weirdstring_to_cstring(z);
    assert_streq(z_cstr, "abcdef");
    free(z_cstr);

    weirdobject_decref(x);
    weirdobject_decref(y);
    weirdobject_decref(z);
}


typedef void (*TestFunc)(void);
TestFunc tests[] = {
	test_refcounts,
	//test_lists,
	test_integers,
	test_strings
};

int main(void)
{
	for (unsigned int i = 0; i < sizeof(tests)/sizeof(TestFunc); i++)
		tests[i]();
	printf("\nall OK\n");
	return 0;
}
