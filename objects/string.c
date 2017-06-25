#include <stdlib.h>
#include <stddef.h>
#include <string.h>

#include "object.h"
#include "string.h"

static void weirdstring_free(void *data_ptr) {
    struct _WeirdString_Data *data = (struct _WeirdString_Data*) data_ptr;
    free(data->value);
    free(data);
}

struct WeirdObject *weirdstring_new(char *value, size_t len) {
    struct _WeirdString_Data *data = malloc(sizeof(struct _WeirdString_Data));
    data->len = len;
    data->value = malloc(len);
    memcpy(data->value, value, len);
    return weirdobject_new("String", weirdstring_free, data);
}

struct WeirdObject *weirdstring_concat(struct WeirdObject *x, struct WeirdObject *y)
{
    struct _WeirdString_Data *x_data = x->data;
    struct _WeirdString_Data *y_data = y->data;

    char *tmp = malloc(x_data->len + y_data->len);
    memcpy(tmp, x_data->value, x_data->len);
    memcpy(tmp + x_data->len, y_data->value, y_data->len);

	struct WeirdObject *res = weirdstring_new(tmp, x_data->len + y_data->len);
	free(tmp);
    return res;
}

char *weirdstring_to_cstring(struct WeirdObject *s) {
    struct _WeirdString_Data *s_data = s->data;

    char *cstr = malloc(sizeof(char) * (s_data->len + 1));
    memcpy(cstr, s_data->value, s_data->len);
    cstr[s_data->len] = 0;

    return cstr;
}
