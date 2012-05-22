from abc import ABCMeta, abstractmethod

class IHashEq(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def hasheq(self):
        pass
