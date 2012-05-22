from abc import ABCMeta, abstractmethod
from clojure.lang.imeta import IMeta

class IReference(IMeta):
    __metaclass__ = ABCMeta

    @abstractmethod
    def alterMeta(self, fn, args):
        """Alters the metadata of an object through a function.
        """

    @abstractmethod
    def resetMeta(self, meta):
        """Resets the metadata of an object to a new value.
        """
