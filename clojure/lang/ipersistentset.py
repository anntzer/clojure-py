from abc import ABCMeta, abstractmethod
from clojure.lang.ipersistentcollection import IPersistentCollection
from clojure.lang.counted import Counted

class IPersistentSet(IPersistentCollection, Counted):
    __metaclass__ = ABCMeta

    @abstractmethod
    def disjoin(self, key):
        pass

    @abstractmethod
    def __contains__(self, item):
        pass

    def __getitem__(self, item):
        return self.get(item)
