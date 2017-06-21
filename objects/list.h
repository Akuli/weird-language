#ifndef WEIRD_LIST_H_
#define WEIRD_LIST_H_

// TODO: figure out a better way to expose this to test_objects.c
struct _WeirdList_Data {
	size_t length;
	size_t maxlen;
	struct WeirdObject **values;
};

/**
 * Create a new, empty list.
 *
 * RETURNS A NEW REFERENCE.
 */
struct WeirdObject *weirdlist_new(void);

/**
 * Add an item to end of the list.
 */
void weirdlist_add(struct WeirdObject *me, struct WeirdObject *item);

/**
 * Look up an element from the list by index.
 *
 * Note that this does NOT return a new reference because having the object in
 * the list already references it.
 */
struct WeirdObject *weirdlist_getbyindex(struct WeirdObject *me, size_t index);

/**
 * Get the length of a list as size_t.
 */
size_t weirdlist_getlength(struct WeirdObject *me);

#endif		// WEIRD_LIST_H_
