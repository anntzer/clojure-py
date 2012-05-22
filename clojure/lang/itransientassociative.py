from abc import ABCMeta, abstractmethod

from clojure.lang.itransientcollection import ITransientCollection
from clojure.lang.ilookup import ILookup


class ITransientAssociative(ITransientCollection, ILookup):
    __metaclass__ = ABCMeta

    @abstractmethod
    def assoc(self, key, val):
        pass
