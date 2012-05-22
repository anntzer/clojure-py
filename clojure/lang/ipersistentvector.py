from abc import ABCMeta, abstractmethod

from clojure.lang.associative import Associative
from clojure.lang.sequential import Sequential
from clojure.lang.ipersistentstack import IPersistentStack
from clojure.lang.reversible import Reversible
from clojure.lang.indexed import Indexed


class IPersistentVector(Associative, Sequential, IPersistentStack, Reversible, Indexed):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __len__(self):
        pass

    @abstractmethod
    def assocN(self, i, val):
        pass

    @abstractmethod
    def cons(self, o):
        pass
