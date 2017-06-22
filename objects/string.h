#ifndef WEIRDSTRING_H
#define WEIRDSTRING_H
#include <stddef.h>

#include "object.h"

struct StringData {
    char *value;
    size_t len;
};

struct WeirdObject *weirdstring_new(char *value, size_t len);

struct WeirdObject *weirdstring_concat(struct WeirdObject *x, struct WeirdObject *y);

char *weirdstring_to_cstring(struct WeirdObject *s);

#endif /* WEIRDSTRING_H */
