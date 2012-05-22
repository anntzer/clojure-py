from abc import ABCMeta, abstractmethod


class Named(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def getNamespace(self):
        pass

    @abstractmethod
    def getName(self):
        pass
