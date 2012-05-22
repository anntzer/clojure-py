from abc import ABCMeta, abstractmethod

class Counted(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __len__(self):
        """Returns the size of an object.
        """
