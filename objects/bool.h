#ifndef WEIRD_BOOL_H_
#define WEIRD_BOOL_H_

#include "object.h"

/**
 * The only two weirdbool objects.
 *
 * These objects are not reference counted.
 */
struct WeirdObject *weirdbool_TRUE;
struct WeirdObject *weirdbool_FALSE;

/**
 * This defines ``weirdbool_TRUE`` and ``weirdbool_FALSE``.
 *
 * Call this in the start of ``main()``.
 */
void weirdbool_init(void);

/**
 * This frees ``weirdbool_TRUE`` and ``weirdbool_FALSE``.
 *
 * Call this at the end of ``main()``.
 */
void weirdbool_finalize(void);

/**
 * Return ``weirdbool_TRUE`` or ``weirdbool_FALSE``.
 *
 * @param value 1 or 0
 */
struct WeirdObject *weirdbool_fromint(int value);

/**
 * Return 1 or 0.
 */
int weirdbool_asint(struct WeirdObject *me);

#endif		// WEIRD_BOOL_H_
