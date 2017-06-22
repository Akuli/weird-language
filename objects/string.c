#include <stdlib.h>
#include <stddef.h>
#include <string.h>

#include "object.h"
#include "string.h"

static void weirdstring_free(void *data_ptr) {
    struct StringData *data = (struct StringData*) data_ptr;
    free(data->value);
    free(data);
}

struct WeirdObject *weirdstring_new(char *value, size_t len) {
    struct StringData *data = malloc(sizeof(struct StringData));
    data->value = value;
    data->len = len;
    return weirdobject_new("String", weirdstring_free, data);
}

struct WeirdObject *weirdstring_concat(struct WeirdObject *x, struct WeirdObject *y) {
    struct StringData *x_data = x->data;
    struct StringData *y_data = y->data;

    size_t new_len = x_data->len + y_data->len;
    char *new_value = malloc(sizeof(char) * new_len);

    memcpy(new_value, x_data->value, x_data->len);
    memcpy(new_value + x_data->len, y_data->value, y_data->len);

    return weirdstring_new(new_value, new_len);
}

char *weirdstring_to_cstring(struct WeirdObject *s) {
    struct StringData *s_data = s->data;

    char *cstr = malloc(sizeof(char) * (s_data->len + 1));
    memcpy(cstr, s_data->value, s_data->len);
    cstr[s_data->len] = 0;

    return cstr;
}
