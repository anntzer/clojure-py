from abc import ABCMeta, abstractmethod

class IMeta(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def meta(self):
        """Return the metadata of an object.
        """
