from abc import ABCMeta, abstractmethod

from clojure.lang.associative import Associative
from clojure.lang.iterable import Iterable
from clojure.lang.counted import Counted


class IPersistentMap(Iterable, Associative, Counted, object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def without(self, key):
        pass
