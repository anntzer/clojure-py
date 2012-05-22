from abc import ABCMeta, abstractmethod

class Iterable(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __iter__(self):
        pass
