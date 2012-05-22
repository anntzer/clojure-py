from abc import ABCMeta, abstractmethod

from clojure.lang.itransientassociative import ITransientAssociative
from clojure.lang.counted import Counted

class ITransientMap(ITransientAssociative, Counted):
    __metaclass__ = ABCMeta

    @abstractmethod
    def assoc(self, key, value):
        pass

    @abstractmethod
    def without(self, key):
        pass

    @abstractmethod
    def persistent(self):
        pass
