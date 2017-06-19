#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "object.h"


static void weirderr_nomem()
{
	fprintf(stderr, "not enough memory :(\n");
	exit(1);
}

// strdup() isn't defined in C99 :(
static char *weird_strdup(char *str)
{
	size_t count = strlen(str) + 1;		// remember the \0 at end
	char *result = malloc(count * sizeof(char));
	for (size_t i = 0; i < count; i++)
		result[i] = str[i];
	return result;
}


struct WeirdObject *
weirdobject_new(char *typename, void (*destructor)(struct WeirdObject *), void *data)
{
	struct WeirdObject *result = malloc(sizeof (struct WeirdObject));
	if (!result)
		weirderr_nomem();

	printf("creating %p\n", result);
	result->typename = weird_strdup(typename);
	result->refcount = 1;
	result->destructor = destructor;
	result->data = data;
	return result;
}

void weirdobject_incref(struct WeirdObject *me)
{
	assert(me->refcount > 0);
	me->refcount++;
}

void weirdobject_decref(struct WeirdObject *me)
{
	assert(me->refcount > 0);
	me->refcount--;
	if (me->refcount == 0) {
		printf("destroying %p\n", me);
		if (me->destructor)
			me->destructor(me);
		free(me->typename);
		free(me);
	}
}
