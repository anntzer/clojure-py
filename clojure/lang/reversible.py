from abc import ABCMeta, abstractmethod


class Reversible(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def rseq(self):
        pass
