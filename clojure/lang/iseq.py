from abc import ABCMeta, abstractmethod
from clojure.lang.ipersistentcollection import IPersistentCollection

class ISeq(IPersistentCollection):
    __metaclass__ = ABCMeta

    @abstractmethod
    def first(self):
        """Return the first item in the collection or None if it's empty.
        """

    @abstractmethod
    def next(self):
        """Return the *tail* of the collection or None if () or (x).
        """

    @abstractmethod
    def more(self):
        """Return the *tail* of the collection or () if () or (x).
        """

    @abstractmethod
    def cons(self, o):
        """Add an item to the front of the collection.
        """
