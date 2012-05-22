from abc import ABCMeta, abstractmethod


class Settable(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def doSet(self, o):
        pass

    @abstractmethod
    def doReset(self, o):
        pass
