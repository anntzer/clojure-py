"""
March 25, 2012 -- Documented
"""

from clojure.lang.iobj import IObj
from clojure.lang.apersistentset import APersistentSet
from clojure.lang.persistenthashmap import EMPTY as EMPTY_MAP
from clojure.lang.cljexceptions import IllegalArgumentException


class PersistentHashSet(APersistentSet, IObj):
    def __init__(self, meta, impl):
        """Use create or createWithCheck to instantiate."""
        APersistentSet.__init__(self, impl)
        self._meta = meta

    def cons(self, o):
        """Return a new PersistentHashSet with o added.

        o -- any object

        The new set will have this set's meta data attached. If o is already
        in this set, return this set."""
        if o in self:
            return self
        return PersistentHashSet(self._meta, self.impl.assoc(o, o))

    def meta(self):
        """Return this PersistentHashSet's meta data'"""
        return self._meta

    def withMeta(self, meta):
        """Return a new PersistentHashSet.

        meta -- the meta data to attach to the returned set

        The set will share this set's content.'"""
        return PersistentHashSet(meta, self.impl)

    def empty(self):
        """Return an empty PersistentHashSet.

        The new set will have this set's meta data attached."""
        return EMPTY.withMeta(self.meta())

    def disjoin(self, key):
        """Return a new PersistentHashSet with key removed.

        key -- any object

        If the key is not in this set, return this set."""
        if key not in self:
            return self
        return PersistentHashSet(self._meta, self.impl.without(key))


def create(*args):
    """Return a new PersistentHashSet.

    create()
    An empty PersistentHashSet will be returned.

    create(iterable)
    The elements of the iterable will be added to the returned set. Any
    duplicates will be silently omitted.

    create(obj1, obj2, ..., objN)
    Add the objs, omitting duplicates."""
    if not len(args):
        return EMPTY
    if len(args) == 1 and hasattr(args[0], "__iter__"):
        m = EMPTY
        s = args[0]
        for x in s:
            m = m.cons(x)
        return m
    m = EMPTY
    for x in args:
        m = m.cons(x)
    return m


def createWithCheck(iterable):
    """Return a new PersistentHashSet containing the items in iterable.

    iterable -- any iterable sequence of objects

    Raise IllegalArgumentException if a duplicate is found in iterable."""
    ret = EMPTY
    for i, key in enumerate(iterable):
        ret = ret.cons(key)
        if len(ret) != i + 1:
            raise IllegalArgumentException("Duplicate key: {0}".format(key))
    return ret;


EMPTY = PersistentHashSet(None, EMPTY_MAP)
