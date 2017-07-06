#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "object.h"


static void weirderr_nomem(void) { fprintf(stderr, "not enough memory\n"); exit(1); }

#if _SVID_SOURCE || _BSD_SOURCE || _XOPEN_SOURCE >= 500 || _XOPEN_SOURCE && _XOPEN_SOURCE_EXTENDED || _POSIX_C_SOURCE >= 200809L
    /*
     * As specified in the man page for stdup, if any of those conditions are
     * true strdup is already defined.
     * Re-defining it results on an error, so we check for it here and don't
     * re-create it if we don't need to.
     */
#else
    /* This mustn't be static, since it's used in do_the_input */
    char *strdup(char *str)
    {
        char *result = malloc(strlen(str)+1);  // sizeof(char) is always 1, +1 for '\0'
        if (!result)
            weirderr_nomem();
        strcpy(result, str);
        return result;
    }
#endif


struct WeirdObject *
weirdobject_new(char *typename, void (*destructor)(void *), void *data)
{
	struct WeirdObject *me = malloc(sizeof (struct WeirdObject));
	if (!me)
		weirderr_nomem();

	printf("object.c: creating %s %p with data %p\n", typename, me, data);
	me->typename = strdup(typename);
	me->use_refcount = 1;
	me->refcount = 1;
	me->destructor = destructor;
	me->data = data;
	return me;
}

void weirdobject_incref(struct WeirdObject *me)
{
	if (me->use_refcount) {
		assert(me->refcount > 0);
		me->refcount++;
	}
}

void weirdobject_destroy(struct WeirdObject *me)
{
	printf("object.c: destroying %s %p with data %p\n",
		(char *) me->typename, me, me->data);
	if (me->destructor)
		me->destructor(me->data);
	free(me->typename);
	free(me);
}

void weirdobject_decref(struct WeirdObject *me)
{
	if (me->use_refcount) {
		assert(me->refcount > 0);
		me->refcount--;
		if (me->refcount == 0)
			weirdobject_destroy(me);
	}
}
