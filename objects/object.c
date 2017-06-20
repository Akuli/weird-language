#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "object.h"


static void weirderr_nomem(void) { fprintf(stderr, "not enough memory\n"); exit(1); }

// strdup() isn't defined in C99 :(
static char *weird_strdup(char *str)
{
	/* some people say that sizeof(char) is defined to be 1, but I
	 * didn't find it in the standards */
	size_t count = strlen(str) + 1;		// remember the \0 at end
	char *result = malloc(count * sizeof(char));
	for (size_t i = 0; i < count; i++)
		result[i] = str[i];
	return result;
}


struct WeirdObject *
weirdobject_new(char *typename, void (*destructor)(void *), void *data)
{
	struct WeirdObject *me = malloc(sizeof (struct WeirdObject));
	if (!me)
		weirderr_nomem();

	printf("object.c: creating   %10p with data %p\n", me, data);
	me->typename = weird_strdup(typename);
	me->refcount = 0;
	me->destructor = destructor;
	me->data = data;
	return me;
}

void weirdobject_incref(struct WeirdObject *me)
{
	me->refcount++;
}

void weirdobject_decref(struct WeirdObject *me)
{
	assert(me->refcount > 0);
	me->refcount--;
	if (me->refcount == 0) {
		printf("object.c: destroying %10p with data %p\n", me, me->data);
		if (me->destructor)
			me->destructor(me->data);
		free(me->typename);
		free(me);
	}
}
