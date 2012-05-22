from abc import ABCMeta, abstractmethod

from clojure.lang.ilookup import ILookup
from clojure.lang.ipersistentcollection import IPersistentCollection


class Associative(ILookup, IPersistentCollection, object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def containsKey(self, key):
        """Return whether a key is mapped by an object.
        """

    @abstractmethod
    def entryAt(self, key):
        """Return the mapping an object gives to a key.
        """

    @abstractmethod
    def assoc(self, key, val):
        """Return a new object with an extra mapping from a key to a value.
        """
