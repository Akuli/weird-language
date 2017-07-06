#ifndef WEIRD_OBJECT_H_
#define WEIRD_OBJECT_H_

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
 * 	int use_refcount;
 * 		Set this to 0 to disable reference counting. 1 by default.
 *
 * 	size_t refcount;
 * 		Number of references to this object. This is 1 by default.
 *
 * 		Note that you can't use ``obj->refcount == 0`` to check if an
 * 		object has been destroyed because objects are free()d during
 * 		destruction.
 *
 * 		.. seealso:: :func:`weirdobject_incref`, :func:`weirdobject_decref`
 *
 * 	void *data;
 * 		The arbitary data passed to :func:`weirdobject_new`.
 */
struct WeirdObject {
	char *typename;
	int use_refcount;
	size_t refcount;
	void (*destructor)(void *);
	void *data;
};

/**
 * Create a new object.
 *
 * RETURNS A NEW REFERENCE.
 *
 * @param typename name of this type, as string
 * @param destructor ``destructor(data)`` will be called when the object is destroyed
 * @param data pointer to any arbitary data associated with the object
 */
struct WeirdObject *
weirdobject_new(char *typename, void (*destructor)(void *), void *data);

/**
 * Free an object and everything associated with it.
 *
 * Note that :func:`weirdobject_decref` calls this automatically if
 * reference counting is used, so this is only useful for things that
 * are not reference counted.
 */
void weirdobject_destroy(struct WeirdObject *me);

/**
 * Increment reference count if ``use_refcount`` is nonzero.
 */
void weirdobject_incref(struct WeirdObject *me);

/**
 * Decrement reference count if ``use_refcount`` is nonzero.
 *
 * The object is destroyed if the reference count becomes 0.
 */
void weirdobject_decref(struct WeirdObject *me);

#endif		// WEIRD_OBJECT_H_
