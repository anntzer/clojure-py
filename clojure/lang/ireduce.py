from abc import ABCMeta, abstractmethod

class IReduce(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def reduce(self, *args):
        pass
