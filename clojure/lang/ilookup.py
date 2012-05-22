from abc import ABCMeta, abstractmethod

class ILookup(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def valAt(self, key, notFound=None):
        pass

