from abc import ABCMeta, abstractmethod

from clojure.lang.ipersistentcollection import IPersistentCollection


class IPersistentStack(IPersistentCollection):
    __metaclass__ = ABCMeta

    @abstractmethod
    def peek(self):
        pass

    @abstractmethod
    def pop(self):
        pass
