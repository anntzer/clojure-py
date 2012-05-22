from abc import ABCMeta, abstractmethod

class IObj(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def withMeta(self, meta):
        pass
