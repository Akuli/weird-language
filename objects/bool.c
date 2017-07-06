#include <assert.h>
#include <stdlib.h>

#include "bool.h"


struct Data {
	int value;		// 1 or 0
};

void weirdbool_init(void)
{
	struct Data *truedata = malloc(sizeof (struct Data));
	struct Data *falsedata = malloc(sizeof (struct Data));
	truedata->value = 1;
	falsedata->value = 0;

	// FIXME: can free be implemented as a macro?
	weirdbool_TRUE = weirdobject_new("Bool", free, truedata);
	weirdbool_FALSE = weirdobject_new("Bool", free, falsedata);

	weirdbool_TRUE->use_refcount = weirdbool_FALSE->use_refcount = 0;
}

void weirdbool_finalize(void)
{
	weirdobject_destroy(weirdbool_TRUE);
	weirdobject_destroy(weirdbool_FALSE);
}

struct WeirdObject *weirdbool_fromint(int value)
{
	return (value ? weirdbool_TRUE : weirdbool_FALSE);
}

int weirdbool_asint(struct WeirdObject *me)
{
	if (me == weirdbool_TRUE)
		return 1;
	if (me == weirdbool_FALSE)
		return 0;
	assert(0);		// it's not TRUE or FALSE
}
