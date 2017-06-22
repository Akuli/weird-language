#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

#include "object.h"
#include "list.h"


static void weirderr_nomem(void) { fprintf(stderr, "not enough memory\n"); exit(1); }


static void destructor(void *voiddata)
{
	struct _WeirdList_Data *data = voiddata;
	for (size_t i = 0; i < data->length; i++)
		weirdobject_decref(data->values[i]);
	free(data);
}

struct WeirdObject *weirdlist_new(void)
{
	struct _WeirdList_Data *data = malloc(sizeof (struct _WeirdList_Data));
	data->length = 0;
	data->maxlen = 10;
	data->values = malloc(10 * sizeof (struct WeirdObject *));
	return weirdobject_new("List", destructor, (void *) data);
}

struct WeirdObject *weirdlist_getbyindex(struct WeirdObject *me, size_t index)
{
	struct _WeirdList_Data *data = me->data;
	struct WeirdObject *result = data->values[index];
	weirdobject_incref(result);
	return result;
}

// TODO: use a WeirdObject integer some day
size_t weirdlist_getlength(struct WeirdObject *me)
{
	struct _WeirdList_Data *data = me->data;
	return data->length;
}

static void resize(struct _WeirdList_Data *data)
{
	if (data->maxlen >= data->length)
		return;

	printf("****** RESIZING ****\n");

	// the list is resized as needed like this: 10, 100, 1000, ...
	data->maxlen *= 10;

	/* this needs to be changed if out-of-memory error handling will be
	 * changed later */
	data->values = realloc(data->values, data->maxlen * sizeof(struct WeirdObject *));
	if (!(data->values))
		weirderr_nomem();
}

void weirdlist_add(struct WeirdObject *me, struct WeirdObject *item)
{
	// TODO: check for overflows
	struct _WeirdList_Data *data = me->data;
	weirdobject_incref(item);
	data->length++;
	resize(data);
	data->values[data->length-1] = item;
}
