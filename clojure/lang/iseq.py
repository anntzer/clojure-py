from clojure.lang.cljexceptions import AbstractMethodCall
from clojure.lang.ipersistentcollection import IPersistentCollection
from . import protocol


@protocol.asProtocol()
class ISeq(IPersistentCollection):
    def first(self):
        """Return the first item in the collection or None if it's empty."""
        raise AbstractMethodCall(self)

    def next(self):
        """Return the *tail* of the collection or None if () or (x)."""
        raise AbstractMethodCall(self)

    def more(self):
        """Return the *tail* of the collection or () if () or (x)."""
        raise AbstractMethodCall(self)

    def cons(self, o):
        """Add an item to the front of the collection."""
        raise AbstractMethodCall(self)

