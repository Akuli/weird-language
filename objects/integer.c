#include <assert.h>
#include <stdlib.h>
#include <stddef.h>

#include "object.h"
#include "integer.h"


// ssize_t is not in c99 :(
struct Data {
	int sign;		// 1 or -1
	size_t value;
};


struct WeirdObject *weirdint_new(size_t value, int sign)
{
	assert(sign == 1 || sign == -1);
	struct Data *data = malloc(sizeof (struct Data));
	data->value = value;
	data->sign = sign;
	return weirdobject_new("Int", free, data);
}

struct WeirdObject *weirdint_add(struct WeirdObject *me, struct WeirdObject *other)
{
	struct Data *data1 = me->data, *data2 = other->data;

	if (data1->sign == data2->sign)
		return weirdint_new(data1->value + data2->value, data1->sign);

	// ok, so their signs are different...
	if (data1->value > data2->value) {
		// data1->value is big, so it determines the sign
		// data1->value - data2->value is also known to be positive
		return weirdint_new(data1->value - data2->value, data1->sign);
	}

	return weirdint_new(data2->value - data1->value, data2->sign);
}

int weirdint_eq(struct WeirdObject *a, struct WeirdObject *b)
{
	struct Data *data1 = a->data, *data2 = b->data;
	if (data1->value == 0 && data2->value == 0)	// special case: ignore signs
		return 1;
	return (data1->sign == data2->sign && data1->value == data2->value);
}
