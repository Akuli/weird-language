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

    for (size_t i = 0; i < x_data->len; ++i) {
        new_value[i] = x_data->value[i];
    }

    for (size_t j = 0; j < y_data->len; ++j) {
        new_value[x_data->len + j] = y_data->value[j];
    }

    return weirdstring_new(new_value, new_len);
}

char *weirdstring_to_cstring(struct WeirdObject *s) {
    struct StringData *s_data = s->data;

    char *cstr = malloc(sizeof(char) * (s_data->len + 1));
    memcpy(cstr, s_data->value, s_data->len);
    cstr[s_data->len] = 0;

    return cstr;
}
