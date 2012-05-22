from abc import ABCMeta, abstractmethod


class Seqable(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def seq(self):
        pass
