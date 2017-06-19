/**
 * All objects are struct WeirdObject.
 *
 * The actual content of this struct is mostly an implementation detail,
 * but these fields are always defined. You can look up their values,
 * but don't change them.
 *
 * 	char *typename;
 *		Name of the type of this object as a string.
 * 		This will probably change later.
 *
 * 	size_t refcount;
 * 		Number of references to this object. Use ``obj->refcount == 0``
 * 		to check if an object has been destroyed.
 *
 * 		.. seealso:: :func:`weirdobject_incref`, :func:`weirdobject_decref`
 *
 * 	void *data;
 * 		The arbitary data passed to :func:`weirdobject_new`.
 */
struct WeirdObject {
	char *typename;
	size_t refcount;
	void (*destructor)(struct WeirdObject *);		// can be NULL
	void *data;		// can be anything
};

/**
 * Create a new object.
 *
 * **This returns a new reference.**
 */
struct WeirdObject *
weirdobject_new(char *typename, void (*destructor)(struct WeirdObject *), void *data);

/**
 * Increment reference count.
 */
void weirdobject_incref(struct WeirdObject *me);

/**
 * Decrement reference count .
 *
 * The object is destroyed if the reference count is 0.
 * Return the new reference count.
 */
void weirdobject_decref(struct WeirdObject *me);
