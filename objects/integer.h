#ifndef WEIRD_INTEGER_H_
#define WEIRD_INTEGER_H_

/**
 * Create a new integer from a C ssize_t.
 *
 * @param value the unsigned value
 * @param sign 1 for positive, -1 for negative
 *
 * RETURNS A NEW REFERENCE.
 */
struct WeirdObject *weirdint_new(size_t value, int sign);

/**
 * Return ``me + other``.
 *
 * RETURNS A NEW REFERENCE.
 */
struct WeirdObject *weirdint_add(struct WeirdObject *me, struct WeirdObject *other);

/**
 * Return ``me == other``.
 *
 * RETURNS A NEW REFERENCE.
 */
int weirdint_eq(struct WeirdObject *me, struct WeirdObject *other);

#endif		// WEIRD_INTEGER_H_
