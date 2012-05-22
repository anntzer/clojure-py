from abc import ABCMeta, abstractmethod

from clojure.lang.seqable import Seqable


class IPersistentCollection(Seqable, object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def count(self):
        pass

    @abstractmethod
    def cons(self, o):
        pass

    @abstractmethod
    def empty(self):
        pass

