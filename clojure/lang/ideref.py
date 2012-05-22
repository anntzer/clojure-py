from abc import ABCMeta, abstractmethod

class IDeref(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def deref(self):
        """Dereference an object.
        """
