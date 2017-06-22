#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "object.h"


static void weirderr_nomem(void) { fprintf(stderr, "not enough memory\n"); exit(1); }

// strdup() isn't defined in C99, this version is based on K&R :)
static char *strdup(char *str)
{
	char *result = malloc(strlen(str)+1);  // sizeof(char) is always 1, +1 for '\0'
	if (!result)
		weirderr_nomem();
	strcpy(result, str);
	return result;
}


struct WeirdObject *
weirdobject_new(char *typename, void (*destructor)(void *), void *data)
{
	struct WeirdObject *me = malloc(sizeof (struct WeirdObject));
	if (!me)
		weirderr_nomem();

	printf("object.c: creating %s %p with data %p\n", typename, me, data);
	me->typename = strdup(typename);
	me->refcount = 1;
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
		printf("object.c: destroying %s %p with data %p\n",
			(char *) me->typename, me, me->data);
		if (me->destructor)
			me->destructor(me->data);
		free(me->typename);
		free(me);
	}
}
