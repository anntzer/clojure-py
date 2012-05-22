from abc import ABCMeta, abstractmethod

class ITransientCollection(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def conj(self, val):
        pass

    @abstractmethod
    def persistent(self):
        pass
